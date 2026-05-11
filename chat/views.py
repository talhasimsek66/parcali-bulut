# chat/views.py

import json
import requests
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from scraper.models import AcibademData
from .models import ChatMessage, ChatSession
from pgvector.django import CosineDistance


# ana sayfa burasi soldaki gecmisi tarihe gore dizip gonderiyoruz
def chat_interface(request):
    sessions = ChatSession.objects.all().order_by('-created_at')
    return render(request, 'chat/index.html', {'sessions': sessions})


# tiklanan sohbetin gecmisini donduren yer bulamazsa 404
def get_chat_history(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    messages = session.messages.all().order_by('created_at')

    # eski mesajlari sirasiyla alip json yapiyoruz frontende lazim
    history = [
        {
            'user_message': msg.user_message,
            'ai_response': msg.ai_response,
        }
        for msg in messages
    ]
    return JsonResponse({'messages': history})


# silme apisi calisiyor dokunmadim
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_session(request, session_id):
    try:
        session = ChatSession.objects.get(pk=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Oturum bulunamadı."}, status=404)
    session.delete()
    return HttpResponse(status=204)


# ana beynimiz burasi disardan gelen post isteklerini karsilar
@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_question = data.get('question', '')
            session_id = data.get('session_id')

            # adam eski sohbete devam ediyorsa onu bul yoksa ilk 40 harften yeni baslik atip oturum ac
            if session_id:
                session = ChatSession.objects.get(id=session_id)
            else:
                title = user_question[:40] + ("..." if len(user_question) > 40 else "")
                session = ChatSession.objects.create(title=title)

            # adamin sorusunu alip ollamaya veriyoruz ki matematiksel vektore cevirsin
            question_embedding = None
            try:
                embed_response = requests.post('http://llm:11434/api/embeddings', json={
                    "model": "nomic-embed-text",
                    "prompt": user_question
                })
                question_embedding = embed_response.json().get('embedding')
            except Exception as e:
                print(f"Soru vektöre çevrilemedi: {e}")

            # once anlamina gore en yakin 5 seyi bul
            vector_results = []
            if question_embedding:
                vector_results = list(
                    AcibademData.objects.filter(embedding__isnull=False)
                    .annotate(rag_dist=CosineDistance('embedding', question_embedding))
                    .order_by('rag_dist')[:5]
                )

            # sonra tam kelime eslesmesi var mi ona bak ozel isimler ve ders kodlari icin sart bu
            query = SearchQuery(user_question)
            keyword_results = list(
                AcibademData.objects.annotate(
                    search=SearchVector('title', 'content'),
                    rank=SearchRank(SearchVector('title', 'content'), query)
                ).filter(search=query).order_by('-rank')[:5]
            )

            # ikisi ayni seyi bulmussa ust uste binmesin diye id uzerinden teke dusuruyoruz
            combined_dict = {item.id: item for item in (vector_results + keyword_results)}
            acibadem_data = list(combined_dict.values())

            # hicbir sey bulamazsa bos kalmasin diye rastgele 5 tane veriyoruz
            if not acibadem_data:
                acibadem_data = list(AcibademData.objects.all()[:5])

            # hepsini alt alta ekleyip devasa bir metin yapiyoruz yapay zeka bunu okuyacak
            context_text = "\n\n".join([f"--- {item.title} ---\n{item.content}" for item in acibadem_data])

            # modelin kafasi yanmasin diye sadece son 5 mesaji veriyoruz
            recent_chats = session.messages.all().order_by('-created_at')[:5]
            history_text = ""
            if recent_chats:
                for chat in reversed(recent_chats):
                    history_text += f"Kullanıcı: {chat.user_message}\nAsistan: {chat.ai_response}\n\n"
            else:
                history_text = "Bu oturumdaki ilk konuşmamız."

            # burasi prompt kismi modele nasil davranacagini soyluyoruz
            prompt = f"""Sen Acıbadem Üniversitesi için tasarlanmış resmi ve yardımsever bir yapay zeka asistanısın. 
            Aşağıda sana üniversitenin web sitesinden toplanmış bazı güncel bilgiler (Context) ve bizim seninle olan önceki konuşmalarımızın geçmişini (Geçmiş) veriyorum. 
            Lütfen kullanıcının sorusunu SADECE bu bilgilere ve geçmiş konuşmalarımıza dayanarak yanıtla. 
            Eğer cevap bu bilgilerde yoksa "Bu konu hakkında elimde güncel bir bilgi bulunmuyor." de ve asla uydurma.

            [ÖNCEKİ KONUŞMALAR (GEÇMİŞ)]
            {history_text}
            [GEÇMİŞ BİTİŞİ]

            [BAĞLAM (CONTEXT) BİLGİLERİ BAŞLANGICI]
            {context_text}
            [BAĞLAM (CONTEXT) BİLGİLERİ BİTİŞİ]

            Kullanıcının Sorusu: {user_question}
            Cevabın:"""

            # uydurma riski var
            ollama_url = "http://llm:11434/api/generate"
            payload = {
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.4
                }
            }

            # kelime kelime ekrana akitma isini burasi yapiyor bitince de db ye kaydediyor
            def stream_response():
                full_response = ""
                with requests.post(ollama_url, json=payload, stream=True) as r:
                    r.raise_for_status()
                    for line in r.iter_lines():
                        if line:
                            decoded_line = json.loads(line.decode('utf-8'))
                            chunk = decoded_line.get("response", "")
                            full_response += chunk
                            yield chunk

                ChatMessage.objects.create(
                    session=session,
                    user_message=user_question,
                    ai_response=full_response,
                )

            # json degil stream donduruyoruz ki harfler yagsin
            response = StreamingHttpResponse(stream_response(), content_type='text/plain')
            response['X-Session-ID'] = str(session.id)
            return response

        except Exception as e:
            # patlarsa 500 hatasi
            return JsonResponse({'error': f"Sistem hatası: {str(e)}"}, status=500)

    # post degilse dogrudan reddet
    return JsonResponse({'error': 'Geçersiz istek tipi.'}, status=400)

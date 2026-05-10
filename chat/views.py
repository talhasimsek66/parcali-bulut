# chat/views.py

import requests
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from scraper.models import AcibademData
from .models import ChatMessage, ChatSession
from django.db.models import Q
from pgvector.django import CosineDistance


# ana sayfa view i
def chat_interface(request):
    # soldaki sidebar (eskiden yeniye)
    sessions = ChatSession.objects.all().order_by('-created_at')
    return render(request, 'chat/index.html', {'sessions': sessions})


# geçmiş yükleme api si (kullanıcı sol menüden bir sohbete tıkladığında bu fonksiyon çalışır)
def get_chat_history(request, session_id):
    # belirtilen id ye sahip oturumu bulur (yoksa 404)
    session = get_object_or_404(ChatSession, id=session_id)

    # o oturuma ait mesajları tarihe göre getirir
    messages = session.messages.all().order_by('created_at')

    # frontend için josn çevir
    history = [
        {'user_message': msg.user_message, 'ai_response': msg.ai_response}
        for msg in messages
    ]
    return JsonResponse({'messages': history})


# llm iletişim api si
@csrf_exempt  # frontend'den gelen POST isteklerinde CSRF token zorunluğu yok
def chat_api(request):
    if request.method == 'POST':
        try:
            # frontend den gelen JSON verisini ayarlar
            data = json.loads(request.body)
            user_question = data.get('question', '')  # kullanıcının sorduğu soru
            session_id = data.get('session_id')  # hangi sohbet odasında olduğu

            # oturum yönetimi
            if session_id:
                # eğer frontend bir id gönderdiyse mevcut oturumu bul
                session = ChatSession.objects.get(id=session_id)
            else:
                title = user_question[:40] + ("..." if len(user_question) > 40 else "")
                session = ChatSession.objects.create(title=title)

            # soruyu vektörize etme
            question_embedding = None
            try:
                # kullanıcının sorusunu veritabanında arayabilmek için ollama ya gönderip vektöre çeviriyoruz
                embed_response = requests.post('http://llm:11434/api/embeddings', json={
                    "model": "nomic-embed-text",
                    "prompt": user_question
                })
                question_embedding = embed_response.json().get('embedding')
            except Exception as e:
                print(f"Soru vektöre çevrilemedi: {e}")

            # semantik arama
            if question_embedding:
                # pgvector eklentisinin CosineDistance özelliğini kullanıyoruz
                # kullanıcının sorusunun vektörü ile veritabanındaki verilerin vektörleri arasındaki açıyı ölçer
                # en benzer ilk 8 parçayı getirir
                acibadem_data = AcibademData.objects.filter(embedding__isnull=False).order_by(
                    CosineDistance('embedding', question_embedding)
                )[:8]
            else:
                # vektörleme başarısız olursa mecburen rastgele ilk 8 veriyi alır
                acibadem_data = AcibademData.objects.all()[:8]

            # bulunan bu 8 parçayı alt alta ekleyerek yapay zekaya sunacağımız tek bir context metni oluşturuyoruz
            context_text = "\n\n".join([f"--- {item.title} ---\n{item.content}" for item in acibadem_data])

            # sohbet geçmişini
            # modelin çok uzayıp kafasının karışmaması için sadece aynı son 5 mesajı alıyoruz
            recent_chats = session.messages.all().order_by('-created_at')[:5]
            history_text = ""
            if recent_chats:
                # order_by ile yeniden eskiye çektik ama metne yazarken eskiden yeniye akması için reversed() kullanıyoruz
                for chat in reversed(recent_chats):
                    history_text += f"Kullanıcı: {chat.user_message}\nAsistan: {chat.ai_response}\n\n"
            else:
                history_text = "Bu oturumdaki ilk konuşmamız."

            # prompt
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

            # ollama api sine istek
            ollama_url = "http://llm:11434/api/generate"
            payload = {
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": True,  # cevap stream
                "options": {
                    "temperature": 0.8,
                    # yaratıcılık seviyesi
                    "top_p": 0.4  # modelin seçeceği kelimelerin olasılık havuzunu
                }
            }

            # streaming
            def stream_response():
                full_response = ""  # gelen kelimeleri burada biriktir

                # stream=True ile bağlantıyı açık tutarak istek atıyoruz
                with requests.post(ollama_url, json=payload, stream=True) as r:
                    r.raise_for_status()
                    for line in r.iter_lines():
                        if line:
                            # ollama dan gelen her bir satır JSON formatındadır utf 8 e decode et
                            decoded_line = json.loads(line.decode('utf-8'))
                            chunk = decoded_line.get("response", "")  # gelen kelime
                            full_response += chunk
                            yield chunk  # Bu kelimeyi anında tarayıcıya (frontend'e) fırlat

                # yapay zeka susunca biriken tüm metni veritabanına kalıcı olarak kaydediyoruz
                ChatMessage.objects.create(
                    session=session,
                    user_message=user_question,
                    ai_response=full_response
                )

            # yanıtı frontende gönderme
            # standart JsonResponse yerine StreamingHttpResponse kullanıyoruz (her kelime geldiğinde yineleyerek ekrana basmak için)
            response = StreamingHttpResponse(stream_response(), content_type='text/plain')

            # frontend eğer yeni bir sohbette ise yeni oluşturulan id yi bilsin ve url yi falan güncelleyebilsin diye header içine id ekliyoruz
            response['X-Session-ID'] = str(session.id)
            return response

        except Exception as e:
            # backend de veya yapay zekada bir çökme olursa frontend e durumu bildir
            return JsonResponse({'error': f"Yapay zeka sunucusuna ulaşılamadı: {str(e)}"}, status=500)

    # POST dışındaki istekleri (GET vb.) reddet
    return JsonResponse({'error': 'Geçersiz istek tipi.'}, status=400)

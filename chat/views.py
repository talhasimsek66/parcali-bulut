import requests
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from scraper.models import AcibademData
from .models import ChatMessage, ChatSession
from django.db.models import Q
from pgvector.django import CosineDistance

# 1. Ana Arayüz: Sol menüde listelenmek üzere tüm geçmiş sohbetleri gönderir
def chat_interface(request):
    sessions = ChatSession.objects.all().order_by('-created_at')
    return render(request, 'chat/index.html', {'sessions': sessions})

# 2. Geçmişi Getir: Sol menüden bir sohbete tıklandığında o sohbetin mesajlarını yükler
def get_chat_history(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    messages = session.messages.all().order_by('created_at')
    history = [
        {
            'user_message': msg.user_message,
            'ai_response': msg.ai_response
        } for msg in messages
    ]
    return JsonResponse({'messages': history})

# 3. Chat API: Akış (Streaming) desteği ve oturum yönetimi ile asıl işlemi yapar
@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_question = data.get('question', '')
            session_id = data.get('session_id')  # Frontend'den gelen oturum ID'si

            # --- A. OTURUM YÖNETİMİ ---
            # Eğer session_id yoksa (yeni sohbetse) yeni bir oturum oluştur
            if session_id:
                session = ChatSession.objects.get(id=session_id)
            else:
                # İlk sorudan otomatik bir başlık oluştur (Gemini mantığı)
                title = user_question[:40] + ("..." if len(user_question) > 40 else "")
                session = ChatSession.objects.create(title=title)

            # --- B. VEKTÖREL ARAMA (RAG) ---
            question_embedding = None
            try:
                # Kullanıcının sorusunu Ollama üzerinden vektöre çeviriyoruz
                embed_response = requests.post('http://llm:11434/api/embeddings', json={
                    "model": "nomic-embed-text",
                    "prompt": user_question
                })
                question_embedding = embed_response.json().get('embedding')
            except Exception as e:
                print(f"Vektörleştirme hatası: {e}")

            # pgvector ile anlamsal olarak en yakın 8 döküman parçasını getir
            if question_embedding:
                acibadem_data = AcibademData.objects.filter(embedding__isnull=False).order_by(
                    CosineDistance('embedding', question_embedding)
                )[:8]
            else:
                acibadem_data = AcibademData.objects.all()[:8]

            context_text = "\n\n".join([f"--- {item.title} ---\n{item.content}" for item in acibadem_data])

            # --- C. BELLEK (SESSION HISTORY) ---
            # SADECE bu oturuma ait son 5 mesajı çekerek yapay zekaya "bağlam" olarak veriyoruz
            recent_chats = session.messages.all().order_by('-created_at')[:5]
            history_text = ""
            if recent_chats:
                for chat in reversed(recent_chats):
                    history_text += f"Kullanıcı: {chat.user_message}\nAsistan: {chat.ai_response}\n\n"
            else:
                history_text = "Bu oturumdaki ilk konuşmamız."

            # --- D. PROMPT HAZIRLIĞI ---
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

            # --- E. OLLAMA STREAMING ---
            ollama_url = "http://llm:11434/api/generate"
            payload = {
                "model": "qwen2.5:3b",
                "prompt": prompt,
                "stream": True
            }

            def stream_response():
                full_ai_response = ""
                with requests.post(ollama_url, json=payload, stream=True) as r:
                    r.raise_for_status()
                    for line in r.iter_lines():
                        if line:
                            decoded_line = json.loads(line.decode('utf-8'))
                            chunk = decoded_line.get("response", "")
                            full_ai_response += chunk
                            yield chunk  # Kelime kelime ön yüze fırlat

                # Tüm akış bittiğinde, diyaloğu bu oturuma (session) kaydet
                ChatMessage.objects.create(
                    session=session,
                    user_message=user_question,
                    ai_response=full_ai_response
                )

            # Yanıt header kısmına session_id ekliyoruz ki frontend yeni sohbetin ID'sini bilsin
            response = StreamingHttpResponse(stream_response(), content_type='text/plain')
            response['X-Session-ID'] = str(session.id)
            return response

        except Exception as e:
            return JsonResponse({'error': f"Sunucu hatası: {str(e)}"}, status=500)

    return JsonResponse({'error': 'Geçersiz istek tipi.'}, status=400)

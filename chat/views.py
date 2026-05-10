import requests
import json
from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from scraper.models import AcibademData
from .models import ChatMessage
from django.db.models import Q
from pgvector.django import CosineDistance

def chat_interface(request):
    return render(request, 'chat/index.html')

@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_question = data.get('question', '')

            question_embedding = None
            try:
                embed_response = requests.post('http://llm:11434/api/embeddings', json={
                    "model": "nomic-embed-text",
                    "prompt": user_question
                })
                question_embedding = embed_response.json().get('embedding')
            except Exception as e:
                print(f"Soru vektöre çevrilemedi: {e}")

            if question_embedding:
                acibadem_data = AcibademData.objects.filter(embedding__isnull=False).order_by(
                    CosineDistance('embedding', question_embedding)
                )[:8]
            else:
                acibadem_data = AcibademData.objects.all()[:8]

            context_text = "\n\n".join([f"--- {item.title} ---\n{item.content}" for item in acibadem_data])

            recent_chats = ChatMessage.objects.order_by('-created_at')[:3]
            history_text = ""
            if recent_chats:
                for chat in reversed(recent_chats):
                    history_text += f"Kullanıcı: {chat.user_message}\nAsistan: {chat.ai_response}\n\n"
            else:
                history_text = "Bu ilk konuşmamız, henüz geçmiş yok."

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

            ollama_url = "http://llm:11434/api/generate"
            payload = {
                "model": "qwen2.5:3b",
                "prompt": prompt,
                "stream": True
            }

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
                    user_message=user_question,
                    ai_response=full_response
                )

            return StreamingHttpResponse(stream_response(), content_type='text/plain')

        except Exception as e:
            return JsonResponse({'error': f"Yapay zeka sunucusuna ulaşılamadı: {str(e)}"}, status=500)

    return JsonResponse({'error': 'Geçersiz istek tipi.'}, status=400)

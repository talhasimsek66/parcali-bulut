import requests
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from scraper.models import AcibademData
from .models import ChatMessage
from django.db.models import Q
from .faq import FAQ_DATA


def chat_interface(request):
    return render(request, 'chat/index.html')


@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_question = data.get('question', '')

            # ÖZEL SORU (FAQ) KONTROLÜ
            user_lower = user_question.lower()
            for item in FAQ_DATA:
                if any(keyword in user_lower for keyword in item["keywords"]):
                    return JsonResponse({
                        "answer": item["answer"]
                    })

            # keyword çıkar
            keywords = [word for word in user_question.lower().split() if len(word) > 3]

            query = Q()
            for word in keywords:
                query |= Q(content__icontains=word) | Q(title__icontains=word)

            # tüm sonuçları al
            results = AcibademData.objects.filter(query).distinct()

            # ranking sistemi
            scored_results = []
            for item in results:
                score = 0
                for word in keywords:
                    if word in item.title.lower():
                        score += 3
                    if word in item.content.lower():
                        score += 1
                scored_results.append((score, item))

            scored_results.sort(key=lambda x: x[0], reverse=True)

            # dynamic context
            if len(user_question) < 30:
                top_k = 2
            elif len(user_question) < 80:
                top_k = 3
            else:
                top_k = 5

            acibadem_data = [item for score, item in scored_results[:top_k]]

            # fallback
            if not acibadem_data:
                acibadem_data = list(AcibademData.objects.all()[:top_k])

            # context oluştur
            context_text = "\n\n".join([
                f"--- {item.title} ---\n{item.content[:2500]}"
                for item in acibadem_data
            ])

            # chat history
            recent_chats = ChatMessage.objects.order_by('-created_at')[:3]
            history_text = ""

            if recent_chats:
                for chat in reversed(recent_chats):
                    history_text += f"Kullanıcı: {chat.user_message}\nAsistan: {chat.ai_response}\n\n"
            else:
                history_text = "Bu ilk konuşmamız, henüz geçmiş yok."

            # prompt
            prompt = f"""Sen Acıbadem Üniversitesi için tasarlanmış resmi ve yardımsever bir yapay zeka asistanısın. 
Aşağıda sana üniversitenin web sitesinden toplanmış bazı güncel bilgiler (Context) ve önceki konuşmalarımız (Geçmiş) veriliyor. 

SADECE bu verilere dayanarak cevap ver.
Eğer bilgi yoksa kesinlikle uydurma.

[GEÇMİŞ]
{history_text}

[CONTEXT]
{context_text}

Soru: {user_question}
Cevap:"""

            # LLM isteği
            ollama_url = "http://llm:11434/api/generate"
            payload = {
                "model": "qwen2.5:3b",
                "prompt": prompt,
                "stream": False
            }

            response = requests.post(ollama_url, json=payload)
            response.raise_for_status()

            ai_answer = response.json().get('response', '')

            # cevap kontrolü
            if not ai_answer or len(ai_answer.strip()) < 20:
                ai_answer = "Bu konu hakkında elimde yeterli ve güvenilir bilgi bulunmuyor."
            elif any(x in ai_answer.lower() for x in ["bilmiyorum", "emin değilim", "kesin değil"]):
                ai_answer = "Bu konu hakkında elimde yeterli ve güvenilir bilgi bulunmuyor."

            # kaydet
            ChatMessage.objects.create(
                user_message=user_question,
                ai_response=ai_answer
            )

            return JsonResponse({'answer': ai_answer})

        except Exception as e:
            return JsonResponse({'error': f"Yapay zeka sunucusuna ulaşılamadı: {str(e)}"}, status=500)

    return JsonResponse({'error': 'Geçersiz istek tipi.'}, status=400)
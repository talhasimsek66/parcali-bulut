import requests
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from scraper.models import AcibademData
from .models import ChatMessage, ChatSession
from django.db.models import Q
from .faq import FAQ_DATA


def chat_interface(request):
    return render(request, 'chat/index.html')


@require_GET
def get_session_messages(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id)
        messages = session.messages.order_by('created_at')

        data = [
            {
                "user": m.user_message,
                "ai": m.ai_response
            }
            for m in messages
        ]

        return JsonResponse({"messages": data})

    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session bulunamadı"}, status=404)


@require_GET
def chat_sessions(request):
    sessions = ChatSession.objects.all().order_by('-created_at')

    data = [
        {
            "id": s.id,
            "title": s.title
        }
        for s in sessions
    ]

    return JsonResponse({"sessions": data})


@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_question = data.get('question', '').strip()

            if not user_question:
                return JsonResponse({"error": "Boş soru gönderilemez"}, status=400)

            session_id = data.get('session_id')

            if session_id:
                try:
                    session = ChatSession.objects.get(id=session_id)
                except ChatSession.DoesNotExist:
                    session = ChatSession.objects.create(title=user_question[:30])
            else:
                session = ChatSession.objects.create(title=user_question[:30])

            user_lower = user_question.lower()
            for item in FAQ_DATA:
                if any(keyword in user_lower for keyword in item["keywords"]):
                    ai_answer = item["answer"]

                    ChatMessage.objects.create(
                        session=session,
                        user_message=user_question,
                        ai_response=ai_answer
                    )

                    return JsonResponse({
                        "answer": ai_answer,
                        "session_id": session.id
                    })

            keywords = [word for word in user_lower.split() if len(word) > 3]

            query = Q()
            for word in keywords:
                query |= Q(content__icontains=word) | Q(title__icontains=word)

            results = AcibademData.objects.filter(query).distinct()

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

            if len(user_question) < 30:
                top_k = 2
            elif len(user_question) < 80:
                top_k = 3
            else:
                top_k = 5

            acibadem_data = [item for score, item in scored_results[:top_k]]

            if not acibadem_data:
                context_text = "SORU İLE İLGİLİ VERİTABANINDA BİLGİ BULUNAMADI."
            else:
                context_text = "\n\n".join([
                    f"--- {item.title} ---\n{item.content[:2500]}"
                    for item in acibadem_data
                ])

            recent_chats = ChatMessage.objects.filter(session=session).order_by('-created_at')[:3]

            history_text = ""
            if recent_chats:
                for chat in reversed(recent_chats):
                    history_text += f"Kullanıcı: {chat.user_message}\nAsistan: {chat.ai_response}\n\n"
            else:
                history_text = "Bu ilk konuşmamız, henüz geçmiş yok."

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

            response = requests.post(
                "http://llm:11434/api/generate",
                json={
                    "model": "qwen2.5:3b",
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()

            ai_answer = response.json().get('response', '')

            if not ai_answer or len(ai_answer.strip()) < 20:
                ai_answer = "Bu konu hakkında elimde yeterli ve güvenilir bilgi bulunmuyor."
            elif any(x in ai_answer.lower() for x in ["bilmiyorum", "emin değilim", "kesin değil"]):
                ai_answer = "Bu konu hakkında elimde yeterli ve güvenilir bilgi bulunmuyor."

            ChatMessage.objects.create(
                session=session,
                user_message=user_question,
                ai_response=ai_answer
            )

            return JsonResponse({
                "answer": ai_answer,
                "session_id": session.id
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Geçersiz istek tipi.'}, status=400)
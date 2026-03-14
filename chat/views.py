import requests
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from scraper.models import AcibademData
from .models import ChatMessage
from django.db.models import Q


# kullanıcıların sohbet edeceği sayfa
def chat_interface(request):
    return render(request, 'chat/index.html')


# 2. yapay zeka ile haberleşen api
@csrf_exempt  # şimdilik api testini kolaylaştırmak için CSRF esnetme (uygulamalar arası geçişte problem yaratabiliyor)
def chat_api(request):
    if request.method == 'POST':
        try:
            # kullanıcının gönderdiği soruyu al
            data = json.loads(request.body)
            user_question = data.get('question', '')

            # kullanıcının sorusundaki kelimeleri ayır ve 3 harften büyükleri al
            keywords = [word for word in user_question.lower().split() if len(word) > 3]

            query = Q()
            for word in keywords:
                # hem sayfa başlığında hem de içerikte bu kelimeleri ara
                query |= Q(content__icontains=word) | Q(title__icontains=word)

            # sorudaki kelimelerle eşleşen en alakalı 3 sayfayı getir (şimdilik 3 sayfa)
            acibadem_data = AcibademData.objects.filter(query).distinct()[:3]

            # eğer sorulan kelimelerle ilgili hiçbir sayfa bulamazsa genel bilgi vermek için rastgele 3 sayfa al
            if not acibadem_data.exists():
                acibadem_data = AcibademData.objects.all()[:3]

            # bulunan sayfaların ilk 2500 karakterini al
            context_text = "\n\n".join([f"--- {item.title} ---\n{item.content[:2500]}" for item in acibadem_data])

            # sohbet geçmişi /*/*/*/*/*/*/*/*
            # database den son 3 sohbeti al (eskiden yeniye)
            recent_chats = ChatMessage.objects.order_by('-created_at')[:3]
            history_text = ""
            if recent_chats:
                for chat in reversed(recent_chats):
                    history_text += f"Kullanıcı: {chat.user_message}\nAsistan: {chat.ai_response}\n\n"
            else:
                history_text = "Bu ilk konuşmamız, henüz geçmiş yok."

            # yapay zekaya kim olduğunu ve elindeki verileri söylüyoruz
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

            # llm */*/*/*/**/*/*/
            # dockerdeki lokal llm e yolla
            ollama_url = "http://llm:11434/api/generate"
            payload = {
                "model": "qwen2.5:3b",  # indirdiğim modelin tam adı
                "prompt": prompt,
                "stream": False  # cevabı kelime kelime değil tek seferde bütün olarak almak için
            }

            response = requests.post(ollama_url, json=payload)
            response.raise_for_status()  # eğer sunucudan hata dönerse tut

            ai_answer = response.json().get('response', '')

            ChatMessage.objects.create(   # sohbeti database e kaydet
                user_message=user_question,
                ai_response=ai_answer
            )

            return JsonResponse({'answer': ai_answer})

        except Exception as e:
            return JsonResponse({'error': f"Yapay zeka sunucusuna ulaşılamadı: {str(e)}"}, status=500)

    return JsonResponse({'error': 'Geçersiz istek tipi.'}, status=400)

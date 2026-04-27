import requests
import json
import os
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from scraper.models import AcibademData
from .models import ChatMessage
from django.db.models import Q

# --- RAG İÇİN EKLENENLER ---
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
# ---------------------------

def chat_interface(request):
    return render(request, 'chat/index.html')


@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_question = data.get('question', '')

            # ==========================================================
            # SEMANTİK RAG (Vektör Arama)
            # ==========================================================
            docs = []
            try:
                # 1. Embedding modelini tanımla
                embeddings = OllamaEmbeddings(
                    model="nomic-embed-text",
                    base_url="http://llm:11434"
                )

                # 2. FAISS Index'i yükle
                if os.path.exists("faiss_index"):
                    vector_db = FAISS.load_local(
                        "faiss_index", 
                        embeddings, 
                        allow_dangerous_deserialization=True
                    )

                    # 3. Benzerlik araması yap
                    docs = vector_db.similarity_search(user_question, k=10)
                else:
                    print("Hata: faiss_index klasörü bulunamadı.")
            except Exception as rag_error:
                print(f"RAG Hatası: {rag_error}")

            # 🔹 Context'i daha net ayırarak oluştur
            context_text = ""
            if docs:
                for i, doc in enumerate(docs):
                    context_text += f"[KAYNAK {i+1}]: {doc.page_content}\n\n"
            else:
                context_text = "Acıbadem Üniversitesi hakkında yeterli bağlam bilgisi bulunamadı."

            # 🔹 prompt (Optimize Edilmiş)
            prompt = f"""Aşağıdaki kaynakları kullanarak soruyu çok kısa (en fazla 15 kelime) cevapla.

{context_text}

TALİMATLAR:
1. "Bölüm Başkanı", "Sorumlu" veya "Adres" gibi spesifik başlıkları kaynaklar içerisinde ara.
2. Sadece sorulan kişiyi veya bilgiyi söyle.
3. Bilgi yoksa "Bu bilgiye sahip değilim." de.

Soru: {user_question}
Cevap:"""

            # 🔹 LLM isteği (Daha kısıtlayıcı)
            ollama_url = "http://llm:11434/api/generate"
            payload = {
                "model": "qwen2.5:3b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 80,   # Cevabı çok daha kısa kes
                    "temperature": 0.1,  # Halüsinasyonu minimize et
                    "top_p": 0.1
                }
            }

            response = requests.post(ollama_url, json=payload)
            response.raise_for_status()

            ai_answer = response.json().get('response', '')

            # CONFIDENCE CONTROL
            if not ai_answer or len(ai_answer.strip()) < 5:
                ai_answer = "Bu konu hakkında şu an için yeterli bilgiye sahip değilim."
            
            # 🔹 kaydet
            ChatMessage.objects.create(
                user_message=user_question,
                ai_response=ai_answer
            )

            return JsonResponse({'answer': ai_answer})

        except Exception as e:
            return JsonResponse({'error': f"Sunucu hatası: {str(e)}"}, status=500)

    return JsonResponse({'error': 'Geçersiz istek tipi.'}, status=400)

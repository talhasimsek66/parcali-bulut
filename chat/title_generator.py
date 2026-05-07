def generate_chat_title(question):
    original_question = question
    question = question.lower()

    categories = {

        "📍 Kampüs ve Ulaşım": [
            "adres", "konum", "kampüs", "ulaşım", "servis",
            "metro", "yol", "harita", "lokasyon", "otobüs",
            "durak", "güzergah", "ataşehir", "yerleşke"
        ],

        "💻 Bilgisayar Mühendisliği": [
            "bilgisayar", "yazılım", "python", "java", "c++",
            "algoritma", "kod", "programlama", "backend",
            "frontend", "django", "yapay zeka", "ai",
            "machine learning", "veri bilimi", "ceng",
            "deep learning", "veritabanı", "api"
        ],

        "🩺 Sağlık ve Tıp": [
            "tıp", "doktor", "sağlık", "hemşirelik",
            "eczacılık", "hastane", "ameliyat", "diş",
            "fizyoterapi", "medikal", "hasta",
            "laboratuvar", "biyomedikal"
        ],

        "🌍 Erasmus ve Yurtdışı": [
            "erasmus", "exchange", "yurtdışı", "vize",
            "pasaport", "hibe", "avrupa", "norveç",
            "başvuru", "değişim", "schengen",
            "almanya", "italya", "ispanya"
        ],

        "📚 Ders ve Sınav": [
            "ders", "vize", "final", "quiz", "sınav",
            "not", "ortalama", "ödev", "obs",
            "akademik takvim", "bütünleme",
            "devamsızlık", "sunum", "proje ödevi"
        ],

        "💰 Ücret ve Burs": [
            "ücret", "burs", "fiyat", "ödeme",
            "taksit", "indirim", "öğrenim",
            "harç", "para", "ücretlendirme"
        ],

        "📝 Öğrenci İşleri": [
            "kayıt", "dondurma", "silme",
            "başvuru", "transkript", "mezuniyet",
            "yatay geçiş", "çift anadal",
            "cap", "öğrenci işleri"
        ],

        "🏠 Kampüs Yaşamı": [
            "yurt", "konaklama", "oda",
            "yemekhane", "kafeterya",
            "kulüp", "sosyal", "etkinlik",
            "kampüs hayatı", "spor", "fitness"
        ],

        "📖 Kütüphane ve Araştırma": [
            "kütüphane", "kitap", "makale",
            "database", "yayın", "araştırma",
            "tez", "dergi", "kaynak"
        ],

        "🚀 Kariyer ve Staj": [
            "staj", "kariyer", "iş",
            "cv", "linkedin", "mülakat",
            "çalışma", "iş başvurusu",
            "kariyer merkezi"
        ],

        "🧪 Laboratuvar ve Projeler": [
            "laboratuvar", "proje", "deney",
            "arduino", "robotik", "tez projesi"
        ],

        "📅 Akademik Takvim": [
            "takvim", "başlangıç", "tatil",
            "ders başlangıcı", "yaz okulu"
        ],

        "🏥 Hastane ve Klinik": [
            "klinik", "acıbadem hastanesi",
            "muayene", "poliklinik"
        ],

        "🎓 Mezuniyet ve Diploma": [
            "mezuniyet", "diploma",
            "kep", "mezun", "tören"
        ]
    }

    ignored_words = [
        "nedir", "nasıl", "hangi", "kaç",
        "neden", "için", "olan", "ve",
        "ile", "ama", "fakat", "şey",
        "bir", "bu", "şu", "acaba",
        "yardım", "hakkında", "olarak",
        "daha", "çok", "az", "mı",
        "mi", "mu", "mü", "var",
        "yok", "gibi"
    ]

    meaningful_words = [
        word.capitalize()
        for word in original_question.split()
        if len(word) > 3 and word.lower() not in ignored_words
    ]

    # Önce kategori kontrolü
    for title, keywords in categories.items():

        if any(word in question for word in keywords):

            extra = ""

            for word in meaningful_words:

                # başlığın içinde geçen kelimeyi tekrar kullanma
                if word.lower() not in title.lower():
                    extra = f" - {word}"
                    break

            final_title = f"{title}{extra}"

            return final_title[:45]

    # Eğer kategori bulunamazsa
    if meaningful_words:

        final_title = f"🧠 {' '.join(meaningful_words[:3])}"

        return final_title[:45]

    return "🧠 Genel Akademik Sohbet"[:45]
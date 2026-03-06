import os
import asyncio
import threading
import logging
import re
from flask import Flask
from telethon import TelegramClient, events, Button

# ================== إعداد التسجيل ==================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ================== سيرفر الويب ==================
app = Flask(__name__)

@app.route('/')
def home():
    return "رادار الرصد الذكي (نسخة نهائية) يعمل بنجاح!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ================== متغيرات البيئة ==================
API_ID = int(os.environ.get("API_ID", 2040))
API_HASH = os.environ.get("API_HASH", "b18441a1ff607e10a989891a5462e627")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL", "student1_admin")
SCORE_THRESHOLD = int(os.environ.get("SCORE_THRESHOLD", 3))

# ================== الحسابات ==================
accounts = [
    {'name': 'رادار [1]', 'id': API_ID, 'hash': API_HASH, 'session': 'session_name'},
    {'name': 'رادار [2]', 'id': API_ID, 'hash': API_HASH, 'session': 'session_2'}
]

# ================== قوائم الأوزان ==================
keyword_weights = {
    # كلمات طلب قوية (وزن +3)
    'واجب': 3, 'حل': 3, 'مشروع': 3, 'بحث': 3, 'كويز': 3, 'اختبار': 3,
    'تخرج': 3, 'مهندس': 3, 'تصميم': 3, 'برمجة': 3, 'كود': 3, 'ترجمة': 3,
    'خصوصي': 3, 'معلم': 3, 'مقرر': 3, 'كتاب': 3, 'مرجع': 3,
    'عذر': 3, 'غياب': 3, 'مرضية': 3, 'سكليف': 4, 'تجسير': 4,
    'تأجيل': 3, 'انسحاب': 4,
    # كلمات طلب متوسطة (وزن +2)
    'أبغى': 2, 'ابي': 2, 'احتاج': 2, 'ممكن': 2, 'يعرف': 2, 'يفيدني': 2,
    'شرح': 2, 'ملخص': 2, 'مذكرة': 2, 'تمارين': 2, 'نموذج': 2,
    'حد': 2, 'دوام': 2, 'تسجيل': 2, 'اعادة': 2,
    # كلمات استفسار خفيفة (وزن +1)
    'مين': 1, 'كيف': 1, 'متى': 1, 'وش': 1, 'ايش': 1, 'شنو': 1,
    'تكفون': 1, 'ساعدوني': 1, 'بالله': 1, 'لو سمحتو': 1,
    # كلمات إعلان (وزن سالب)
    'تواصل': -5, 'واتساب': -5, 'واتس': -5, 'للتواصل': -5,
    'درجة كاملة': -5, 'عرض خاص': -4, 'ضمان': -3, 'استثمار': -3,
    'راسلني': -3, 'موجود حل': -3, 'يوجد حل': -3, 'متوفر حل': -3,
}

# قائمة السياق الأكاديمي
academic_context = [
    'فيزياء', 'كيمياء', 'رياضيات', 'أحياء', 'عربي', 'انجليزي',
    'تاريخ', 'جغرافيا', 'فلسفة', 'منطق', 'إحصاء', 'محاسبة',
    'اقتصاد', 'قانون', 'طب', 'هندسة', 'تقنية', 'برمجة',
    'مادة', 'مقرر', 'كتاب', 'مرجع', 'خصوصي', 'دروس', 'معلم',
    'عذر', 'غياب', 'مرضية', 'سكليف', 'تجسير', 'دوام', 'تسجيل'
]

# كلمات مستبعدة
exclusion_words = [
    'الله', 'الرسول', 'الدين', 'الإسلام', 'المسلم', 'القرآن',
    'سبحان', 'الحمد', 'الشكر', 'الدعاء', 'الآية', 'السورة',
    'الموت', 'الحياة', 'الروح', 'القلب', 'النفس', 'الإنسان'
]

# ================== منع التكرار ==================
sent_messages = set()
MAX_SENT_IDS = 10000

# ================== دوال مساعدة ==================
def normalize_arabic(text):
    text = re.sub(r'[إأآ]', 'ا', text)
    text = re.sub(r'[ة]', 'ه', text)
    text = re.sub(r'[ًٌٍَُِّْ]', '', text)
    return text

def calculate_score(text):
    text_norm = normalize_arabic(text.lower())
    words = text_norm.split()
    score = 0
    matched_words = []
    for word in words:
        if word in keyword_weights:
            score += keyword_weights[word]
            matched_words.append(word)
    for ctx in academic_context:
        if ctx in text_norm:
            score += 2
            matched_words.append(f"[سياق]{ctx}")
            break
    for ex in exclusion_words:
        if ex in text_norm:
            score -= 3
            matched_words.append(f"[مستبعد]{ex}")
    return score, matched_words

def is_likely_question(text):
    patterns = [
        r'(هل|ما|من|متى|أين|كيف|لماذا|كم)\s+\S+',
        r'(مين|وش|ايش|شنو)\s+\S+',
        r'(\S+\s+)?(يعرف|يفيدني|يشرح|يساعد)\s+\S+',
        r'(تكفون|ساعدوني|بالله|لو سمحتو)',
        r'.*\?$|.*؟$'
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False

def contains_link(text):
    link_patterns = [
        r'https?://\S+',
        r'www\.\S+',
        r't\.me/\S+',
        r'wa\.me/\S+',
        r'bit\.ly/\S+',
        r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/\S*)?'
    ]
    text_lower = text.lower()
    for pattern in link_patterns:
        if re.search(pattern, text_lower):
            return True
    return False

def contains_phone_number(text):
    cleaned = re.sub(r'[\s\-\(\)\+]', '', text)
    if re.search(r'\d{10,15}', cleaned):
        return True
    return False

def is_duplicate(chat_id, message_id):
    msg_id = f"{chat_id}:{message_id}"
    if msg_id in sent_messages:
        return True
    sent_messages.add(msg_id)
    if len(sent_messages) > MAX_SENT_IDS:
        sent_messages.pop()
    return False

# ================== دالة الرصد الرئيسية ==================
async def start_monitoring(acc_info):
    client = TelegramClient(acc_info['session'], acc_info['id'], acc_info['hash'])
    radar_name = acc_info['name']

    @client.on(events.NewMessage)
    async def handler(event):
        try:
            if event.is_private:
                return

            # منع التكرار
            if is_duplicate(event.chat_id, event.id):
                return

            text = event.raw_text.strip()
            # ✅ شرط الطول: لا تقل عن 5 ولا تزيد عن 110 حرف
            if not text or len(text) < 5 or len(text) > 110:
                return

            # منع الروابط
            if contains_link(text):
                return

            # منع أرقام الهواتف
            if contains_phone_number(text):
                return

            # حساب النقاط
            score, matched = calculate_score(text)
            logger.debug(f"{radar_name} - score: {score}, matched: {matched}")

            if score < SCORE_THRESHOLD and not is_likely_question(text):
                return

            sender = await event.get_sender()
            chat = await event.get_chat()
            username = getattr(sender, 'username', None)
            user_display = f"@{username}" if username else "بدون يوزر"
            first_name = getattr(sender, 'first_name', 'مستخدم')
            chat_title = getattr(chat, 'title', 'مجموعة')

            matched_str = ', '.join(matched) if matched else 'لا يوجد'

            display_message = (
                f"⚡️ **رصد جديد عبر {radar_name}**\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"👤 **العميل:** {first_name} ( {user_display} )\n"
                f"🆔 **ID:** `{sender.id}`\n"
                f"📍 **المصدر:** `{chat_title}`\n"
                f"🔗 [انتقل للرسالة الأصلية](https://t.me/c/{chat.id}/{event.id})\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"📝 **النص المرصود:**\n"
                f"_{text}_\n"  # النص الآن ضمن 110 حرف
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"**النقاط:** {score} | **الكلمات:** {matched_str}\n"
                f"👇 **تواصل مع العميل مباشرة:**"
            )

            buttons_list = []
            if username:
                buttons_list.append([Button.url("💬 مراسلة خاصة", f"https://t.me/{username}")])
            buttons_list.append([Button.url("⤴️ الرد في المجموعة", f"https://t.me/c/{chat.id}/{event.id}")])

            await client.send_message(TARGET_CHANNEL, display_message, buttons=buttons_list, silent=False)

        except Exception as e:
            logger.error(f"خطأ في {radar_name}: {e}")

    # تشغيل العميل مع إعادة اتصال تلقائية
    while True:
        try:
            await client.start()
            logger.info(f"✅ {radar_name} بدأ العمل...")
            await client.run_until_disconnected()
        except Exception as e:
            logger.error(f"❗ {radar_name} انقطع: {e}. إعادة المحاولة بعد 5 ثوان...")
            await asyncio.sleep(5)
        finally:
            await client.disconnect()

# ================== التشغيل الرئيسي ==================
async def main():
    tasks = [start_monitoring(acc) for acc in accounts]
    await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت يدوياً.")

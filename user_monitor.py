# ================== رادار الرصد الذكي لطلبات الطلاب ==================
# ================== النسخة النهائية مع StringSession ==================

import os
import sys
import re
import asyncio
import threading
import logging
from datetime import datetime
from collections import deque
from flask import Flask
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession  # <-- مهم جداً

# ================== 1. إعداد التسجيل (Logging) ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('radar.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ================== 2. سيرفر الويب (Flask) ==================
app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    <h1>🎓 رادار الرصد الذكي</h1>
    <p>✅ النظام يعمل بنجاح!</p>
    <p>📊 الحالة: متصل ويعمل</p>
    <p>🕐 آخر تحديث: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    """

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()
logger.info("✅ سيرفر الويب يعمل على المنفذ 10000")

# ================== 3. متغيرات البيئة والأمان ==================
def get_required_env(var_name, default=None, required=True):
    """دالة آمنة لجلب متغيرات البيئة"""
    value = os.environ.get(var_name, default)
    if required and (value is None or value == default):
        logger.error(f"❌ متغير البيئة '{var_name}' مطلوب ولم يتم تحديده!")
        sys.exit(1)
    return value

# البيانات الأساسية (تأكد من وضعها في متغيرات البيئة)
API_ID = int(get_required_env("API_ID", "2040"))
API_HASH = get_required_env("API_HASH", "b18441a1ff607e10a989891a5462e627")
TARGET_CHANNEL = get_required_env("TARGET_CHANNEL", "student1_admin")

# قراءة الجلسات النصية من متغيرات البيئة (اختياري لكل حساب)
SESSION_1 = os.environ.get("SESSION_1")
SESSION_2 = os.environ.get("SESSION_2")

# إعدادات الرصد
SCORE_THRESHOLD = int(os.environ.get("SCORE_THRESHOLD", "4"))
MIN_MESSAGE_LENGTH = int(os.environ.get("MIN_MSG_LENGTH", "5"))
MAX_MESSAGE_LENGTH = int(os.environ.get("MAX_MSG_LENGTH", "70"))

logger.info(f"📋 الإعدادات: عتبة النقاط={SCORE_THRESHOLD}, الطول={MIN_MESSAGE_LENGTH}-{MAX_MESSAGE_LENGTH}")

# ================== 4. الحسابات (User Accounts) مع StringSession ==================
accounts = []
if SESSION_1:
    accounts.append({
        'name': 'رادار [1]',
        'id': API_ID,
        'hash': API_HASH,
        'session': SESSION_1   # نص الجلسة وليس اسم ملف
    })
if SESSION_2:
    accounts.append({
        'name': 'رادار [2]',
        'id': API_ID,
        'hash': API_HASH,
        'session': SESSION_2
    })

if not accounts:
    logger.error("❌ لم يتم توفير أي جلسة! أضف SESSION_1 أو SESSION_2 في متغيرات البيئة.")
    sys.exit(1)

# ================== 5. قوائم الكلمات والأوزان ==================
# 🎯 كلمات الطلبات المباشرة
request_keywords = {
    'عالي': {
        'مطلوب': 5, 'ابغى': 4, 'ابي': 4, 'احتاج': 4, 'أحتاج': 4, 
        'بحث': 4, 'ابحث': 4, 'دور': 3, 'عندي': 3, 'صعوبة': 3, 'ما فهمت': 3
    },
    'متوسط': {
        'واجب': 3, 'حل': 3, 'مشروع': 3, 'بحث': 3, 'كويز': 3, 'اختبار': 3,
        'تخرج': 3, 'مهندس': 3, 'تصميم': 3, 'برمجة': 3, 'كود': 3, 'ترجمة': 3,
        'خصوصي': 3, 'معلم': 3, 'مدرس': 3, 'مقرر': 3, 'كتاب': 3, 'مرجع': 3,
        'عذر': 3, 'غياب': 3, 'مرضية': 3, 'سكليف': 4, 'تجسير': 4,
        'تأجيل': 3, 'انسحاب': 4, 'استاذ': 2, 'دكتور': 2, 'دروس': 2
    },
    'خفيف': {
        'مين': 1, 'كيف': 1, 'متى': 1, 'وش': 1, 'ايش': 1, 'شنو': 1,
        'تكفون': 1, 'ساعدوني': 1, 'بالله': 1, 'لو سمحتو': 1, 'حد': 1,
        'يعرف': 1, 'يفيد': 1, 'ممكن': 1
    }
}

# 🚫 كلمات الإعلانات القاتلة (Kill Switch)
ad_killers = {
    'للتواصل', 'للتسجيل', 'واتساب', 'واتس', 'تواصل', 'راسلني', 'لبيع', 
    'سعر', 'ريال', 'دولار', 'عرض', 'خصم', 'ضمان', 'استثمار', 'ربح', 
    'تسويق', 'اعلان', 'معلن', 'احجز', 'مقعد', 'سارع', 'محدود',
    'يوجد حل', 'متوفر حل', 'موجود حل', 'نحل', 'نحل الواجب', 'نحل التكليف',
    'نضمن', 'درجة كاملة', 'نجاح مضمون', 'توظيف', 'مطلوب معلمين', 
    'مطلوب مدرسين', 'وظيفة', 'مكتب', 'مجموعة', 'قناة', 'لدينا', 'عندنا',
    'نقدم', 'خدماتنا', 'لشراء', 'للبيع', 'سعر', 'ريال', 'دولار', 'جنيه'
}

# ❓ كلمات الاستفسارات
inquiry_keywords = {
    'أدوات استفهام': {
        'كيف': 3, 'متى': 3, 'كم': 2, 'أين': 2, 'من': 2, 'هل': 2,
        'وش': 2, 'ايش': 2, 'شنو': 2, 'ليه': 2, 'لماذا': 2, 'مين': 2
    },
    'أفعال استفسار': {
        'يعرف': 3, 'يفيدني': 3, 'تشرح': 3, 'تشرحون': 3, 'تساعد': 3,
        'أفهم': 2, 'أعرف': 2, 'أتأكد': 2, 'استفسر': 3, 'سؤال': 2, 'سؤالي': 2
    },
    'كلمات إجراء أكاديمي': {
        'أسجل': 4, 'التسجيل': 4, 'شعبة': 3, 'جدول': 3, 'موعد': 3,
        'اختبار': 3, 'امتحان': 3, 'نتيجة': 3, 'رصد': 3, 'غياب': 3,
        'عذر': 3, 'انسحاب': 3, 'تأجيل': 3, 'نظام': 2, 'بوابة': 2, 'منصة': 2
    }
}

# 📚 السياق الأكاديمي
academic_context = [
    'فيزياء', 'كيمياء', 'رياضيات', 'أحياء', 'عربي', 'انجليزي', 'لغة',
    'تاريخ', 'جغرافيا', 'فلسفة', 'منطق', 'إحصاء', 'محاسبة', 'اقتصاد',
    'قانون', 'طب', 'هندسة', 'تقنية', 'برمجة', 'كمبيوتر', 'حاسب',
    'مادة', 'مقرر', 'كتاب', 'مرجع', 'دروس', 'محاضرة', 'محاضرات',
    'واجب', 'تكليف', 'سكليف', 'تجسير', 'دوام', 'تسجيل', 'شعبة', 'جدول',
    'اختبار', 'امتحان', 'نتيجة', 'رصد', 'درجة', 'علامة', 'نسبة', 'معدل',
    'تراكمي', 'فصل', 'ترم', 'سنة', 'سنه', 'جامعة', 'كلية', 'معهد'
]

# كلمات مستبعدة (دينية، عامة جداً)
exclusion_words = [
    'الله', 'الرسول', 'الدين', 'الإسلام', 'المسلم', 'القرآن',
    'سبحان', 'الحمد', 'الشكر', 'الدعاء', 'الآية', 'السورة'
]

# ================== 6. أنماط الكشف الأمني ==================
LINK_PATTERNS = [
    r'https?://\S+',
    r'www\.\S+',
    r't\.me/\S+',
    r'telegram\.me/\S+',
    r'wa\.me/\S+',
    r'whatsapp\.com/\S+',
    r'bit\.ly/\S+',
    r'goo\.gl/\S+',
    r'[a-zA-Z0-9.-]+\.(com|net|org|info|biz|me|io|co|sa|ae|eg)\S*',
    r'\.[a-zA-Z]{2,}(/\S*)?',
    r'\S+@\S+\.\S+',
]

PHONE_PATTERNS = [
    r'\+?\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}',
    r'05\d{8}',
    r'00966\d{9}',
    r'\+966\d{9}',
    r'01\d{8}',
    r'0020\d{9}',
    r'\+20\d{9}',
    r'07\d{8}',
    r'00964\d{9}',
    r'\+964\d{9}',
    r'\d{10,15}',
]

CONTACT_WORDS = [
    'تواصل', 'للتواصل', 'راسلني', 'واتساب', 'واتس', 'wb',
    'سناب', 'انستقرام', 'انستا', 'تويتر', 'فيسبوك',
    'ايميل', 'بريد', 'email', 'call', 'رقم', 'جوال', 'موبايل',
    'للتحميل', 'للتسجيل', 'اضغط هنا', 'link', 'رابط'
]

# ================== 7. منع التكرار (Memory Management) ==================
MAX_SENT_IDS = 10000
sent_messages = deque(maxlen=MAX_SENT_IDS)

def is_duplicate(chat_id, message_id):
    msg_id = f"{chat_id}:{message_id}"
    if msg_id in sent_messages:
        return True
    sent_messages.append(msg_id)
    return False

# ================== 8. دوال المعالجة النصية ==================
def normalize_arabic(text):
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ةه]', 'ه', text)
    text = re.sub(r'[ىي]', 'ي', text)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)  # إزالة التشكيل
    return text.strip().lower()

def contains_link(text):
    text_lower = text.lower()
    found = []
    for pattern in LINK_PATTERNS:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        found.extend(matches)
    for word in CONTACT_WORDS:
        if word in text_lower:
            found.append(f"[{word}]")
    return len(found) > 0, found[:3]

def contains_phone(text):
    cleaned = re.sub(r'[\s\-\(\)\+\.\,]', '', text)
    found = []
    for pattern in PHONE_PATTERNS:
        matches = re.findall(pattern, text)
        found.extend(matches)
    digits = re.sub(r'[^\d]', '', text)
    if len(digits) >= 10:
        found.append(f"[{digits[:15]}]")
    return len(found) > 0, found[:3]

def is_likely_question(text):
    patterns = [
        r'(هل|ما|من|متى|أين|كيف|لماذا|كم)\s+\S+',
        r'(مين|وش|ايش|شنو)\s+\S+',
        r'.*[؟?]$',
        r'\b(يعرف|يفيدني|تشرح|تساعد)\b'
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False

# ================== 9. نظام التحليل والفرز ==================
def calculate_score(text):
    text_norm = normalize_arabic(text)
    words_set = set(text_norm.split())
    
    score = 0
    matched = []
    classification = "غير_مصنف"
    
    # 🔴 الفحص القاتل للإعلانات
    for ad_word in ad_killers:
        if ad_word in text_norm:
            return -100, "إعلان", [f"🚫 {ad_word}"]
    
    # 🟢 كشف الاستفسارات
    inquiry_score = 0
    inquiry_type = None
    
    for word in words_set:
        for k, v in inquiry_keywords['أدوات استفهام'].items():
            if word == k:
                inquiry_score += v
                inquiry_type = "سؤال_مباشر"
                matched.append(f"❓{k}")
                break
    
    for k, v in inquiry_keywords['أفعال استفسار'].items():
        if k in text_norm:
            inquiry_score += v
            inquiry_type = "طلب_شرح"
            matched.append(f"💡{k}")
            break
    
    for k, v in inquiry_keywords['كلمات إجراء أكاديمي'].items():
        if k in text_norm:
            inquiry_score += v
            inquiry_type = "استفسار_إجرائي"
            matched.append(f"📋{k}")
            break
    
    if inquiry_score > 0:
        has_context = any(ctx in text_norm for ctx in academic_context)
        if has_context:
            score += inquiry_score + 2
            classification = "استفسار_أكاديمي"
        else:
            score += inquiry_score
            classification = "استفسار_عام"
    
    # 🔵 كشف الطلبات المباشرة
    request_found = False
    for word in words_set:
        for level, keywords in request_keywords.items():
            if word in keywords:
                score += keywords[word]
                matched.append(f"🎯{word}+{keywords[word]}")
                request_found = True
                if classification == "غير_مصنف":
                    classification = "طلب_مباشر"
                break
    
    # 🟡 تعزيز السياق الأكاديمي
    if any(ctx in text_norm for ctx in academic_context):
        score += 2
        if not any("[سياق" in m for m in matched):
            matched.append("[سياق+2]")
    
    # 🎯 الجمع بين طلب واستفسار
    if request_found and inquiry_score > 0:
        score += 3
        matched.append("✅ طلب+استفسار")
        classification = "طلب_مؤكّد"
    
    # ⚖️ تعديلات إضافية
    if 15 <= len(text_norm) <= 70:
        score += 1
    if text.endswith('?') or text.endswith('؟'):
        score += 1
    if len(text_norm) < 8:
        score -= 2
    
    return score, classification, matched

# ================== 10. تنسيق رسالة الرصد ==================
def format_message(event, sender, chat, radar_name, score, classification, matched, text):
    username = getattr(sender, 'username', None)
    first_name = getattr(sender, 'first_name', 'مستخدم')
    last_name = getattr(sender, 'last_name', '')
    full_name = f"{first_name} {last_name}".strip() or first_name
    user_id = sender.id
    chat_title = getattr(chat, 'title', 'مجموعة خاصة')
    chat_id = chat.id
    msg_id = event.id
    
    if str(chat_id).startswith('-100'):
        link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{msg_id}"
    else:
        link = f"https://t.me/c/{abs(chat_id)}/{msg_id}"
    
    display_text = text if len(text) <= 150 else text[:150] + "..."
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    msg = (
        f"⚡️ **طلب خدمة طلابية جديد**\n"
        f"🕐 `{timestamp}` | عبر {radar_name}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 **العميل:** {full_name}\n"
        f"🔖 **اليوزر:** @{username or 'بدون'}\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"📍 **المصدر:** {chat_title}\n"
        f"🔗 [الرسالة الأصلية]({link})\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📝 **نص الطلب:**\n_{display_text}_\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 **التحليل:**\n"
        f"• التصنيف: {classification}\n"
        f"• النقاط: {score}\n"
        f"• الكلمات: {', '.join(matched[:5]) if matched else 'لا يوجد'}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👇 **إجراءات سريعة:**"
    )
    
    buttons = []
    if username:
        buttons.append([Button.url("💬 مراسلة الطالب", f"https://t.me/{username}")])
    buttons.append([Button.url("🔗 الانتقال للرسالة", link)])
    
    return msg, buttons

# ================== 11. دالة الرصد الرئيسية (معدلة لاستخدام StringSession) ==================
async def start_monitoring(acc_info):
    # استخدام StringSession بدلاً من اسم الملف
    client = TelegramClient(StringSession(acc_info['session']), acc_info['id'], acc_info['hash'])
    radar_name = acc_info['name']
    
    @client.on(events.NewMessage)
    async def handler(event):
        try:
            if event.is_private:
                return
            
            if is_duplicate(event.chat_id, event.id):
                return
            
            text = event.raw_text.strip()
            if not text:
                return
            
            text_len = len(text)
            if text_len < MIN_MESSAGE_LENGTH or text_len > MAX_MESSAGE_LENGTH:
                logger.debug(f"📏 [{radar_name}] رسالة مستبعدة للطول ({text_len})")
                return
            
            has_link, links = contains_link(text)
            if has_link:
                logger.debug(f"🔗 [{radar_name}] رسالة تحتوي روابط: {links}")
                return
            
            has_phone, phones = contains_phone(text)
            if has_phone:
                logger.debug(f"📱 [{radar_name}] رسالة تحتوي أرقام: {phones}")
                return
            
            score, classification, matched = calculate_score(text)
            is_academic = any(ctx in normalize_arabic(text) for ctx in academic_context)
            
            should_forward = (
                score >= SCORE_THRESHOLD or
                (classification == "استفسار_أكاديمي" and score >= 3) or
                (classification == "طلب_مؤكّد") or
                (classification.startswith("استفسار") and is_academic and score >= 4)
            )
            
            if not should_forward:
                logger.debug(f"❌ [{radar_name}] رسالة مستبعدة للنقاط ({score}): {text[:40]}")
                return
            
            sender = await event.get_sender()
            chat = await event.get_chat()
            
            msg, buttons = format_message(
                event, sender, chat, radar_name,
                score, classification, matched, text
            )
            
            await client.send_message(TARGET_CHANNEL, msg, buttons=buttons, silent=False)
            logger.info(f"✅ [{radar_name}] تم إرسال: {classification} ({score} نقاط)")
            
        except Exception as e:
            logger.error(f"❌ [{radar_name}] خطأ في المعالج: {e}", exc_info=True)
    
    # حلقة الاتصال مع إعادة المحاولة
    retry_count = 0
    max_retries = 10
    
    while True:
        try:
            await client.start()
            logger.info(f"✅ {radar_name} متصل بنجاح!")
            retry_count = 0
            await client.run_until_disconnected()
        except Exception as e:
            retry_count += 1
            wait_time = min(5 * retry_count, 60)
            logger.error(f"⚠️ {radar_name} انقطع: {e}. إعادة المحاولة خلال {wait_time}ث (محاولة {retry_count})")
            if retry_count >= max_retries:
                logger.error(f"❌ {radar_name} تجاوز الحد الأقصى للمحاولات")
                retry_count = 0
            await asyncio.sleep(wait_time)
        finally:
            if client.is_connected():
                await client.disconnect()

# ================== 12. التشغيل الرئيسي ==================
async def main():
    logger.info("🚀 بدء تشغيل رادار الرصد الذكي...")
    logger.info(f"📊 عدد الحسابات: {len(accounts)}")
    logger.info(f"🎯 القناة المستهدفة: {TARGET_CHANNEL}")
    logger.info(f"📏 الطول المقبول: {MIN_MESSAGE_LENGTH}-{MAX_MESSAGE_LENGTH} حرف")
    logger.info(f"🎚️ عتبة النقاط: {SCORE_THRESHOLD}")
    
    tasks = [start_monitoring(acc) for acc in accounts]
    await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 تم إيقاف البوت يدوياً")
    except Exception as e:
        logger.error(f"💥 خطأ فادح: {e}")
        import traceback
        traceback.print_exc()

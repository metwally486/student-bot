#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎓 رادار الرصد الذكي لطلبات الطلاب - النسخة المُحسَّنة
الوظيفة: جلب طلبات الطلاب المباشرة فقط (بدون استفسارات أو إعلانات)
المطور: مساعد الذكاء الاصطناعي
التاريخ: 2026
"""

# ================== 1. استيراد المكتبات ==================
import os
import sys
import re
import asyncio
import threading
import logging
from datetime import datetime
from collections import deque

from flask import Flask, jsonify
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

# ================== 2. إعداد التسجيل (Logging) ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ================== 3. سيرفر الويب (Flask) للبقاء متصلًا على Render ==================
app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    <h1>🎓 رادار الرصد الذكي لطلبات الطلاب</h1>
    <p>✅ النظام يعمل بنجاح!</p>
    <p>🕐 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>📊 الحالة: متصل ويعمل</p>
    """

@app.route('/health')
def health():
    return jsonify(status="healthy", timestamp=datetime.now().isoformat())

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# تشغيل السيرفر في خلفية منفصلة
threading.Thread(target=run_flask, daemon=True).start()
logger.info(f"✅ سيرفر الويب يعمل على المنفذ {os.environ.get('PORT', 10000)}")

# ================== 4. تحميل متغيرات البيئة ==================
logger.info("📋 جاري تحميل متغيرات البيئة...")

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL")

# التحقق من المتغيرات الأساسية
if not all([API_ID, API_HASH, TARGET_CHANNEL]):
    logger.error("❌ خطأ: أحد المتغيرات الأساسية مفقود!")
    logger.error(f"   API_ID: {'✅' if API_ID else '❌ مفقود'}")
    logger.error(f"   API_HASH: {'✅' if API_HASH else '❌ مفقود'}")
    logger.error(f"   TARGET_CHANNEL: {'✅' if TARGET_CHANNEL else '❌ مفقود'}")
    sys.exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    logger.error(f"❌ خطأ: API_ID يجب أن يكون رقماً صحيحاً، القيمة الحالية: {API_ID}")
    sys.exit(1)

logger.info("✅ تم تحميل المتغيرات الأساسية بنجاح")

# جلسات الحسابات
SESSION_1 = os.environ.get("SESSION_1", "").strip()
SESSION_2 = os.environ.get("SESSION_2", "").strip()

# ================== 5. إعدادات التصفية (يمكن تعديلها حسب الحاجة) ==================
SCORE_THRESHOLD = int(os.environ.get("SCORE_THRESHOLD", "8"))  # الحد الأدنى للنقاط لقبول الطلب
MIN_MSG_LENGTH = int(os.environ.get("MIN_MSG_LENGTH", "10"))   # أقل عدد أحرف للرسالة
MAX_MSG_LENGTH = int(os.environ.get("MAX_MSG_LENGTH", "200"))  # أكبر عدد أحرف للرسالة

# ================== 6. إعداد حسابات التليجرام ==================
accounts = []

if SESSION_1:
    accounts.append({
        'name': 'رادار-1',
        'api_id': API_ID,
        'api_hash': API_HASH,
        'session': SESSION_1
    })
    logger.info("✅ الحساب الأول [رادار-1] تم تحميله")

if SESSION_2:
    accounts.append({
        'name': 'رادار-2',
        'api_id': API_ID,
        'api_hash': API_HASH,
        'session': SESSION_2
    })
    logger.info("✅ الحساب الثاني [رادار-2] تم تحميله")

if not accounts:
    logger.error("❌ خطأ: لم يتم توفير أي جلسة! أضف SESSION_1 في متغيرات البيئة")
    sys.exit(1)

logger.info(f"📊 إجمالي الحسابات النشطة: {len(accounts)}")

# ================== 7. إعدادات خاصة (اختياري) ==================
# قناة خاصة للتحويل الفوري (بدون فلاتر) - اتركها -1 إذا لم تستخدمها
SPECIAL_CHANNEL_ID = int(os.environ.get("SPECIAL_CHANNEL_ID", "-1"))

# روابط دعوة المجموعات (للمجموعات الخاصة)
INVITE_LINKS = {
    # مثال: -1001234567890: "https://t.me/+AbCdEfGhIjK12345",
}
DEFAULT_INVITE_LINK = os.environ.get("DEFAULT_INVITE_LINK", "")

# ================== 8. ⭐ كلمات الطلبات المباشرة (المقبولة فقط) ⭐ ==================
# هذه الكلمات تضمن أن الرسالة "طلب" وليس "استفسار" أو "إعلان"
DIRECT_REQUEST_KEYWORDS = {
    'طلب_عاجل': [
        'احتاج', 'أحتاج', 'ابغى', 'ابي', 'مطلوب', 'مطلوبة', 
        'عندي واجب', 'عندي تكليف', 'عندي مشروع'
    ],
    'طلب_مساعدة': [
        'حد يسوي', 'مين يسوي', 'حد يكمل', 'مين يكمل', 'حد يساعد', 
        'أبحث عن', 'ابحث عن', 'دور لي', 'محتاج واحد'
    ],
    'طلب_خدمة': [
        'حل واجب', 'حل تكليف', 'سكليف', 'تجسير', 'عرض بوربوينت', 
        'عرض تقديمي', 'ترجمة نص', 'خصوصي احصاء', 'خصوصي مادة',
        'عذر طبي', 'تأجيل اختبار', 'انسحاب مادة'
    ]
}

# ================== 9. ⭐ كلمات الاستبعاد (المرشحات السلبية) ⭐ ==================
# أي رسالة تحتوي على هذه الكلمات سيتم تجاهلها فوراً

# 9.1 كلمات الإعلانات والخدمات التجارية
AD_KILLERS = {
    'للتواصل', 'للتسجيل', 'واتساب', 'واتس', 'تواصل', 'راسلني', 'لبيع', 
    'سعر', 'ريال', 'دولار', 'عرض', 'خصم', 'ضمان', 'استثمار', 'ربح', 
    'تسويق', 'اعلان', 'معلن', 'احجز', 'مقعد', 'سارع', 'محدود', 'يوجد حل', 'متوفر حل', 'نحل', 'نحل الواجب', 'نحل التكليف',
    'نضمن', 'درجة كاملة', 'نجاح مضمون', 'توظيف', 'مطلوب معلمين', 
    'مطلوب مدرسين', 'وظيفة', 'مكتب', 'مجموعة', 'قناة', 'لدينا', 'عندنا',
    'نقدم', 'خدماتنا', 'لشراء', 'للبيع', 'جنيه', 'دفع', 'دفعات',
    'حل جميع المواد', 'حلول جاهزة', 'مكتب خدمات', 'ضمان النجاح', 
    'توثيق رسائل', 'تحضير عروض', 'تصميم بوربوينت', 'خدمة مدفوعة',
    'للاشتراك', 'اشترك', 'انشر', 'نشر', 'ترويج', 'إشهار'
}

# 9.2 أدوات الاستفهام (للاستفسارات العامة التي نريد استبعادها)
INQUIRY_WORDS = {
    'كيف', 'متى', 'كم', 'أين', 'من', 'هل', 'وش', 'ايش', 'شنو', 
    'ليه', 'لماذا', 'مين', 'وشلون', 'ايش رأيكم', 'شو رأيكم'
}

# 9.3 كلمات البداية التي تشير لرسائل غير طلبات
IGNORE_STARTS = [
    '[إعلان]', '🔴 هام', '📢 يعلن', 'فرصة', 'مطلوب للعمل', 
    'مطلوب للتدريس', 'سلام عليكم', 'مساء الخير', 'صباح النور',
    'السلام عليكم', 'هاي', 'هلا', 'مرحبا', 'أهلاً'
]

# ================== 10. السياق الأكاديمي (لتعزيز الطلبات الشرعية) ==================
ACADEMIC_CONTEXT = [
    'فيزياء', 'كيمياء', 'رياضيات', 'أحياء', 'عربي', 'انجليزي', 'لغة',
    'تاريخ', 'جغرافيا', 'فلسفة', 'منطق', 'إحصاء', 'محاسبة', 'اقتصاد',
    'قانون', 'طب', 'هندسة', 'تقنية', 'برمجة', 'كمبيوتر', 'حاسب',
    'مادة', 'مقرر', 'كتاب', 'مرجع', 'دروس', 'محاضرة', 'محاضرات',
    'واجب', 'تكليف', 'سكليف', 'تجسير', 'دوام', 'تسجيل', 'شعبة', 'جدول',
    'اختبار', 'امتحان', 'نتيجة', 'رصد', 'درجة', 'علامة', 'نسبة', 'معدل',
    'تراكمي', 'فصل', 'ترم', 'سنة', 'جامعة', 'كلية', 'معهد', 'طالب', 'طالبة'
]

# ================== 11. أنماط الروابط وأرقام الهواتف (للاستبعاد) ==================
LINK_PATTERNS = [
    r'https?://\S+', r'www\.\S+', r't\.me/\S+', r'telegram\.me/\S+',
    r'wa\.me/\S+', r'whatsapp\.com/\S+', r'bit\.ly/\S+', r'goo\.gl/\S+',
    r'[a-zA-Z0-9.-]+\.(com|net|org|info|biz|me|io|co|sa|ae|eg)\S*',
    r'\.[a-zA-Z]{2,}(/\S*)?', r'\S+@\S+\.\S+',
]

PHONE_PATTERNS = [
    r'\+?\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}',
    r'05\d{8}', r'00966\d{9}', r'\+966\d{9}', r'01\d{8}',
    r'0020\d{9}', r'\+20\d{9}', r'07\d{8}', r'00964\d{9}',
    r'\+964\d{9}', r'\d{10,15}',
]

CONTACT_WORDS = [
    'تواصل', 'للتواصل', 'راسلني', 'واتساب', 'واتس', 'wb', 'سناب', 'انستقرام', 'انستا', 'تويتر', 'فيسبوك',
    'ايميل', 'بريد', 'email', 'call', 'رقم', 'جوال', 'موبايل',
    'للتحميل', 'للتسجيل', 'اضغط هنا', 'link', 'رابط'
]

# ================== 12. منع تكرار إرسال نفس الرسالة ==================
MAX_SENT_IDS = 10000
sent_messages = deque(maxlen=MAX_SENT_IDS)

def is_duplicate(chat_id: int, message_id: int) -> bool:
    """التحقق مما إذا كانت الرسالة قد أُرسلت مسبقاً"""
    key = f"{chat_id}:{message_id}"
    if key in sent_messages:
        return True
    sent_messages.append(key)
    return False

# ================== 13. دوال معالجة النصوص ==================
def normalize_arabic(text: str) -> str:
    """توحيد شكل النص العربي لتسهيل المطابقة"""
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ةه]', 'ه', text)
    text = re.sub(r'[ىي]', 'ي', text)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)  # إزالة التشكيل
    return text.strip().lower()

def contains_link(text: str) -> bool:
    """التحقق من وجود روابط في النص"""
    text_lower = text.lower()
    for pattern in LINK_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    for word in CONTACT_WORDS:
        if word in text_lower:
            return True
    return False

def contains_phone(text: str) -> bool:
    """التحقق من وجود أرقام هواتف في النص"""
    cleaned = re.sub(r'[^\d]', '', text)
    return len(cleaned) >= 10

# ================== 14. ⭐ نظام التحليل والفرز الذكي ⭐ ==================
def analyze_message(text: str) -> tuple[int, str, list[str]]:
    """
    تحليل نص الرسالة وتحديد ما إذا كان طلباً شرعياً أم لا
    
    العودة: (النقاط النهائية, التصنيف, قائمة الكلمات المطابقة)
    """
    text_norm = normalize_arabic(text)
    words = text_norm.split()
    words_set = set(words)
    
    matched_keywords = []
    
    # ─────────────────────────────────────────────────────
    # ❌ الفلتر الأول: الاستبعاد الفوري للإعلانات
    # ─────────────────────────────────────────────────────
    for ad_word in AD_KILLERS:
        if ad_word in text_norm:
            return -100, "إعلان_مستبعد", [f"🚫{ad_word}"]
    
    # ─────────────────────────────────────────────────────
    # ❌ الفلتر الثاني: الاستبعاد الفوري للروابط وأرقام الهاتف
    # ─────────────────────────────────────────────────────
    if contains_link(text) or contains_phone(text):
        return -100, "يحتوي_على_رابط_أو_هاتف", ["🔗رابط/هاتف"]
    
    # ─────────────────────────────────────────────────────
    # ❌ الفلتر الثالث: رسائل البداية العامة (تحية فقط)
    # ─────────────────────────────────────────────────────
    first_few_words = ' '.join(words[:3])
    for ignore in IGNORE_STARTS:
        if ignore in text_norm or first_few_words.startswith(ignore):
            # استثناء: إذا كانت الرسالة تحتوي على طلب قوي رغم البداية
            has_strong_request = any(
                req in text_norm 
                for category in DIRECT_REQUEST_KEYWORDS.values() 
                for req in category
            )
            if not has_strong_request:
                return -50, "تحية_فقط", ["👋بداية عامة"]
    
    # ─────────────────────────────────────────────────────
    # ✅ الفلتر الرابع: البحث عن كلمات الطلب المباشرة
    # ─────────────────────────────────────────────────────
    request_score = 0
    has_direct_request = False
    
    for category, keywords in DIRECT_REQUEST_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_norm:
                request_score += 15  # نقاط عالية جداً لكلمات الطلب المباشرة
                has_direct_request = True
                matched_keywords.append(f"✅{keyword}")
                break  # نكتفي بأول مطابقة في كل فئة
    
    # ─────────────────────────────────────────────────────
    # ⚠️ الفلتر الخامس: خصم نقاط لأسئلة الاستفسار العامة
    # ─────────────────────────────────────────────────────
    inquiry_count = sum(1 for word in words_set if word in INQUIRY_WORDS)
    
    # إذا كانت الرسالة تبدأ بأداة استفهام وليس فيها طلب مباشر = استبعاد
    if words and words[0] in INQUIRY_WORDS and not has_direct_request:
        return -30, "استفسار_عام", [f"❓{words[0]}"]
    
    # خصم نقاط بسيطة إذا كانت الرسالة تحتوي على الكثير من أدوات الاستفهام
    if inquiry_count >= 2 and not has_direct_request:
        request_score -= 10
        matched_keywords.append("❓استفسار")
    
    # ─────────────────────────────────────────────────────
    # 🎓 الفلتر السادس: تعزيز السياق الأكاديمي
    # ─────────────────────────────────────────────────────
    academic_bonus = 0
    for context_word in ACADEMIC_CONTEXT:
        if context_word in text_norm:
            academic_bonus += 2
            if "[أكاديمي]" not in matched_keywords:
                matched_keywords.append("[أكاديمي]")
            break  # نكتفي بكلمة سياق واحدة
    
    # ─────────────────────────────────────────────────────
    # 📏 الفلتر السابع: فحص طول الرسالة (منطقي للطلبات)
    # ─────────────────────────────────────────────────────
    text_len = len(text_norm)
    if text_len < MIN_MSG_LENGTH or text_len > MAX_MSG_LENGTH:
        return -20, "طول_غير_مناسب", [f"📏{text_len} حرف"]
    
    # ─────────────────────────────────────────────────────
    # 🧮 حساب النقاط النهائية واتخاذ القرار
    # ─────────────────────────────────────────────────────
    final_score = request_score + academic_bonus
    
    # تحديد التصنيف
    if has_direct_request and final_score >= 10:
        classification = "طلب_مباشر_مؤكد"
    elif has_direct_request:
        classification = "طلب_مباشر"
    elif final_score >= SCORE_THRESHOLD and academic_bonus > 0:
        classification = "طلب_محتمل"
    else:
        classification = "غير_مؤهل"
    
    # ✅ شرط القبول النهائي: يجب أن يكون هناك طلب مباشر أو نقاط عالية جداً
    if not has_direct_request and final_score < SCORE_THRESHOLD:
        return -10, classification, matched_keywords
    
    return final_score, classification, matched_keywords

# ================== 15. ⭐ دالة إنشاء الروابط الذكية للمجموعات ⭐ ==================
def get_smart_links(chat, event_id: int) -> tuple[str, str]:
    """
    إنشاء روابط ذكية للمجموعات:
    - المجموعات العامة: t.me/username/message_id
    - المجموعات الخاصة: رابط الدعوة أو رابط داخلي
    
    العودة: (رابط المجموعة, رابط الرسالة)
    """
    chat_id = chat.id
    chat_username = getattr(chat, 'username', None)
    
    group_link = "#"
    msg_link = "#"
    
    # 🔗 رابط المجموعة (للانضمام)
    if chat_id in INVITE_LINKS:
        group_link = INVITE_LINKS[chat_id]
    elif chat_username:
        group_link = f"https://t.me/{chat_username}"
    elif DEFAULT_INVITE_LINK:
        group_link = DEFAULT_INVITE_LINK
    
    # 🔗 رابط الرسالة الأصلية
    if chat_username:
        msg_link = f"https://t.me/{chat_username}/{event_id}"
    else:
        try:
            cid = str(chat_id)
            if cid.startswith('-100'):
                msg_link = f"https://t.me/c/{cid[4:]}/{event_id}"
            else:
                msg_link = f"https://t.me/c/{abs(chat_id)}/{event_id}"
        except Exception:
            pass
    
    return group_link, msg_link

# ================== 16. تنسيق رسالة الإرسال للقناة ==================
def format_forward_message(
    event, sender, chat, radar_name: str, 
    score: int, classification: str, matched: list[str], 
    text: str, is_special: bool = False
) -> tuple[str, list]:
    """تنسيق الرسالة قبل إرسالها للقناة المستهدفة"""
    
    # معلومات المرسل
    username = getattr(sender, 'username', None)
    first_name = getattr(sender, 'first_name', 'مستخدم')
    last_name = getattr(sender, 'last_name', '')
    full_name = f"{first_name} {last_name}".strip() or first_name
    user_id = sender.id
    
    # معلومات المجموعة
    chat_title = getattr(chat, 'title', 'مجموعة')
    
    # الروابط الذكية
    group_link, msg_link = get_smart_links(chat, event.id)
    
    # اقتطاع النص الطويل
    display_text = text[:150] + "..." if len(text) > 150 else text
    
    # ─────────────────────────────────────────────────────
    # 📝 بناء نص الرسالة
    # ─────────────────────────────────────────────────────
    if is_special:
        # رسالة القناة الخاصة (تحويل فوري)
        msg = (
            f"🔴 **تحويل فوري | قناة خاصة**\n"
            f"🕐 `{datetime.now().strftime('%H:%M:%S')}` | عبر {radar_name}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **المرسل:** {full_name}\n"
            f"🔖 **اليوزر:** @{username or 'بدون'}\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"📍 **المصدر:** {chat_title} ⭐\n"
            f"🔗 [الرسالة الأصلية]({msg_link})\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 **النص:**\n_{display_text}_\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👇 **إجراءات سريعة:**"
        )
    else:
        # رسالة الطلب العادي
        keywords_str = " | ".join(matched[:5]) if matched else "بدون كلمات مفتاحية"
        msg = (
            f"⚡️ **طلب خدمة طلابية جديد**\n"
            f"🕐 `{datetime.now().strftime('%H:%M:%S')}` | عبر {radar_name}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **العميل:** {full_name}\n"
            f"🔖 **اليوزر:** @{username or 'بدون'}\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"📍 **المصدر:** {chat_title}\n"
            f"🔗 [الرسالة الأصلية]({msg_link})\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 **نص الطلب:**\n_{display_text}_\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 **التصنيف:** {classification}\n"
            f"🎯 **الكلمات:** {keywords_str}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👇 **إجراءات سريعة:**"
        )
    
    # ─────────────────────────────────────────────────────
    # 🔘 بناء الأزرار
    # ─────────────────────────────────────────────────────
    buttons = []
    
    # زر المراسلة الخاصة للطالب
    if username:
        buttons.append([Button.url("💬 مراسلة الطالب", f"https://t.me/{username}")])
    
    # زر الانضمام للمجموعة
    if group_link and group_link != "#":
        buttons.append([Button.url("👥 الانضمام للمجموعة", group_link)])
    
    # زر رؤية الرسالة الأصلية
    if msg_link and msg_link != "#":
        btn_text = "🔗 رؤية الرسالة" if chat.username else "🔗 الرسالة (للأعضاء فقط)"
        buttons.append([Button.url(btn_text, msg_link)])
    
    return msg, buttons

# ================== 17. ⭐ دالة الرصد الرئيسية لكل حساب ⭐ ==================
async def start_monitoring(acc_info: dict):
    """بدء مراقبة الرسائل لحساب تليجرام معين"""
    
    client = TelegramClient(
        StringSession(acc_info['session']),
        acc_info['api_id'],
        acc_info['api_hash'],
        auto_reconnect=True,
        connection_retries=5,
        retry_delay=3
    )
    
    radar_name = acc_info['name']
    
    @client.on(events.NewMessage)
    async def message_handler(event):
        try:
            # ❌ تجاهل الرسائل الخاصة (البوت لا يراقب الدردشات الخاصة)
            if event.is_private:
                return
            
            # ❌ منع تكرار معالجة نفس الرسالة
            if is_duplicate(event.chat_id, event.id):
                return
            
            # استخراج النص
            text = event.raw_text.strip()
            if not text:
                return
            
            # الحصول على معلومات المرسل والمجموعة
            sender = await event.get_sender()
            chat = await event.get_chat()
            chat_id = chat.id
            
            # ─────────────────────────────────────────────────────
            # ⭐ الاستثناء: القناة الخاصة (تحويل فوري بدون فلاتر)
            # ─────────────────────────────────────────────────────
            if SPECIAL_CHANNEL_ID > 0 and chat_id == SPECIAL_CHANNEL_ID:
                logger.info(f"⭐ [{radar_name}] تحويل فوري من القناة الخاصة")
                
                msg, buttons = format_forward_message(
                    event, sender, chat, radar_name,
                    score=0, classification="تحويل_فوري", matched=[],
                    text=text, is_special=True
                )
                
                await client.send_message(TARGET_CHANNEL, msg, buttons=buttons, silent=False)
                return  # ✅ خروج فوري - لا تطبق الفلاتر
            
            # ─────────────────────────────────────────────────────
            # ✅ تطبيق نظام الفلترة الذكي على جميع القنوات الأخرى
            # ─────────────────────────────────────────────────────
            
            # تحليل الرسالة
            score, classification, matched = analyze_message(text)
            
            # ❌ رفض الرسالة إذا كانت النقاط سالبة أو التصنيف غير مؤهل
            if score < 0 or classification in ["إعلان_مستبعد", "غير_مؤهل", "استفسار_عام", "تحية_فقط"]:
                return
            
            # ✅ قبول الرسالة وإرسالها للقناة المستهدفة
            msg, buttons = format_forward_message(
                event, sender, chat, radar_name,
                score, classification, matched, text, is_special=False
            )
            
            await client.send_message(TARGET_CHANNEL, msg, buttons=buttons, silent=False)
            logger.info(f"✅ [{radar_name}] {classification} | نقاط: {score} | كلمات: {matched[:3]}")
            
        except Exception as e:
            logger.error(f"❌ [{radar_name}] خطأ في المعالجة: {e}", exc_info=True)
    
    # ─────────────────────────────────────────────────────
    # 🔁 حلقة الاتصال المستمرة
    # ─────────────────────────────────────────────────────
    while True:
        try:
            await client.start()
            logger.info(f"✅ {radar_name} متصل بنجاح وبدأ الرصد!")
            await client.run_until_disconnected()
        except Exception as e:
            logger.error(f"⚠️ {radar_name} انقطع الاتصال: {e}")
            await asyncio.sleep(5)
        finally:
            if client.is_connected():
                await client.disconnect()

# ================== 18. التشغيل الرئيسي للبوت ==================
async def main():
    """الدالة الرئيسية لبدء تشغيل جميع الحسابات"""
    logger.info("🚀 بدء تشغيل رادار الرصد الذكي لطلبات الطلاب...")
    logger.info(f"📊 الحسابات النشطة: {len(accounts)}")
    logger.info(f"🎯 القناة المستهدفة: {TARGET_CHANNEL}")
    if SPECIAL_CHANNEL_ID > 0:
        logger.info(f"⭐ القناة الخاصة للتحويل الفوري: {SPECIAL_CHANNEL_ID}")
    
    # إنشاء مهام المراقبة لكل حساب
    tasks = [start_monitoring(acc) for acc in accounts]
    
    # تشغيل جميع المهام بشكل متوازي
    await asyncio.gather(*tasks, return_exceptions=True)

# ================== 19. نقطة الدخول للتطبيق ==================
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 تم إيقاف البوت يدوياً")
    except Exception as e:
        logger.error(f"💥 خطأ فادح في التشغيل: {e}", exc_info=True)
        import traceback
        traceback.print_exc()

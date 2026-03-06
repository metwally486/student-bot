import os
import asyncio
import threading
import google.generativeai as genai
from flask import Flask
from telethon import TelegramClient, events, Button

# ================== 1. إعدادات Gemini والبيئة ==================
# سحب المفتاح الجديد الذي وضعته في Render
GEMINI_KEY = os.environ.get("GEMINI_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

# ================== 2. قوائم الكلمات (تحديث لمنع الإعلانات) ==================
ALL_KEYWORDS = [
    'حد', 'مين', 'كيف', 'متى', 'سؤال', 'استفسار', 'احتاج', 'ممكن', 'أبغى', 'تكفون', 
    'ساعدوني', 'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 'شرح', 'ملخص', 
    'برمجة', 'تصميم', 'كود', 'إحصاء', 'سلايدات', 'هومورك'
]

# إضافة كلمات المعلنين الذين ظهروا في صورك
FORBIDDEN_WORDS = [
    'تواصل', 'واتساب', 'ارباح', 'استثمار', 'ضمان', 'فحص دوري', 'تأشيرات',
    'تخفيضات', 'خصم', 'يووجد لدينا', 'لدينا الآن', 'معانا', 'بأسعار'
]

# ================== 3. الإعدادات الأساسية ==================
API_ID = 2040 
API_HASH = "b18441a1ff607e10a989891a5462e627"
TARGET_CHANNEL = "student1_admin"

app = Flask(__name__)
@app.route('/')
def home(): return "Gemini-Radar is Online"

# ================== 4. التحليل الذكي (إصلاح الـ Loop ورفض الإعلانات) ==================
async def analyze_message(text):
    if not (5 <= len(text) <= 180): return False
    text_lower = text.lower()
    
    # فلترة أولية بالكلمات الممنوعة لمنع أصحاب الإعلانات
    if any(bad in text_lower for bad in FORBIDDEN_WORDS): return False
    
    # التحقق من وجود كلمات مفتاحية
    if not any(word in text_lower for word in ALL_KEYWORDS): return False

    # تفعيل عقل Gemini (باستخدام توجيه صارم)
    if ai_model:
        try:
            # استخدام to_thread يحل مشكلة RuntimeError التي ظهرت في سجلاتك
            prompt = (
                f"حلل النص التالي: '{text}'\n"
                "هل هذا 'طالب' يطلب مساعدة (أجب YES)؟ "
                "أم هو 'معلن/مكتب' يعرض خدماته بخصومات (أجب NO)؟"
            )
            response = await asyncio.to_thread(ai_model.generate_content, prompt)
            return "yes" in response.text.lower()
        except:
            # إذا تعطل المفتاح، نعتمد على الفلترة اليدوية أعلاه
            return True 
    return True

# ================== 5. نظام التشغيل المستقر ==================
async def start_radar(acc):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(acc['session'], API_ID, API_HASH, loop=loop)
    
    @client.on(events.NewMessage)
    async def handler(event):
        if event.is_private or not event.raw_text: return
        
        # استدعاء التحليل المطور
        if await analyze_message(event.raw_text):
            sender = await event.get_sender()
            username = getattr(sender, 'username', None)
            user_id = getattr(sender, 'id', 'غير معروف')
            
            buttons = [[Button.url("💬 مراسلة الطالب (خاص)", f"https://t.me/{username}")]] if username else []
            
            clean_msg = (
                f"💗 خدمات طلابيه\n⚡️ طلب جديد مفحوص بذكاء Gemini\n━━━━━━━━━━━━━━━━━━\n"
                f"👤 العميل: @{username if username else 'بدون_يوزر'}\n🆔 ID: `{user_id}`\n"
                f"📍 المصدر: {getattr(event.chat, 'title', 'مجموعة')}\n"
                f"━━━━━━━━━━━━━━━━━━\n📝 نص الطلب:\n{event.raw_text}\n━━━━━━━━━━━━━━━━━━"
            )
            try:
                await client.send_message(TARGET_CHANNEL, clean_msg, buttons=buttons, link_preview=False)
                await asyncio.sleep(6) 
            except: pass

    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    # تشغيل Flask على بورد 10000 كما هو موضح في سجلاتك
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    
    accounts = [{'session': 'session_1'}, {'session': 'session_2'}]
    for acc in accounts:
        # تشغيل كل حساب في Thread مستقل تماماً لضمان استقرار Gemini
        threading.Thread(target=lambda a=acc: asyncio.run(start_radar(a)), daemon=True).start()
    
    while True:
        import time
        time.sleep(10)

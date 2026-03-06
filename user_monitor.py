import os, asyncio, threading
import google.generativeai as genai
from flask import Flask
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession # ضروري جداً لتجنب طلب الهاتف

# ================== 1. إعدادات البيئة (Render) ==================
GEMINI_KEY = os.environ.get("GEMINI_KEY")
SESSION_1 = os.environ.get("SESSION_1") # النص المستخرج من Termux

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

# ================== 2. القائمة الموسعة (دراسة + تقنية) ==================
ALL_KEYWORDS = [
    'حد', 'مين', 'كيف', 'متى', 'سؤال', 'استفسار', 'احتاج', 'ممكن', 'أبغى', 'ساعدوني', 
    'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 'شرح', 'ملخص', 
    'برمجة', 'تصميم', 'كود', 'سي شارب', 'C#', 'SQL', 'داتابيز', 'شبكات', 
    'باكيت تريسر', 'Packet Tracer', 'سلايدات', 'هومورك', 'تاسك'
]

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
def home(): return "Advanced Radar is Live"

# ================== 4. التحليل الذكي ==================
async def analyze_message(text):
    if not (5 <= len(text) <= 200): return False
    text_lower = text.lower()
    
    if any(bad in text_lower for bad in FORBIDDEN_WORDS): return False
    if not any(word in text_lower for word in ALL_KEYWORDS): return False

    if ai_model:
        try:
            prompt = (
                f"حلل النص: '{text}'\n"
                "هل هذا طالب يطلب مساعدة (أجب YES)؟ "
                "أم هو معلن يعرض خدماته (أجب NO)؟"
            )
            # استخدام to_thread يمنع الـ RuntimeError في Render
            response = await asyncio.to_thread(ai_model.generate_content, prompt)
            return "yes" in response.text.lower()
        except:
            return True 
    return True

# ================== 5. تشغيل الرادار بنظام StringSession ==================
async def start_radar(session_string):
    if not session_string: return
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # هنا الفرق الجوهري الذي يمنع طلب رقم الهاتف
    client = TelegramClient(StringSession(session_string), API_ID, API_HASH, loop=loop)
    
    @client.on(events.NewMessage)
    async def handler(event):
        if event.is_private or not event.raw_text: return
        if await analyze_message(event.raw_text):
            sender = await event.get_sender()
            username = getattr(sender, 'username', None)
            
            buttons = [[Button.url("💬 مراسلة الطالب (خاص)", f"https://t.me/{username}")]] if username else []
            clean_msg = (
                f"💗 خدمات طلابيه\n⚡️ طلب جديد مفحوص بذكاء Gemini\n━━━━━━━━━━━━━━━━━━\n"
                f"📝 النص: {event.raw_text}\n━━━━━━━━━━━━━━━━━━"
            )
            try:
                await client.send_message(TARGET_CHANNEL, clean_msg, buttons=buttons, link_preview=False)
                await asyncio.sleep(5) 
            except: pass

    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    
    # تشغيل الجلسة التي وضعتها في Render
    if SESSION_1:
        threading.Thread(target=lambda: asyncio.run(start_radar(SESSION_1)), daemon=True).start()
    
    while True:
        import time
        time.sleep(10)


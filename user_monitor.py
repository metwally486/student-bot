import os
import re
import asyncio
import threading
from datetime import datetime
from flask import Flask
from telethon import TelegramClient, events, Button

# --- 1. سيرفر الويب لإبقاء البوت حياً ---
app = Flask(__name__)
@app.route('/')
def home(): return "البوت يعمل بأعلى كفاءة!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# --- 2. إعدادات الحساب ---
api_id = 2040
api_hash = 'b18441a1ff607e10a989891a5462e627'
session_name = 'session_name' 

client = TelegramClient(session_name, api_id, api_hash)

# --- 3. الكلمات المفتاحية والفلاتر ---
keywords = [
    'حد', 'مين', 'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 'تلخيص', 
    'عذر', 'اعذار', 'إجازة مرضية', 'تقرير طبي', 'سكليف', 'غياب',
    'تصميم', 'برمجة', 'كود', 'إحصاء', 'احصاء', 'رياضيات', 'فيزياء', 'ترجمة'
]
forbidden = ['استثمار', 'ارباح', 'دخل', 'ضمان', 'سعر خاص']

# --- 4. معالج الرسائل بتنسيق احترافي ---
@client.on(events.NewMessage)
async def handler(event):
    try:
        if event.is_private: return 
        
        text = event.raw_text.strip()
        length = len(text)
        
        # استثناء الروابط التسويقية الصريحة
        if any(x in text for x in ['http', 'wa.me', 't.me/+', 'snapchat.com']): return

        if any(word in text.lower() for word in keywords):
            if 5 <= length <= 130:
                if not any(bad in text for bad in forbidden):
                    
                    # جلب بيانات المرسل والمجموعة
                    sender = await event.get_sender()
                    sender_name = f"@{sender.username}" if getattr(sender, 'username', None) else "لا يوجد يوزر"
                    name_display = getattr(sender, 'first_name', 'مستخدم')
                    
                    chat = await event.get_chat()
                    chat_title = chat.title if hasattr(chat, 'title') else "مجموعة غير معروفة"
                    time_now = datetime.now().strftime("%I:%M %p")
                    
                    # تصميم الواجهة المرتبة
                    display_message = (
                        f"**✨ رصد طلب جديد**\n"
                        f"‏━━━━━━━━━━━━━━━━━━\n"
                        f"**👤 المرسل:** {name_display} ( {sender_name} )\n"
                        f"**📍 المصدر:** `{chat_title}`\n"
                        f"**⏰ الوقت:** `{time_now}`\n"
                        f"‏━━━━━━━━━━━━━━━━━━\n"
                        f"**📝 نص الطلب:**\n"
                        f"« _ {text} _ »\n"
                        f"‏━━━━━━━━━━━━━━━━━━"
                    )
                    
                    # إرسال الرسالة مع زر الانتقال المباشر
                    await client.send_message(
                        'student1_admin', 
                        display_message, 
                        buttons=[[Button.url("💬 تواصل مع الطالب / رد الآن", f"https://t.me/c/{chat.id}/{event.id}")]]
                    )
    except Exception as e:
        print(f"⚠️ خطأ: {e}")

# --- 5. التشغيل الآمن ---
async def main():
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())

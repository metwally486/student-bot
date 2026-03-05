import os
import re
import asyncio
import threading
from datetime import datetime
from flask import Flask
from telethon import TelegramClient, events, Button

# --- 1. سيرفر الويب لإبقاء البوت حياً على Render ---
app = Flask(__name__)
@app.route('/')
def home(): return "رادار الاستفسارات الطلابية يعمل بنجاح!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# --- 2. إعدادات الحساب ---
api_id = 2040
api_hash = 'b18441a1ff607e10a989891a5462e627'
session_name = 'session_name' 

client = TelegramClient(session_name, api_id, api_hash)

# --- 3. الكلمات المفتاحية (رصد شامل لكل الاستفسارات) ---
keywords = [
    # كلمات السؤال والاستفسار
    'حد', 'مين', 'كيف', 'متى', 'سؤال', 'استفسار', 'يعرف', 'يفيدني', 'احتاج', 'ممكن', 
    'وش', 'شنو', 'ايش', 'تكفون', 'ساعدوني', 'بالله', 'لو سمحتو', 'يا شباب', 'يا بنات',
    # تخصصات وخدمات
    'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 'مهندس', 'تصميم', 'برمجة', 
    'كود', 'إحصاء', 'رياضيات', 'فيزياء', 'كيمياء', 'ترجمة', 'محاسبة', 'اقتصاد',
    # أمور أكاديمية
    'عذر', 'غياب', 'سكليف', 'مرضية', 'تجسير', 'دوام', 'تدريب', 'صيفي', 'مادة', 'دكتور', 
    'استاذ', 'تحضير', 'حرمان', 'درجات', 'معدل', 'جامعة', 'كلية'
]

# --- 4. كلمات المنع (فلتر الإعلانات والتواصل الخارجي)
forbidden = [
    'تواصل', 'واتساب', 'واتس', 'للتواصل', 'رقم', 'ارباح', 'دخل', 'استثمار', 
    'ضمان', 'سعر', 'رخيص', 'خصم', 'عروض',  'دقة', 'انجاز', 'متوفر'
]

# --- 5. معالج الرسائل الذكي ---
@client.on(events.NewMessage)
async def handler(event):
    try:
        if event.is_private: return 
        
        text = event.raw_text.strip()
        length = len(text)
        
        # أ. استبعاد الروابط فوراً
        if any(x in text for x in ['http', 'wa.me', 't.me/+', 'snapchat.com']): return
        
        # ب. استبعاد الرسائل التي تحتوي على كلمات "تواصل" أو إعلانات
        if any(bad in text for bad in forbidden): return

        # ج. رصد الكلمات المفتاحية
        if any(word in text.lower() for word in keywords):
            # نطاق طول يسمح بالاستفسارات الحقيقية ويستبعد النصوص الطويلة جداً
            if 2 <= length <= 150:
                
                sender = await event.get_sender()
                sender_id = sender.id
                username = f"@{sender.username}" if getattr(sender, 'username', None) else "بدون يوزر"
                name_display = getattr(sender, 'first_name', 'مستخدم')
                
                chat = await event.get_chat()
                chat_title = chat.title if hasattr(chat, 'title') else "مجموعة غير معروفة"
                
                # تصميم الواجهة الاحترافي
                display_message = (
                    f"✨ **رصد استفسار / طلب جديد**\n"
                    f"‏━━━━━━━━━━━━━━━━━━\n"
                    f"👤 **المرسل:** {name_display} ( {username} )\n"
                    f"🆔 **ID:** `{sender_id}`\n"
                    f"📍 **المصدر:** `{chat_title}`\n"
                    f"🔗 [انتقل للرسالة الأصلية](https://t.me/c/{chat.id}/{event.id})\n"
                    f"‏━━━━━━━━━━━━━━━━━━\n"
                    f"📝 **نص الاستفسار:**\n"
                    f"_{text}_\n"
                    f"‏━━━━━━━━━━━━━━━━━━\n"
                    f"👇 **تواصل مع العميل:**"
                )
                
                buttons = []
                if getattr(sender, 'username', None):
                    buttons.append([Button.url("💬 مراسلة خاصة", f"https://t.me/{sender.username}")])
                
                buttons.append([Button.url("⤴️ الرد في المجموعة", f"https://t.me/c/{chat.id}/{event.id}")])

                await client.send_message('student1_admin', display_message, buttons=buttons, silent=False)
                
    except Exception as e:
        print(f"⚠️ خطأ: {e}")

# --- 6. التشغيل ---
async def main():
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())

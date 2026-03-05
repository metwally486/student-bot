import os
import re
import threading
from datetime import datetime
from flask import Flask
from telethon import TelegramClient, events, Button

# --- 1. إعداد سيرفر وهمي لإبقاء الخدمة تعمل على Render ---
app = Flask(__name__)
@app.route('/')
def home(): return "الرصد الشامل يعمل بنجاح!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# --- 2. إعدادات حسابك (API ID & HASH) ---
# ملاحظة: تأكد من أن اسم الجلسة يطابق ملف .session المرفوع
api_id = 2040
api_hash = 'b18441a1ff607e10a989891a5462e627'
session_name = 'session_name' 

client = TelegramClient(session_name, api_id, api_hash)

# --- 3. وظيفة المعالجة والرصد الذكي ---
@client.on(events.NewMessage)
async def handler(event):
    try:
        # تجاهل الرسائل الخاصة (الرصد للمجموعات فقط)
        if event.is_private: return 
        
        text = event.raw_text.strip()
        length = len(text)
        
        # أ. الفلاتر (منع الروابط التسويقية وأرقام الجوال فقط)
        if any(x in text for x in ['http', 'wa.me', 't.me/+', 'snapchat.com']):
            return
        if re.search(r'\d{9,}', text): 
            return

        # ب. قائمة كلمات مفتاحية ضخمة (طلبات، أعذار، تخصصات، حد)
        keywords = [
            'حد', 'مين', 'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 'تلخيص', 
            'ممكن حل', 'أحتاج مساعدة', 'ميد ترم', 'فاينل', 'مين يعرف', 'مساعدة',
            'تصميم', 'برمجة', 'كود', 'باثيون', 'جافا', 'سي بلس', 'قاعدة بيانات', 'تطبيق', 'موقع',
            'فتوشوب', 'اليستريتور', 'لوقو', 'شعار', 'مونتاج', 'فيديو', 'هندسة',
            'إحصاء', 'احصاء', 'رياضيات', 'فيزياء', 'كيمياء', 'تحليل بيانات', 'ترجمة',
            'عذر', 'اعذار', 'إجازة مرضية', 'تقرير طبي', 'سكليف', 'غياب', 'مستشفى'
        ]
        
        # ج. كلمات الاستبعاد (لتجنب المروجين)
        forbidden = ['استثمار', 'ارباح', 'دخل', 'ضمان', 'رخيص', 'سعر خاص']

        # د. تطبيق شروط الدقة (الطول والكلمات)
        if any(word in text.lower() for word in keywords):
            if 15 <= length <= 120: # نطاق طول مرن
                if not any(bad in text for bad in forbidden):
                    
                    # جلب تفاصيل المصدر والوقت
                    chat = await event.get_chat()
                    chat_title = chat.title if hasattr(chat, 'title') else "مجموعة غير معروفة"
                    time_now = datetime.now().strftime("%I:%M %p")
                    
                    # تنسيق الواجهة الاحترافية
                    display_message = (
                        f"**🚀 رصد طلب/عذر جديد**\n"
                        f"‏━━━━━━━━━━━━━━━━━━\n"
                        f"**📍 المصدر:** `{chat_title}`\n"
                        f"**⏰ الوقت:** `{time_now}`\n"
                        f"‏━━━━━━━━━━━━━━━━━━\n"
                        f"**📝 النص المرصود:**\n"
                        f"_{text}_\n"
                        f"‏━━━━━━━━━━━━━━━━━━"
                    )
                    
                    # إرسال الرسالة مع زر الانتقال المباشر
                    await client.send_message(
                        'student1_admin', 
                        display_message, 
                        link_preview=False,
                        buttons=[
                            [Button.url("🔗 اذهب للطلب الآن", f"https://t.me/c/{chat.id}/{event.id}")]
                        ]
                    )
                    print(f"✅ تم رصد طلب من: {chat_title}")
                
    except Exception as e:
        print(f"⚠️ خطأ: {e}")

# --- 4. تشغيل الحساب ---
print("جاري بدء الرصد الشامل...")
client.start()
client.run_until_disconnected()

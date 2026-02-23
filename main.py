import telebot
from telebot import types
import os
from flask import Flask
from threading import Thread

# 1. إعداد خادم الويب للبقاء حياً على Render
app = Flask('')

@app.route('/')
def home():
    return "Bot is active with full keywords list!"

def run():
    # استخدام المنفذ 10000 لضمان استقرار الخدمة وفقاً لسجلات رندر
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. إعداد البوت والتوكن
TOKEN = "8414496098:AAGbAhsbf-7DnBoJT4tW0ZMN_osGyy_rntQ"
bot = telebot.TeleBot(TOKEN)

# 3. قائمة المديرين (أنت وصديقك 8329587970)
ADMIN_IDS = [8329587970]

# 4. قائمة الكلمات المفتاحية الشاملة جداً (لن يفوت البوت أي طلب)
KEYWORDS = [
    "واجب", "حل", "بحث", "عذر", "مطلوب", "أحتاج", "ابي", "بغيت", "مشروع", "اختبار",
    "كويز", "assignment", "homework", "تخرج", "ترجمة", "تلخيص", "بوربوينت", "تصميم",
    "سيرة ذاتية", "اعذار", "عذر طبي", "سكليف", "sick leave", "تقرير طبي", "مين يحل",
    "مين يسوي", "تنسيق", "ملخص", "نموذج", "تحليل", "بيانات", "عرض تقديمي"
]

CHANNEL = "@student1_admin"

@bot.message_handler(commands=['start'])
def start_admin(message):
    if message.from_user.id in ADMIN_IDS:
        bot.reply_to(message, "✅ أهلاً بك يا مدير! القائمة الكاملة للكلمات مفعلة الآن (واجبات، أعذار، مشاريع).")

@bot.message_handler(func=lambda message: True)
def monitor_requests(message):
    if not message.text:
        return
    
    text = message.text.lower()
    
    # التحقق من وجود الكلمات المفتاحية (تم تقليل شرط الطول لضمان الرصد)
    if any(word in text for word in KEYWORDS) and len(text) >= 2:
        sender_username = message.from_user.username
        sender_id = message.from_user.id
        
        # استخراج المصدر الأصلي (احترافي مثل الصورة المرفقة)
        if message.forward_from:
            source = f"👤 محول من: @{message.forward_from.username if message.forward_from.username else message.forward_from.id}"
        elif message.forward_from_chat:
            source = f"📢 المصدر: {message.forward_from_chat.title}"
        else:
            source = f"📍 المصدر: {message.chat.title if message.chat.title else 'محادثة خاصة'}"

        # تنسيق الرسالة النهائي بلمسة احترافية
        alert_msg = (
            f"⚡️ **طلب خدمة طلابية جديد**\n"
            f"──────────────────\n"
            f"👤 **العميل:** @{sender_username if sender_username else 'بدون يوزر'}\n"
            f"🆔 **ID العميل:** `{sender_id}`\n"
            f"📌 **{source}**\n\n"
            f"📝 **نص الطلب:**\n_{message.text}_\n"
            f"──────────────────\n"
            f"👇 **تواصل مع العميل مباشرة:**"
        )

        markup = types.InlineKeyboardMarkup()
        if sender_username:
            markup.add(types.InlineKeyboardButton("💬 مراسلة الطالب (خاص)", url=f"tg://resolve?domain={sender_username}"))
        
        try:
            bot.send_message(CHANNEL, alert_msg, reply_markup=markup, parse_mode="Markdown")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    keep_alive()
    print("Bot is starting with FULL keywords...")
    bot.infinity_polling()

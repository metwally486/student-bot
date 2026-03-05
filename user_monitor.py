import asyncio
from telethon import TelegramClient, events

# بيانات API العامة
API_ID = 2040 
API_HASH = 'b18441a1ff607e10a989891a5462e627'
TARGET_CHANNEL = 'student1_admin' 

client = TelegramClient('session_name', API_ID, API_HASH)

@client.on(events.NewMessage)
async def my_event_handler(event):
    if event.is_private: return 
    
    # القائمة الشاملة للكلمات
    KEYWORDS = [
        "واجب", "حل", "بحث", "مشاريع", "مشروع", "اختبار", "كويز", 
        "ميد", "فاينل", "تلخيص", "بوربوينت", "عرض", "تخرج", "أبي حل", 
        "احتاج حل", "مساعدة", "تكليف", "واجبات", "assignment", "quiz",
        "هومورك", "عملي", "نظري", "تقرير", "بحوث", "حلول"
    ]
    
    message_text = event.message.message.lower()
    if any(word in message_text for word in KEYWORDS):
        sender = await event.get_sender()
        chat = await event.get_chat()
        
        alert_msg = (
            f"🚀 **طلب جديد مرصود**\n"
            f"──────────────────\n"
            f"👤 **العميل:** @{sender.username if sender.username else 'بدون يوزر'}\n"
            f"📍 **المصدر:** {chat.title}\n\n"
            f"📝 **النص:**\n_{message_text}_\n"
            f"──────────────────\n"
            f"🔗 [مراسلة العميل](tg://user?id={sender.id})"
        )
        await client.send_message(TARGET_CHANNEL, alert_msg)

async def main():
    print("بدء تشغيل الرصد الشامل...")
    await client.start()
    print("الرصد يعمل الآن، يرجى مراقبة السجلات لإدخال الرقم إذا طلب منك.")
    await client.run_until_disconnected()

# تشغيل الكود بطريقة متوافقة مع Render
if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())

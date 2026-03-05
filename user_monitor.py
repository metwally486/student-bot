from telethon import TelegramClient, events

# استخدام أرقام API عامة لتجاوز خطأ الموقع الرسمي
API_ID = 2040 
API_HASH = 'b18441a1ff607e10a989891a5462e627'

# اسم القناة التي سيتم إرسال الطلبات إليها
TARGET_CHANNEL = 'student1_admin' 

client = TelegramClient('session_name', API_ID, API_HASH)

@client.on(events.NewMessage)
async def my_event_handler(event):
    if event.is_private: 
        return 
    
    # قائمة شاملة لكل كلمات الطلبات المتوقعة
    KEYWORDS = [
        "واجب", "حل", "بحث", "مشاريع", "مشروع", "اختبار", "كويز", 
        "ميد", "فاينل", "تحليف", "تلخيص", "بوربوينت", "عرض", 
        "تخرج", "أبي حل", "احتاج حل", "مساعدة", "تكليف", "واجبات"
    ]
    
    message_text = event.message.message
    # التحقق مما إذا كانت الرسالة تحتوي على أي كلمة من القائمة
    if any(word in message_text for word in KEYWORDS):
        sender = await event.get_sender()
        chat = await event.get_chat()
        
        # تنسيق الرسالة لتبدو احترافية ومنظمة
        alert_msg = (
            f"🚀 **طلب جديد تم رصده**\n"
            f"──────────────────\n"
            f"👤 **العميل:** @{sender.username if sender.username else 'بدون يوزر'}\n"
            f"📍 **المجموعة:** {chat.title}\n\n"
            f"📝 **نص الطلب:**\n_{message_text}_\n"
            f"──────────────────\n"
            f"🔗 [اضغط لمراسلة العميل](tg://user?id={sender.id})"
        )
        
        await client.send_message(TARGET_CHANNEL, alert_msg)

print("الرصد الذكي يعمل الآن بجميع الكلمات المفتاحية...")
client.start()
client.run_until_disconnected()

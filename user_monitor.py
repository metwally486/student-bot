import os
import asyncio
import httpx
import logging
from telethon import TelegramClient, events, Button

# ================== إعدادات الرادار الذكي ==================
API_ID = 2040 
API_HASH = "b18441a1ff607e10a989891a5462e627"
TARGET_CHANNEL = "student1_admin"  # معرف قناتك التي تستقبل الرصد
DEEPSEEK_KEY = "sk-2a1a0305161c4969abfa799d11c31244" # مفتاحك الخاص

# لمنع تكرار إرسال نفس الرسالة من الحسابين
processed_ids = set()

# إعداد الحسابات (رادار 1 و رادار 2)
accounts = [
    {'name': 'رادار [1]', 'session': 'session_name'},
    {'name': 'رادار [2]', 'session': 'session_2'}
]

# ================== دالة تحليل الذكاء الاصطناعي ==================
async def check_with_ai(text):
    """تحليل النص لجلب كافة الخدمات والاستفسارات ومنع الإعلانات"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json"
    }
    
    # التوجيه (Prompt) لجلب كل الخدمات والاستفسارات مهما كانت
    prompt = (
        f"حلل النص التالي بعناية. أجب بكلمة واحدة فقط 'yes' أو 'no'.\n"
        f"أجب بـ 'yes' إذا كان النص يمثل:\n"
        f"1- طلب خدمة (مهما كان نوعها: حل، واجب، تصميم، برمجة، ترجمة، بحث، إلخ).\n"
        f"2- استفسار أو سؤال أكاديمي أو عام يبحث عن مساعدة أو معلومة.\n"
        f"أجب بـ 'no' فقط إذا كان النص إعلاناً تجارياً صريحاً (مثل بيع متابعين، أعذار طبية، تأشيرات) أو كلام غير مفهوم.\n"
        f"النص: {text}"
    )
    
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3 # درجة مرونة تسمح بفهم الاستفسارات المتنوعة
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers, timeout=12)
            result = response.json()['choices'][0]['message']['content'].lower()
            return "yes" in result
    except Exception as e:
        print(f"⚠️ خطأ في AI: {e}")
        return True # في حال حدوث خطأ، نمرر الرسالة للقناة احتياطاً

# ================== دالة تشغيل الرادار لكل حساب ==================
async def start_radar(acc):
    client = TelegramClient(acc['session'], API_ID, API_HASH)
    radar_name = acc['name']
    
    @client.on(events.NewMessage)
    async def handler(event):
        # تجاهل الرسائل الخاصة والنصوص الفارغة
        if event.is_private or not event.raw_text:
            return
        
        # منع تكرار الرسالة إذا رصدها الحسابان معاً
        msg_id = f"{event.chat_id}_{event.id}"
        if msg_id in processed_ids:
            return
        processed_ids.add(msg_id)

        # التحليل بالذكاء الاصطناعي
        if await check_with_ai(event.raw_text):
            sender = await event.get_sender()
            username = getattr(sender, 'username', None)
            chat = await event.get_chat()
            
            # بناء أزرار التواصل الزرقاء
            buttons = []
            if username:
                buttons.append([Button.url("💬 مراسلة خاصة", f"https://t.me/{username}")])
            buttons.append([Button.url("⤴️ الرد في المجموعة", f"https://t.me/c/{event.chat_id}/{event.id}")])

            # تنسيق الرسالة النهائي
            msg = (
                f"🤖 **رصد ذكي (AI) عبر {radar_name}**\n"
                f"👤 **العميل:** {getattr(sender, 'first_name', 'مستخدم')}\n"
                f"🆔 **ID:** `{sender.id if sender else 'N/A'}`\n"
                f"📍 **المصدر:** `{getattr(chat, 'title', 'مجموعة غير معروفة')}`\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"📝 **النص المرصود:**\n_{event.raw_text[:600]}_\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"👇 **تواصل مع العميل مباشرة:**"
            )
            
            try:
                await client.send_message(TARGET_CHANNEL, msg, buttons=buttons)
            except Exception as e:
                print(f"❌ خطأ في الإرسال للقناة (تأكد من وجود الحساب كمسؤول): {e}")

    # بدء تشغيل العميل مع إعادة الاتصال التلقائي
    while True:
        try:
            await client.start()
            print(f"✅ {radar_name} متصل الآن بذكاء DeepSeek")
            await client.run_until_disconnected()
        except Exception as e:
            print(f"⚠️ انقطع اتصال {radar_name}.. إعادة المحاولة: {e}")
            await asyncio.sleep(10)

# ================== التشغيل الرئيسي للمشروع ==================
async def main():
    print("🚀 جاري تشغيل رادارات الرصد الشامل...")
    await asyncio.gather(*(start_radar(acc) for acc in accounts))

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 تم إيقاف الرادار يدوياً.")

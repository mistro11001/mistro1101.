# ============================================
# bot.py - بوت سحب المقاطع من قناة محددة
# ============================================

import logging
import os
import json
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===== التحقق من التوكن =====
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("❌ خطأ: لم يتم تعيين BOT_TOKEN في متغيرات البيئة!")
    print("📌 يرجى إضافة BOT_TOKEN في Railway > Variables")
    exit(1)

ADMIN_ID = int(os.getenv("ADMIN_ID", 1025310531))

# ===== إعدادات القناة =====
VIDEO_CHANNEL = "@col19881"  # القناة المرجعية
TOTAL_VIDEOS = 900  # إجمالي عدد المقاطع
FIRST_VIDEO_ID = 2  # أول مقطع

# ===== قنوات الاشتراك الإجباري =====
required_channels = []  # المطور يضيفها

# ===== بيانات المستخدمين =====
user_data = {}
user_activity = {}
command_usage = {}
user_positions = {}

# ===== تحميل البيانات =====
def load_data():
    global user_data, user_activity, command_usage, required_channels
    try:
        with open('user_data.json', 'r', encoding='utf-8') as f:
            user_data = json.load(f)
    except:
        user_data = {}
    
    try:
        with open('user_activity.json', 'r', encoding='utf-8') as f:
            user_activity = json.load(f)
    except:
        user_activity = {}
    
    try:
        with open('command_usage.json', 'r', encoding='utf-8') as f:
            command_usage = json.load(f)
    except:
        command_usage = {}
    
    try:
        with open('required_channels.json', 'r', encoding='utf-8') as f:
            required_channels = json.load(f)
    except:
        required_channels = []

def save_data():
    with open('user_data.json', 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)
    with open('user_activity.json', 'w', encoding='utf-8') as f:
        json.dump(user_activity, f, ensure_ascii=False, indent=2)
    with open('command_usage.json', 'w', encoding='utf-8') as f:
        json.dump(command_usage, f, ensure_ascii=False, indent=2)
    with open('required_channels.json', 'w', encoding='utf-8') as f:
        json.dump(required_channels, f, ensure_ascii=False, indent=2)

load_data()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== Application =====
application = Application.builder().token(TOKEN).build()

# ===== دوال المساعدة =====
async def check_sub(user_id, context):
    """فحص الاشتراك في جميع القنوات المطلوبة"""
    if not required_channels:
        return True
    
    for ch in required_channels:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

def get_channels_keyboard():
    """لوحة مفاتيح قنوات الاشتراك"""
    keyboard = []
    for ch in required_channels:
        clean_ch = ch.replace('@', '')
        keyboard.append([InlineKeyboardButton(
            f"📢 {ch}", 
            url=f"https://t.me/{clean_ch}"
        )])
    keyboard.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")])
    return InlineKeyboardMarkup(keyboard)

def log_user_activity(user_id, command):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_activity[str(user_id)] = now
    if command not in command_usage:
        command_usage[command] = 0
    command_usage[command] += 1
    save_data()

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

# ===== دوال المقاطع =====
async def send_videos(context, chat_id, num1, num2):
    """إرسال مقطعين من القناة"""
    try:
        if num1 <= TOTAL_VIDEOS:
            await context.bot.copy_message(
                chat_id=chat_id,
                from_chat_id=VIDEO_CHANNEL,
                message_id=FIRST_VIDEO_ID + num1 - 1
            )
        if num2 <= TOTAL_VIDEOS:
            await context.bot.copy_message(
                chat_id=chat_id,
                from_chat_id=VIDEO_CHANNEL,
                message_id=FIRST_VIDEO_ID + num2 - 1
            )
        return True
    except Exception as e:
        logger.error(f"خطأ في جلب المقطع: {e}")
        return False

def get_keyboard(current):
    """أزرار التنقل بين المقاطع"""
    row = []
    if current > 1:
        row.append(InlineKeyboardButton("⬅️ السابق", callback_data="prev"))
    row.append(InlineKeyboardButton(f"📌 {current}-{current+1}", callback_data="none"))
    if current + 2 <= TOTAL_VIDEOS:
        row.append(InlineKeyboardButton("التالي ➡️", callback_data="next"))
    
    keyboard = [row]
    
    # زر الرئيسية للمستخدم العادي
    main_buttons = [InlineKeyboardButton("🏠 الرئيسية", callback_data="home")]
    
    # زر لوحة التحكم للمطور
    if is_admin(update_context_user_id()):
        main_buttons.append(InlineKeyboardButton("⚙️ التحكم", callback_data="admin_panel"))
    
    keyboard.append(main_buttons)
    return InlineKeyboardMarkup(keyboard)

def update_context_user_id():
    """دالة مساعدة للحصول على user_id في context"""
    return None

# ===== دوال الإعدادات للمطور =====
async def show_admin_panel(update, context, user_id):
    """عرض لوحة تحكم المطور"""
    keyboard = [
        [InlineKeyboardButton("📢 إدارة قنوات الاشتراك", callback_data="admin_required_channels")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("📥 تصدير البيانات", callback_data="admin_export")],
        [InlineKeyboardButton("🔙 رجوع للرئيسية", callback_data="home")]
    ]
    
    text = f"⚙️ **لوحة تحكم المطور**\n\n"
    text += f"📹 قناة المقاطع: {VIDEO_CHANNEL}\n"
    text += f"📢 عدد قنوات الاشتراك: {len(required_channels)}\n"
    text += f"👥 إجمالي المستخدمين: {len(user_data)}"
    
    if isinstance(update, Update) and update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ===== إدارة قنوات الاشتراك =====
async def manage_required_channels(update, context):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for i, ch in enumerate(required_channels):
        keyboard.append([
            InlineKeyboardButton(f"🗑️ {ch}", callback_data=f"remove_required_{i}")
        ])
    
    keyboard.append([InlineKeyboardButton("➕ إضافة قناة اشتراك", callback_data="add_required_channel")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
    
    text = "📢 **إدارة قنوات الاشتراك الإجباري**\n\n"
    if required_channels:
        text += "القنوات الحالية:\n"
        for ch in required_channels:
            text += f"• {ch}\n"
    else:
        text += "❌ لا توجد قنوات اشتراك إجباري\n\n"
    text += "\nالمستخدم يجب أن يشترك بكل هذه القنوات لاستخدام البوت."
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def add_required_channel(update, context):
    query = update.callback_query
    await query.answer()
    
    context.user_data['waiting_for'] = 'add_required_channel'
    
    await query.message.edit_text(
        "📝 **إضافة قناة اشتراك إجباري جديدة**\n\n"
        "أرسل معرف القناة (مثال: @channel_name)\n"
        "أو /cancel للإلغاء"
    )

async def handle_add_required_channel(update, context):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    channel = update.message.text.strip()
    
    if channel.startswith('@'):
        required_channels.append(channel)
        save_data()
        await update.message.reply_text(f"✅ تم إضافة القناة {channel} بنجاح!")
    else:
        await update.message.reply_text("❌ يجب أن يبدأ المعرف بـ @")
    
    context.user_data['waiting_for'] = None
    await show_admin_panel(update, context, user_id)

async def remove_required_channel(update, context):
    query = update.callback_query
    await query.answer()
    
    index = int(query.data.split('_')[2])
    removed = required_channels.pop(index)
    save_data()
    
    await query.message.reply_text(f"✅ تم حذف القناة {removed}")
    await manage_required_channels(update, context)

# ===== الإحصائيات =====
async def admin_stats(update, context):
    query = update.callback_query
    await query.answer()
    
    total_users = len(user_data)
    
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    
    active_today = sum(1 for u in user_activity.values() if u.startswith(today))
    active_week = sum(1 for u in user_activity.values() if u >= week_ago)
    active_month = sum(1 for u in user_activity.values() if u >= month_ago)
    
    stats_text = f"📊 **إحصائيات البوت**\n\n"
    stats_text += f"👥 **إجمالي المستخدمين:** {total_users}\n"
    stats_text += f"🟢 **نشط اليوم:** {active_today}\n"
    stats_text += f"🟡 **نشط الأسبوع:** {active_week}\n"
    stats_text += f"🟠 **نشط الشهر:** {active_month}\n\n"
    
    sorted_commands = sorted(command_usage.items(), key=lambda x: x[1], reverse=True)[:5]
    stats_text += "📌 **الأوامر الأكثر استخداماً:**\n"
    for cmd, count in sorted_commands:
        stats_text += f"`{cmd}`: {count} مرة\n"
    
    await query.message.edit_text(stats_text)

async def admin_users(update, context):
    query = update.callback_query
    await query.answer()
    
    users_list = list(user_data.values())
    users_list.reverse()
    users_list = users_list[:10]
    
    text = "👥 **آخر 10 مستخدمين:**\n\n"
    for i, user in enumerate(users_list, 1):
        name = user.get('first_name', 'غير معروف')
        username = user.get('username', '')
        added = user.get('added_date', '')
        
        text += f"{i}. **{name}**\n"
        if username:
            text += f"   🆔 @{username}\n"
        text += f"   📅 {added}\n\n"
    
    await query.message.edit_text(text)

async def admin_export(update, context):
    query = update.callback_query
    await query.answer()
    
    data = {
        'users': user_data,
        'activity': user_activity,
        'commands': command_usage,
        'required_channels': required_channels,
        'video_channel': VIDEO_CHANNEL,
        'export_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'total_users': len(user_data)
    }
    
    with open('export_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    await context.bot.send_document(
        chat_id=query.message.chat.id,
        document=open('export_data.json', 'rb'),
        filename=f'bot_export_{datetime.now().strftime("%Y%m%d")}.json',
        caption="📊 **تصدير بيانات البوت والإعدادات**"
    )
    
    os.remove('export_data.json')

# ===== دوال البوت الرئيسية =====
async def start(update, context):
    user = update.message.from_user
    user_id = user.id
    
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            'first_name': user.first_name,
            'last_name': user.last_name or '',
            'username': user.username or '',
            'user_id': user_id,
            'added_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'is_bot': user.is_bot,
            'language_code': user.language_code or ''
        }
        save_data()
    
    log_user_activity(user_id, "/start")
    
    is_subscribed = await check_sub(user_id, context)
    
    if not is_subscribed and required_channels:
        await update.message.reply_text(
            "⚠️ **تنبيه مهم!**\n\n"
            "يجب الاشتراك بـ **جميع** القنوات التالية أولاً:\n\n"
            "بعد الاشتراك بكل القنوات، اضغط 'تحقق من الاشتراك'",
            reply_markup=get_channels_keyboard()
        )
        return
    
    # تعيين الموضع الابتدائي
    user_positions[user_id] = 1
    
    keyboard = [
        [InlineKeyboardButton("🎬 عرض المقاطع", callback_data="next")],
    ]
    
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")])
    
    await update.message.reply_text(
        "🎉 **أهلاً وسهلاً!**\n\n"
        "✅ شكراً لاشتراكك!\n\n"
        "اضغط 'عرض المقاطع' لتبدأ! 🎬",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_videos_start(update, context):
    """بدء عرض المقاطع"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    # تعيين الموضع الابتدائي
    user_positions[user_id] = 1
    
    current = 1
    success = await send_videos(context, query.message.chat.id, current, current + 1)
    
    if not success:
        await query.message.reply_text("❌ خطأ في جلب المقاطع.")
        return
    
    user_positions[user_id] = current + 2
    
    # بناء الأزرار مع زر التحكم للمطور
    keyboard = get_keyboard_with_admin(current, user_id)
    
    await query.message.reply_text(
        f"🎬 **المقطع {current} و {current+1}**",
        reply_markup=keyboard
    )

def get_keyboard_with_admin(current, user_id):
    """أزرار التنقل مع زر التحكم للمطور"""
    row = []
    if current > 1:
        row.append(InlineKeyboardButton("⬅️ السابق", callback_data="prev"))
    row.append(InlineKeyboardButton(f"📌 {current}-{current+1}", callback_data="none"))
    if current + 2 <= TOTAL_VIDEOS:
        row.append(InlineKeyboardButton("التالي ➡️", callback_data="next"))
    
    keyboard = [row]
    
    # زر الرئيسية
    main_buttons = [InlineKeyboardButton("🏠 الرئيسية", callback_data="home")]
    
    # زر لوحة التحكم للمطور
    if is_admin(user_id):
        main_buttons.append(InlineKeyboardButton("⚙️ التحكم", callback_data="admin_panel"))
    
    keyboard.append(main_buttons)
    return InlineKeyboardMarkup(keyboard)

# ===== معالج الأزرار الرئيسي =====
async def buttons(update, context):
    query = update.callback_query
    user_id = int(query.from_user.id)
    await query.answer()
    
    # فحص الاشتراك
    is_subscribed = await check_sub(user_id, context)
    
    if not is_subscribed and required_channels:
        await query.message.reply_text(
            "❌ **تحذير!**\n\n"
            "لقد طلعت من أحد القنوات! 🚫\n\n"
            "يجب الاشتراك بـ **جميع** القنوات التالية:\n\n"
            "بعد الاشتراك بكل القنوات، جرب مرة أخرى!",
            reply_markup=get_channels_keyboard()
        )
        return
    
    log_user_activity(user_id, query.data)
    
    if query.data == "check_sub":
        is_sub = await check_sub(user_id, context)
        if is_sub:
            keyboard = [
                [InlineKeyboardButton("🎬 عرض المقاطع", callback_data="next")],
            ]
            if is_admin(user_id):
                keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")])
            
            await query.message.edit_text(
                "✅ **تم التحقق!**\n\n"
                "أنت مشترك بجميع القنوات! 🎉\n\n"
                "اضغط 'عرض المقاطع' للبدء.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.message.reply_text(
                "❌ لم تشترك بجميع القنوات بعد!",
                reply_markup=get_channels_keyboard()
            )
    
    elif query.data == "next":
        current = user_positions.get(user_id, 1)
        
        if current > TOTAL_VIDEOS:
            await query.message.reply_text("❌ انتهت المقاطع!")
            return
        
        success = await send_videos(context, query.message.chat.id, current, current + 1)
        if not success:
            await query.message.reply_text("❌ خطأ في جلب المقاطع.")
            return
        
        user_positions[user_id] = current + 2
        await query.message.reply_text(
            f"🎬 **المقطع {current} و {current+1}**",
            reply_markup=get_keyboard_with_admin(current, user_id)
        )
    
    elif query.data == "prev":
        current = user_positions.get(user_id, 1)
        prev = max(1, current - 2)
        
        success = await send_videos(context, query.message.chat.id, prev, prev + 1)
        if not success:
            await query.message.reply_text("❌ خطأ في جلب المقاطع.")
            return
        
        user_positions[user_id] = prev
        await query.message.reply_text(
            f"🎬 **المقطع {prev} و {prev+1}**",
            reply_markup=get_keyboard_with_admin(prev, user_id)
        )
    
    elif query.data == "home":
        user_positions[user_id] = 1
        keyboard = [
            [InlineKeyboardButton("🎬 عرض المقاطع", callback_data="next")],
        ]
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")])
        
        await query.message.edit_text(
            "🏠 **القائمة الرئيسية**\n\nاختر أحد الخيارات:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data == "admin_panel":
        if not is_admin(user_id):
            await query.message.reply_text("⛔ هذا الخيار خاص بالمطور فقط.")
            return
        await show_admin_panel(update, context, user_id)
    
    elif query.data == "admin_required_channels":
        if not is_admin(user_id):
            await query.message.reply_text("⛔ غير مصرح.")
            return
        await manage_required_channels(update, context)
    
    elif query.data == "admin_stats":
        if not is_admin(user_id):
            await query.message.reply_text("⛔ غير مصرح.")
            return
        await admin_stats(update, context)
    
    elif query.data == "admin_users":
        if not is_admin(user_id):
            await query.message.reply_text("⛔ غير مصرح.")
            return
        await admin_users(update, context)
    
    elif query.data == "admin_export":
        if not is_admin(user_id):
            await query.message.reply_text("⛔ غير مصرح.")
            return
        await admin_export(update, context)
    
    elif query.data.startswith("remove_required_"):
        if not is_admin(user_id):
            await query.message.reply_text("⛔ غير مصرح.")
            return
        await remove_required_channel(update, context)
    
    elif query.data == "add_required_channel":
        if not is_admin(user_id):
            await query.message.reply_text("⛔ غير مصرح.")
            return
        await add_required_channel(update, context)
    
    elif query.data == "none":
        await query.answer("📌 لا يمكن الضغط هنا")

# ===== أوامر النص =====
async def handle_text(update, context):
    user_id = update.message.from_user.id
    waiting_for = context.user_data.get('waiting_for')
    
    if waiting_for == 'add_required_channel':
        await handle_add_required_channel(update, context)
    else:
        await update.message.reply_text("❌ غير معروف. استخدم /start للبدء")

async def cancel(update, context):
    context.user_data['waiting_for'] = None
    await update.message.reply_text("✅ تم الإلغاء")

# ===== تشغيل البوت =====
def main():
    try:
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("cancel", cancel))
        application.add_handler(CallbackQueryHandler(buttons))
        application.add_handler(CommandHandler("text", handle_text))
        
        print("🚀 البوت شغال...")
        print(f"📹 قناة المقاطع: {VIDEO_CHANNEL}")
        print(f"👥 إجمالي المقاطع: {TOTAL_VIDEOS}")
        application.run_polling()
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {e}")

if __name__ == "__main__":
    main()

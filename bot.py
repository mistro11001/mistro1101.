import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, JobQueue
from datetime import datetime, timedelta
import json
import os

# ===== التوكن والإعدادات الأساسية =====
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 1025310531))

# ===== إعدادات البوت =====
SCHEDULE_TIME = 3600  # كل ساعة (بالثواني)

# ===== متغيرات الإعدادات =====
config = {
    "video_channels": [],  # قائمة القنوات المصدر للمقاطع
    "required_channels": [],  # قائمة قنوات الاشتراك الإجباري
    "schedule_enabled": True,
    "schedule_interval": 3600,
    "last_posted": None
}

# ===== بيانات المستخدمين =====
user_data = {}
user_activity = {}
command_usage = {}
user_positions = {}

# ===== تحميل البيانات =====
def load_data():
    global user_data, user_activity, command_usage, config
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
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        config = {
            "video_channels": [],
            "required_channels": [],
            "schedule_enabled": True,
            "schedule_interval": 3600,
            "last_posted": None
        }

def save_data():
    with open('user_data.json', 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)
    with open('user_activity.json', 'w', encoding='utf-8') as f:
        json.dump(user_activity, f, ensure_ascii=False, indent=2)
    with open('command_usage.json', 'w', encoding='utf-8') as f:
        json.dump(command_usage, f, ensure_ascii=False, indent=2)
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

load_data()

logging.basicConfig(level=logging.INFO)

# ===== Application =====
application = Application.builder().token(TOKEN).build()

# ===== دوال المساعدة =====
async def check_sub(user_id, context):
    """فحص الاشتراك في جميع القنوات المطلوبة"""
    if not config["required_channels"]:
        return True  # إذا ما في قنوات مطلوبة
    
    for ch in config["required_channels"]:
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
    for ch in config["required_channels"]:
        keyboard.append([InlineKeyboardButton(ch, url=f"https://t.me/{ch.replace('@','')}")])
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

# ===== دوال الإعدادات =====
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    """عرض لوحة تحكم المطور"""
    keyboard = [
        [InlineKeyboardButton("📹 إدارة قنوات المقاطع", callback_data="admin_video_channels")],
        [InlineKeyboardButton("📢 إدارة قنوات الاشتراك", callback_data="admin_required_channels")],
        [InlineKeyboardButton("⏰ إدارة الجدولة", callback_data="admin_schedule")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("📥 تصدير البيانات", callback_data="admin_export")],
        [InlineKeyboardButton("🔙 رجوع للرئيسية", callback_data="home")]
    ]
    
    text = f"⚙️ **لوحة تحكم المطور**\n\n"
    text += f"📹 عدد قنوات المقاطع: {len(config['video_channels'])}\n"
    text += f"📢 عدد قنوات الاشتراك: {len(config['required_channels'])}\n"
    text += f"⏰ الجدولة: {'🟢 مفعلة' if config['schedule_enabled'] else '🔴 معطلة'}\n"
    text += f"👥 إجمالي المستخدمين: {len(user_data)}"
    
    if isinstance(update, Update) and update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ===== إدارة قنوات المقاطع =====
async def manage_video_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for i, ch in enumerate(config["video_channels"]):
        keyboard.append([
            InlineKeyboardButton(f"🗑️ {ch}", callback_data=f"remove_video_{i}")
        ])
    
    keyboard.append([InlineKeyboardButton("➕ إضافة قناة", callback_data="add_video_channel")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
    
    text = "📹 **إدارة قنوات المقاطع**\n\n"
    if config["video_channels"]:
        text += "القنوات الحالية:\n"
        for ch in config["video_channels"]:
            text += f"• {ch}\n"
    else:
        text += "❌ لا توجد قنوات مقاطع حالياً\n\n"
    text += "\nيمكنك إضافة قناة جديدة أو حذف قناة موجودة."
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def add_video_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['waiting_for'] = 'add_video_channel'
    
    await query.message.edit_text(
        "📝 **إضافة قناة مقطع جديدة**\n\n"
        "أرسل معرف القناة (مثال: @channel_name)\n"
        "أو /cancel للإلغاء"
    )

async def handle_add_video_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    channel = update.message.text.strip()
    
    if channel.startswith('@'):
        config["video_channels"].append(channel)
        save_data()
        await update.message.reply_text(f"✅ تم إضافة القناة {channel} بنجاح!")
    else:
        await update.message.reply_text("❌ يجب أن يبدأ المعرف بـ @")
    
    context.user_data['waiting_for'] = None
    await show_admin_panel(update, context, user_id)

async def remove_video_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    index = int(query.data.split('_')[2])
    removed = config["video_channels"].pop(index)
    save_data()
    
    await query.message.reply_text(f"✅ تم حذف القناة {removed}")
    await manage_video_channels(update, context)

# ===== إدارة قنوات الاشتراك =====
async def manage_required_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for i, ch in enumerate(config["required_channels"]):
        keyboard.append([
            InlineKeyboardButton(f"🗑️ {ch}", callback_data=f"remove_required_{i}")
        ])
    
    keyboard.append([InlineKeyboardButton("➕ إضافة قناة اشتراك", callback_data="add_required_channel")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
    
    text = "📢 **إدارة قنوات الاشتراك الإجباري**\n\n"
    if config["required_channels"]:
        text += "القنوات الحالية:\n"
        for ch in config["required_channels"]:
            text += f"• {ch}\n"
    else:
        text += "❌ لا توجد قنوات اشتراك إجباري\n\n"
    text += "\nالمستخدم يجب أن يشترك بكل هذه القنوات لاستخدام البوت."
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def add_required_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['waiting_for'] = 'add_required_channel'
    
    await query.message.edit_text(
        "📝 **إضافة قناة اشتراك إجباري جديدة**\n\n"
        "أرسل معرف القناة (مثال: @channel_name)\n"
        "أو /cancel للإلغاء"
    )

async def handle_add_required_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    channel = update.message.text.strip()
    
    if channel.startswith('@'):
        config["required_channels"].append(channel)
        save_data()
        await update.message.reply_text(f"✅ تم إضافة القناة {channel} بنجاح!")
    else:
        await update.message.reply_text("❌ يجب أن يبدأ المعرف بـ @")
    
    context.user_data['waiting_for'] = None
    await show_admin_panel(update, context, user_id)

async def remove_required_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    index = int(query.data.split('_')[2])
    removed = config["required_channels"].pop(index)
    save_data()
    
    await query.message.reply_text(f"✅ تم حذف القناة {removed}")
    await manage_required_channels(update, context)

# ===== إدارة الجدولة =====
async def manage_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton(
            "🟢 تفعيل" if not config["schedule_enabled"] else "🔴 تعطيل", 
            callback_data="toggle_schedule"
        )],
        [InlineKeyboardButton("⏱️ تغيير الفترة", callback_data="change_interval")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    
    status = "مفعلة 🟢" if config["schedule_enabled"] else "معطلة 🔴"
    interval_min = config["schedule_interval"] // 60
    
    text = f"⏰ **إدارة الجدولة**\n\n"
    text += f"الحالة: {status}\n"
    text += f"الفترة: كل {interval_min} دقيقة\n"
    text += f"آخر نشر: {config['last_posted'] or 'لم يتم بعد'}"
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def toggle_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    config["schedule_enabled"] = not config["schedule_enabled"]
    save_data()
    
    if config["schedule_enabled"]:
        await query.message.reply_text("🟢 تم تفعيل الجدولة")
        schedule_posts(context.bot)
    else:
        await query.message.reply_text("🔴 تم تعطيل الجدولة")
        # إيقاف الجدولة
    
    await manage_schedule(update, context)

async def change_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['waiting_for'] = 'change_interval'
    
    await query.message.edit_text(
        "⏱️ **تغيير فترة الجدولة**\n\n"
        "أرسل الوقت بالدقائق (مثال: 30)\n"
        "أو /cancel للإلغاء"
    )

async def handle_change_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    try:
        minutes = int(update.message.text.strip())
        if minutes < 1:
            await update.message.reply_text("❌ يجب أن تكون الدقائق أكثر من 0")
            return
        
        config["schedule_interval"] = minutes * 60
        save_data()
        await update.message.reply_text(f"✅ تم تغيير الفترة إلى {minutes} دقيقة")
        
        # إعادة جدولة
        job_queue = context.job_queue
        if job_queue:
            job_queue.stop()
            schedule_posts(context.bot)
        
        await show_admin_panel(update, context, user_id)
    except ValueError:
        await update.message.reply_text("❌ يرجى إدخال رقم صحيح")
    
    context.user_data['waiting_for'] = None

# ===== دوال الجدولة والنشر =====
async def post_videos(context: ContextTypes.DEFAULT_TYPE):
    """نشر مقاطع من القنوات المسجلة"""
    if not config["schedule_enabled"]:
        return
    
    if not config["video_channels"]:
        logging.warning("لا توجد قنوات مقاطع للنشر")
        return
    
    try:
        # تجربة جلب مقطع من أول قناة مسجلة
        channel = config["video_channels"][0]
        # هنا يمكنك تحديد كيفية جلب المقاطع
        # مثلاً: جلب آخر منشور من القناة وإرساله
        
        config["last_posted"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_data()
        logging.info(f"تم نشر مقطع من {channel}")
        
    except Exception as e:
        logging.error(f"خطأ في النشر المجدول: {e}")

def schedule_posts(bot):
    """جدولة النشر التلقائي"""
    job_queue = application.job_queue
    if job_queue and config["schedule_enabled"]:
        job_queue.run_repeating(
            post_videos,
            interval=config["schedule_interval"],
            first=10
        )

# ===== دوال البوت الرئيسية =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    # فحص الاشتراك
    is_subscribed = await check_sub(user_id, context)
    
    if not is_subscribed and config["required_channels"]:
        await update.message.reply_text(
            "⚠️ **تنبيه مهم!**\n\n"
            "يجب الاشتراك بـ **جميع** القنوات التالية أولاً:\n\n"
            "بعد الاشتراك بكل القنوات، اضغط 'تحقق من الاشتراك'",
            reply_markup=get_channels_keyboard()
        )
        return
    
    # مشترك
    keyboard = [
        [InlineKeyboardButton("📹 عرض المقاطع", callback_data="show_videos")],
    ]
    
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")])
    
    await update.message.reply_text(
        "🎉 **أهلاً وسهلاً!**\n\n"
        "بوت إدارة القنوات والمقاطع\n"
        "اختر أحد الخيارات أدناه",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if not config["video_channels"]:
        await query.message.reply_text("❌ لا توجد قنوات مقاطع حالياً")
        return
    
    text = "📹 **قنوات المقاطع المتاحة:**\n\n"
    for ch in config["video_channels"]:
        text += f"• {ch}\n"
    
    text += "\nسيتم جلب المقاطع من هذه القنوات تلقائياً"
    await query.message.reply_text(text)

# ===== الإحصائيات والبيانات =====
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def admin_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = {
        'users': user_data,
        'activity': user_activity,
        'commands': command_usage,
        'config': config,
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

# ===== معالج الأزرار الرئيسي =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = int(query.from_user.id)
    await query.answer()
    
    # فحص الاشتراك
    is_subscribed = await check_sub(user_id, context)
    
    if not is_subscribed and config["required_channels"]:
        await query.message.reply_text(
            "❌ **تحذير!**\n\n"
            "لقد طلعت من أحد القنوات! 🚫\n\n"
            "يجب الاشتراك بـ **جميع** القنوات التالية:\n\n"
            "بعد الاشتراك بكل القنوات، جرب مرة أخرى!",
            reply_markup=get_channels_keyboard()
        )
        return
    
    log_user_activity(user_id, query.data)
    
    # ===== معالجة الأزرار =====
    if query.data == "check_sub":
        is_sub = await check_sub(user_id, context)
        if is_sub:
            await query.message.edit_text(
                "✅ **تم التحقق!**\n\n"
                "أنت مشترك بجميع القنوات! 🎉\n\n"
                "اختر أحد الخيارات أدناه.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📹 عرض المقاطع", callback_data="show_videos")],
                    [InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")] if is_admin(user_id) else []
                ])
            )
        else:
            await query.message.reply_text(
                "❌ لم تشترك بجميع القنوات بعد!",
                reply_markup=get_channels_keyboard()
            )
    
    elif query.data == "show_videos":
        await show_videos(update, context)
    
    elif query.data == "admin_panel":
        if not is_admin(user_id):
            await query.message.reply_text("⛔ هذا الخيار خاص بالمطور فقط.")
            return
        await show_admin_panel(update, context, user_id)
    
    elif query.data == "admin_stats":
        await admin_stats(update, context)
    
    elif query.data == "admin_users":
        await admin_users(update, context)
    
    elif query.data == "admin_export":
        await admin_export(update, context)
    
    elif query.data == "admin_video_channels":
        await manage_video_channels(update, context)
    
    elif query.data == "admin_required_channels":
        await manage_required_channels(update, context)
    
    elif query.data == "admin_schedule":
        await manage_schedule(update, context)
    
    elif query.data.startswith("remove_video_"):
        await remove_video_channel(update, context)
    
    elif query.data.startswith("remove_required_"):
        await remove_required_channel(update, context)
    
    elif query.data == "add_video_channel":
        await add_video_channel(update, context)
    
    elif query.data == "add_required_channel":
        await add_required_channel(update, context)
    
    elif query.data == "toggle_schedule":
        await toggle_schedule(update, context)
    
    elif query.data == "change_interval":
        await change_interval(update, context)
    
    elif query.data == "home":
        keyboard = [
            [InlineKeyboardButton("📹 عرض المقاطع", callback_data="show_videos")],
        ]
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")])
        
        await query.message.edit_text(
            "🏠 **القائمة الرئيسية**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ===== أوامر النص =====
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    waiting_for = context.user_data.get('waiting_for')
    
    if waiting_for == 'add_video_channel':
        await handle_add_video_channel(update, context)
    elif waiting_for == 'add_required_channel':
        await handle_add_required_channel(update, context)
    elif waiting_for == 'change_interval':
        await handle_change_interval(update, context)
    else:
        await update.message.reply_text("❌ غير معروف. استخدم /start للبدء")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['waiting_for'] = None
    await update.message.reply_text("✅ تم الإلغاء")

# ===== تشغيل البوت =====
def main():
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(buttons))
    application.add_handler(CommandHandler("text", handle_text))
    
    # جدولة النشر التلقائي
    schedule_posts(application.bot)
    
    print("🚀 البوت شغال...")
    application.run_polling()

if __name__ == "__main__":
    main()

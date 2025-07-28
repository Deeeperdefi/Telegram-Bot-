# -*- coding: utf-8 -*-
import logging
import datetime
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# --- Updated Links with Emojis ---
YOUTUBE_URL = "https://cutt.ly/GrYcicUY"
X_URL = "https://x.com/ifarttoken"
FACEBOOK_URL = "https://web.facebook.com/cryptoadvertiser11"
SPONSOR_URL = "https://www.profitableratecpm.com/h7636fr3k?key=e9c1b80bf6645940264046b0a5f6ce72"
MINI_APP_URL = "https://venerable-basbousa-d50332.netlify.app/"

# Telegram join links
TELEGRAM_GROUP_URL = "https://t.me/+h2YUHTxOo7ZlYWE8"
TELEGRAM_CHANNEL_URL = "https://t.me/ifarttoken"

# --- Bot Data Storage ---
user_progress = {}
daily_reminder_users = set()

# --- Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Modern Task Definitions ---
TASKS = [
    {
        "name": "group",
        "intro": "🌟 *Step 1/6: Join Our Community*\n\nJoin our exclusive Telegram group to connect with other iFart enthusiasts and get the latest updates!",
        "button_text": "✨ Join Group",
        "url": TELEGRAM_GROUP_URL,
        "emoji": "💬"
    },
    {
        "name": "channel",
        "intro": "🚀 *Step 2/6: Stay Updated*\n\nSubscribe to our official Telegram channel for important announcements and exclusive content!",
        "button_text": "📢 Join Channel",
        "url": TELEGRAM_CHANNEL_URL,
        "emoji": "📢"
    },
    {
        "name": "sponsor",
        "intro": "💎 *Step 3/6: Support Our Sponsor*\n\nVisit our sponsor's website for 30 seconds to help keep iFart running!",
        "button_text": "❤️ Visit Sponsor",
        "url": SPONSOR_URL,
        "emoji": "🤝"
    },
    {
        "name": "youtube",
        "intro": "🎬 *Step 4/6: Subscribe on YouTube*\n\nWatch our latest videos and tutorials to maximize your iFart experience!",
        "button_text": "🎥 Subscribe",
        "url": YOUTUBE_URL,
        "emoji": "📺"
    },
    {
        "name": "twitter",
        "intro": "🐦 *Step 5/6: Follow on X*\n\nStay updated with our latest tweets and crypto insights!",
        "button_text": "📱 Follow Us",
        "url": X_URL,
        "emoji": "🐦"
    },
    {
        "name": "facebook",
        "intro": "👍 *Step 6/6: Like on Facebook*\n\nConnect with our growing community on Facebook!",
        "button_text": "👍 Like Page",
        "url": FACEBOOK_URL,
        "emoji": "👍"
    }
]

# --- Visual Elements ---
WELCOME_MESSAGE = """
🎉 *Welcome to iFart Token!* 🎉

Earn $IFART tokens by completing simple social tasks. Complete all 6 steps to unlock the iFart Mini App!

📊 *Your Progress:* 0/6 tasks completed
💰 *Potential Earnings:* 100 $IFART

Let's get started with the first task!
"""

PROGRESS_BAR = {
    0: "🟦⬜⬜⬜⬜⬜ 0%",
    1: "🟦🟦⬜⬜⬜⬜ 16%",
    2: "🟦🟦🟦⬜⬜⬜ 33%",
    3: "🟦🟦🟦🟦⬜⬜ 50%",
    4: "🟦🟦🟦🟦🟦⬜ 66%",
    5: "🟦🟦🟦🟦🟦🟦 83%",
    6: "🟩🟩🟩🟩🟩🟩 100%"
}

# --- Helper Functions ---
def get_progress_bar(progress):
    return PROGRESS_BAR.get(progress, PROGRESS_BAR[0])

async def advance_flow(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    step = user_progress.get(chat_id, 0)
    task_index = step // 2
    is_screenshot_step = step % 2 != 0

    if task_index >= len(TASKS):
        user_progress[chat_id] = 99
        if chat_id not in daily_reminder_users:
            daily_reminder_users.add(chat_id)
            logger.info(f"User {chat_id} completed all tasks")

        final_message = (
            "🎊 *Congratulations!* 🎊\n\n"
            "You've completed all tasks and earned 100 $IFART tokens!\n\n"
            "🔓 You now have full access to the iFart Mini App!"
        )
        keyboard = [
            [InlineKeyboardButton("🚀 PLAY iFart Mini App", web_app=WebAppInfo(url=MINI_APP_URL))],
            [InlineKeyboardButton("📊 View Earnings", callback_data="view_earnings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=chat_id, 
            text=final_message, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return

    if is_screenshot_step:
        task = TASKS[task_index]
        screenshot_request_text = (
            f"📸 *Step {task_index+1} Verification*\n\n"
            f"Please send a screenshot showing you completed:\n"
            f"*{task['button_text']}* {task['emoji']}\n\n"
            "🔒 All submissions are verified before token distribution"
        )
        await context.bot.send_message(
            chat_id=chat_id, 
            text=screenshot_request_text, 
            parse_mode='Markdown'
        )
    else:
        task = TASKS[task_index]
        progress = task_index
        progress_bar = get_progress_bar(progress)
        
        message = (
            f"{progress_bar}\n\n"
            f"{task['intro']}\n\n"
            f"💎 *Reward:* {15 + task_index*2} $IFART\n"
            f"⏱️ *Estimated time:* {1 + task_index} minute\n\n"
            "Click the button below to complete this task:"
        )
        
        buttons = [
            [InlineKeyboardButton(f"{task['button_text']} {task['emoji']}", url=task["url"])],
            [InlineKeyboardButton("✅ I've Completed This", callback_data="request_proof")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await context.bot.send_message(
            chat_id=chat_id, 
            text=message, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = user.id
    logger.info(f"User {user.first_name} started the bot.")
    
    # Send welcome message with modern UI
    await context.bot.send_message(
        chat_id=chat_id,
        text=WELCOME_MESSAGE,
        parse_mode='Markdown'
    )
    
    # Send initial task after a short delay
    user_progress[chat_id] = 0
    await asyncio.sleep(1.5)
    await advance_flow(context, chat_id)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "request_proof":
        try:
            await query.message.delete()
        except:
            logger.warning("Couldn't delete message")
        
        user_progress[user_id] += 1
        await advance_flow(context, user_id)
    elif query.data == "view_earnings":
        await query.edit_message_text(
            text="💰 *Your iFart Earnings*\n\n"
                 "▫️ Task Completion: 100 $IFART\n"
                 "▫️ Daily Mining: 0 $IFART\n"
                 "▫️ Referrals: 0 $IFART\n\n"
                 "Total Balance: 100 $IFART\n\n"
                 "Withdrawals available after 500 $IFART",
            parse_mode='Markdown'
        )

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    step = user_progress.get(user_id, -1)
    is_screenshot_step = step % 2 != 0

    if is_screenshot_step:
        task_index = step // 2
        reward = 15 + task_index*2
        
        # Create confirmation message
        confirmation = (
            f"✅ *Verification Received!*\n\n"
            f"Thank you for completing Step {task_index+1}!\n"
            f"🎁 You earned: *{reward} $IFART*\n\n"
            f"Your total earnings: *{100 if task_index == 5 else (task_index+1)*17} $IFART*"
        )
        
        # Add animation effect
        for i in range(3):
            await update.message.reply_text("⏳ Verifying" + "." * (i+1))
            await asyncio.sleep(0.5)
        
        await context.bot.send_message(
            chat_id=user_id,
            text=confirmation,
            parse_mode='Markdown'
        )
        
        # Move to next task
        user_progress[user_id] += 1
        await asyncio.sleep(1.5)
        await advance_flow(context, user_id)
    else:
        await update.message.reply_text(
            "⚠️ Please complete your current task first before sending screenshots",
            parse_mode='Markdown'
        )

# --- Daily Reminder ---
async def send_daily_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Sending daily reminders to {len(daily_reminder_users)} users")
    
    reminder_message = (
        "⏰ *Daily Reminder!*\n\n"
        "Your iFart tokens are waiting! Don't forget to mine today:\n\n"
        "▫️ Daily mining bonus: 10 $IFART\n"
        "▫️ Streak bonus: 5 $IFART\n\n"
        "Tap below to start mining now! 👇"
    )
    
    keyboard = [
        [InlineKeyboardButton("⛏️ Mine Now", web_app=WebAppInfo(url=MINI_APP_URL))],
        [InlineKeyboardButton("📊 View Portfolio", callback_data="view_earnings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for chat_id in daily_reminder_users.copy():
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=reminder_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send to {chat_id}: {e}")
            if "blocked" in str(e).lower():
                daily_reminder_users.discard(chat_id)

# --- Main Bot Logic ---
def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # Setup daily reminder
    job_queue = application.job_queue
    if job_queue:
        reminder_time = datetime.time(hour=9, minute=0, second=0, tzinfo=datetime.timezone.utc)
        job_queue.run_daily(send_daily_reminder, time=reminder_time)
        logger.info(f"Daily reminders scheduled for {reminder_time} UTC")

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))

    # Modern start command
    application.add_handler(CommandHandler("menu", start))

    logger.info("🚀 iFart Bot is running with modern UI...")
    application.run_polling()

if __name__ == "__main__":
    import asyncio
    main()

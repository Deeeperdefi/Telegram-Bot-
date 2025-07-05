import logging
import datetime
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ChatMemberStatus

# --- Configuration ---
# This code now correctly reads the variables from Render's Environment tab.
BOT_TOKEN = os.environ.get("BOT_TOKEN")
TELEGRAM_GROUP_ID = os.environ.get("TELEGRAM_GROUP_ID") 

# --- IMPORTANT: Make sure you have updated these URLs with your real links ---
YOUTUBE_URL = "https://youtube.com/your_channel"
X_URL = "https://x.com/your_profile"
FACEBOOK_URL = "https://facebook.com/your_page"
TELEGRAM_GROUP_URL = "https://t.me/your_group_invite_link" # Make sure this is your group's invite link
MINI_APP_URL = "https://your-ifart-mini-app.com"

# --- Bot Data Storage (for demonstration) ---
user_progress = {}
daily_reminder_users = set()

# --- Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Task Definitions ---
TASKS = [
    {
        "name": "telegram",
        "intro": "1️⃣ First, you must join our official Telegram Group. Click the button below to join, then come back and click 'Verify'.",
        "button_text": "Join Group",
        "url": TELEGRAM_GROUP_URL,
        "verify": True
    },
    {
        "name": "youtube",
        "intro": "2️⃣ Great! Now, please subscribe to our YouTube Channel. Click the button below, subscribe, and then return here.",
        "button_text": "Subscribe on YouTube 🎬",
        "url": YOUTUBE_URL,
        "verify": False
    },
    {
        "name": "twitter",
        "intro": "3️⃣ Almost there! Follow our X (Twitter) profile to stay up-to-date with the latest news.",
        "button_text": "Follow on X 🐦",
        "url": X_URL,
        "verify": False
    },
    {
        "name": "facebook",
        "intro": "4️⃣ Last one! Please like our Facebook page.",
        "button_text": "Like on Facebook 👍",
        "url": FACEBOOK_URL,
        "verify": False
    }
]

# --- Helper Function to Send Tasks ---
async def send_task_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, step: int):
    """Sends the message for the user's current task step."""
    if step < len(TASKS):
        task = TASKS[step]
        
        buttons = [
            [InlineKeyboardButton(task["button_text"], url=task["url"])]
        ]
        if task["verify"]:
            buttons.append([InlineKeyboardButton("✅ Verify Join", callback_data=f"verify_{task['name']}")])
        else:
            buttons.append([InlineKeyboardButton("➡️ Next Task", callback_data="next_task")])
        
        reply_markup = InlineKeyboardMarkup(buttons)
        await context.bot.send_message(chat_id=chat_id, text=task["intro"], reply_markup=reply_markup)
    else:
        user_progress[chat_id] = 99
        if chat_id not in daily_reminder_users:
            daily_reminder_users.add(chat_id)
            logger.info(f"User {chat_id} completed all tasks and was added to reminder list.")

        final_message = "🎉 Congratulations! You have completed all the tasks. You now have access to the iFart Mini App!"
        keyboard = [[InlineKeyboardButton("🚀 Play iFart Mini App!", web_app=WebAppInfo(url=MINI_APP_URL))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=chat_id, text=final_message, reply_markup=reply_markup)

# --- Command and Callback Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command, beginning the task sequence."""
    user = update.effective_user
    chat_id = user.id
    logger.info(f"User {user.first_name} ({chat_id}) started the bot.")
    
    user_progress[chat_id] = 0
    await send_task_message(context, chat_id, 0)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles all button presses (callbacks)."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    current_step = user_progress.get(user_id, -1)
    
    if current_step == -1:
        await query.edit_message_text("Something went wrong. Please type /start to begin again.")
        return

    if query.data == "verify_telegram":
        if current_step == 0:
            try:
                member = await context.bot.get_chat_member(chat_id=TELEGRAM_GROUP_ID, user_id=user_id)
                if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                    await query.edit_message_text("✅ Verification successful! Thank you for joining.")
                    user_progress[user_id] += 1
                    await send_task_message(context, user_id, user_progress[user_id])
                else:
                    await context.bot.answer_callback_query(query.id, "❌ Verification failed. You are not a member of the group. Please join and try again.", show_alert=True)
            except Exception as e:
                logger.error(f"Error verifying user {user_id} in group {TELEGRAM_GROUP_ID}: {e}")
                await context.bot.answer_callback_query(query.id, "An error occurred. Make sure the bot is an admin in the group and the Group ID is correct.", show_alert=True)
        return

    if query.data == "next_task":
        if not TASKS[current_step]["verify"]:
            await query.edit_message_text(f"Task {current_step + 1} acknowledged. Here is the next one:")
            user_progress[user_id] += 1
            await send_task_message(context, user_id, user_progress[user_id])
        else:
            await context.bot.answer_callback_query(query.id, "Please complete the current verification step.", show_alert=True)

# --- Daily Reminder Functionality ---
async def send_daily_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a reminder message to all users who have completed the tasks."""
    logger.info(f"Running daily reminder job. Sending to {len(daily_reminder_users)} users.")
    
    reminder_message = "⏰ Daily Reminder!\n\nHey, don't forget to mine today in the iFart app, or you might miss your earnings! 💨💰"
    keyboard = [[InlineKeyboardButton("Mine Now! 🚀", web_app=WebAppInfo(url=MINI_APP_URL))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for chat_id in daily_reminder_users:
        try:
            await context.bot.send_message(chat_id=chat_id, text=reminder_message, reply_markup=reply_markup)
            logger.info(f"Sent reminder to {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            if "bot was blocked" in str(e):
                daily_reminder_users.remove(chat_id)
                logger.info(f"Removed blocked user {chat_id} from reminders.")

# --- Main Bot Logic ---
def main() -> None:
    """Start the bot and set up the daily job."""
    # This is the new, correct check for the environment variables.
    if not BOT_TOKEN or not TELEGRAM_GROUP_ID:
        logger.error("FATAL: BOT_TOKEN or TELEGRAM_GROUP_ID environment variables not set.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    job_queue = application.job_queue
    reminder_time = datetime.time(hour=9, minute=0, second=0, tzinfo=datetime.timezone.utc)
    job_queue.run_daily(send_daily_reminder, time=reminder_time, name="daily_reminder_job")
    
    logger.info(f"Daily reminder job scheduled for {reminder_time} UTC.")

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
import logging
import datetime
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- Configuration ---
# Reads the variables from Render's Environment tab.
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# --- Your Links (Updated as per your request) ---
# Main social links
YOUTUBE_URL = "https://cutt.ly/GrYcicUY"
X_URL = "https://x.com/ifarttoken"
FACEBOOK_URL = "https://web.facebook.com/cryptoadvertiser11"
SPONSOR_URL = "https://www.profitableratecpm.com/h7636fr3k?key=e9c1b80bf6645940264046b0a5f6ce72"
MINI_APP_URL = "https://brilliant-toffee-0b87e0.netlify.app/"

# Telegram join links
TELEGRAM_GROUP_URL = "https://t.me/+h2YUHTxOo7ZlYWE8"
TELEGRAM_CHANNEL_URL = "https://t.me/ifarttoken"


# --- Bot Data Storage (for demonstration) ---
# user_progress maps user_id to their current step.
# Even numbers (0, 2, 4...) are for performing a task.
# Odd numbers (1, 3, 5...) are for submitting a screenshot for that task.
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
        "name": "group",
        "intro": "1️⃣ First, please join our official Telegram Group. Click the button below, then come back and click 'Done' to submit your proof.",
        "button_text": "Join Group 💬",
        "url": TELEGRAM_GROUP_URL,
    },
    {
        "name": "channel",
        "intro": "2️⃣ Excellent! Now, please join our official Telegram Channel. Click the button below, then come back and click 'Done'.",
        "button_text": "Join Channel 📢",
        "url": TELEGRAM_CHANNEL_URL,
    },
    {
        "name": "sponsor",
        "intro": "3️⃣ Please visit our sponsor's site. Stay on the site for at least 30 seconds, then come back and click 'Done'.",
        "button_text": "Visit our Sponsor ❤️",
        "url": SPONSOR_URL,
    },
    {
        "name": "youtube",
        "intro": "4️⃣ Next, please subscribe to our YouTube Channel. Click the button below, then come back and click 'Done'.",
        "button_text": "Subscribe on YouTube 🎬",
        "url": YOUTUBE_URL,
    },
    {
        "name": "twitter",
        "intro": "5️⃣ Almost there! Follow our X (Twitter) profile. Click the button below, then come back and click 'Done'.",
        "button_text": "Follow on X 🐦",
        "url": X_URL,
    },
    {
        "name": "facebook",
        "intro": "6️⃣ Last one! Please like our Facebook page. Click the button below, then come back and click 'Done'.",
        "button_text": "Like on Facebook �",
        "url": FACEBOOK_URL,
    }
]

# --- Helper Function to manage conversation flow ---
async def advance_flow(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Determines what message to send based on the user's progress."""
    step = user_progress.get(chat_id, 0)
    task_index = step // 2
    is_screenshot_step = step % 2 != 0

    if task_index >= len(TASKS):
        # User has finished all tasks and screenshots
        user_progress[chat_id] = 99
        if chat_id not in daily_reminder_users:
            daily_reminder_users.add(chat_id)
            logger.info(f"User {chat_id} completed all tasks and was added to reminder list.")

        final_message = "🎉 Congratulations! You have completed all the tasks. You now have access to the iFart Mini App!"
        keyboard = [[InlineKeyboardButton("🚀 PLAY iFart Mini App!", web_app=WebAppInfo(url=MINI_APP_URL))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=chat_id, text=final_message, reply_markup=reply_markup)
        return

    if is_screenshot_step:
        # Ask for a screenshot
        screenshot_request_text = (
            f"👍 Now, please send a screenshot as proof for **Task {task_index + 1}**.\n\n"
            "⚠️ *All submissions will be reviewed by our team before your airdrop withdrawal is processed. Honest participation is required.*"
        )
        await context.bot.send_message(chat_id=chat_id, text=screenshot_request_text, parse_mode='Markdown')
    else:
        # Send the next task
        task = TASKS[task_index]
        buttons = [
            [InlineKeyboardButton(task["button_text"], url=task["url"])],
            [InlineKeyboardButton("✅ Done, Ready to Send Proof", callback_data="request_proof")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await context.bot.send_message(chat_id=chat_id, text=task["intro"], reply_markup=reply_markup)


# --- Command and Callback Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command, beginning the task sequence."""
    user = update.effective_user
    chat_id = user.id
    logger.info(f"User {user.first_name} ({chat_id}) started the bot.")
    
    user_progress[chat_id] = 0
    await advance_flow(context, chat_id)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the press of the 'Done' button."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "request_proof":
        # Delete the old message with the buttons
        await query.message.delete()
        # Move user to the screenshot submission stage for the current task
        user_progress[user_id] += 1
        await advance_flow(context, user_id)

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles when a user sends a photo."""
    user_id = update.effective_user.id
    step = user_progress.get(user_id, -1)
    is_screenshot_step = step % 2 != 0

    if is_screenshot_step:
        # Send the warning/confirmation message
        await update.message.reply_text(
            "✅ Thank you! Your proof has been received and will be reviewed by our team. Here is the next task."
        )
        # Move user to the next task
        user_progress[user_id] += 1
        await advance_flow(context, user_id)
    else:
        # Ignore photos sent at the wrong time
        logger.info(f"User {user_id} sent a photo, but it was not expected.")


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
    if not BOT_TOKEN:
        logger.error("FATAL: BOT_TOKEN environment variable is not set.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    job_queue = application.job_queue
    if job_queue:
        reminder_time = datetime.time(hour=9, minute=0, second=0, tzinfo=datetime.timezone.utc)
        job_queue.run_daily(send_daily_reminder, time=reminder_time, name="daily_reminder_job")
        logger.info(f"Daily reminder job scheduled for {reminder_time} UTC.")

    # Register all the handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    # Add the new handler for photos
    application.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
�

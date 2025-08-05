# -*- coding: utf-8 -*-
import logging
import datetime
import os
import asyncio
import random
import string
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import firebase_admin
from firebase_admin import credentials, firestore

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
APP_ID = 'ifart-miner-dev' # Make sure this matches the appId in your web app

# --- Firebase Admin SDK setup ---
try:
    # Best practice for Render/Heroku: Use environment variables
    firebase_creds_json = os.environ.get("FIREBASE_CREDS_JSON")
    if not firebase_creds_json:
        # Fallback for local development: check for a service account file
        if os.path.exists('firebase-service-account.json'):
            with open('firebase-service-account.json') as f:
                firebase_creds_json = f.read()
        else:
            raise ValueError("Firebase credentials not found in FIREBASE_CREDS_JSON env var or firebase-service-account.json file.")

    firebase_creds_dict = json.loads(firebase_creds_json)
    cred = credentials.Certificate(firebase_creds_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logging.info("Firebase Admin SDK initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Firebase Admin SDK: {e}")
    db = None


# --- Updated Links with Emojis ---
YOUTUBE_URL = "https://cutt.ly/GrYcicUY"
X_URL = "https://x.com/ifarttoken"
FACEBOOK_URL = "https://web.facebook.com/cryptoadvertiser11"
TELEGRAM_CHANNEL_URL = "https://t.me/ifarttoken"

# --- [MODIFIED] Mini App URLs for iOS and Android ---
IOS_MINI_APP_URL = "https://ifartminiappios.xyz/"
ANDROID_MINI_APP_URL = "https://ifarttokenminiapp.xyz/"

# --- Bot Data Storage ---
user_progress = {}
daily_reminder_users = {} # Store chat_id and selected device

# --- Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- [MODIFIED] Modern Task Definitions (4 Tasks) ---
TASKS = [
    {
        "name": "channel",
        "intro": "🚀 *Step 1/4: Stay Updated*\n\nSubscribe to our official Telegram channel for important announcements!",
        "button_text": "📢 Join Channel",
        "url": TELEGRAM_CHANNEL_URL,
        "emoji": "📢"
    },
    {
        "name": "youtube",
        "intro": "🎬 *Step 2/4: Subscribe on YouTube*\n\nWatch our latest videos to maximize your iFart experience!",
        "button_text": "🎥 Subscribe",
        "url": YOUTUBE_URL,
        "emoji": "📺"
    },
    {
        "name": "twitter",
        "intro": "🐦 *Step 3/4: Follow on X*\n\nStay updated with our latest tweets and crypto insights!",
        "button_text": "📱 Follow Us",
        "url": X_URL,
        "emoji": "🐦"
    },
    {
        "name": "facebook",
        "intro": "👍 *Step 4/4: Like on Facebook*\n\nConnect with our growing community on Facebook!",
        "button_text": "👍 Like Page",
        "url": FACEBOOK_URL,
        "emoji": "👍"
    }
]

# --- [MODIFIED] Visual Elements ---
WELCOME_MESSAGE = """
🎉 *Welcome to iFart Token!* 🎉

Complete these 4 simple steps to unlock access to the exclusive iFart Mini App!

📊 *Your Progress:* 0/4 tasks completed
🔒 *App Status:* Locked

Let's get started with the first task!
"""

PROGRESS_BAR = {
    0: "🔒⬜⬜⬜ 0%",
    1: "🔓🔒⬜⬜ 25%",
    2: "🔓🔓🔒⬜ 50%",
    3: "🔓🔓🔓🔒 75%",
    4: "🔓🔓🔓🔓 100%"
}

# --- Helper Functions ---
def get_progress_bar(progress):
    return PROGRESS_BAR.get(progress, PROGRESS_BAR[0])

def generate_passcode():
    """Generates a random 5-character passcode: 2 letters, 1 number, 2 symbols."""
    letters = string.ascii_uppercase
    digits = string.digits
    symbols = '!@#$&*'
    
    part1 = ''.join(random.choice(letters) for _ in range(2))
    part2 = ''.join(random.choice(digits) for _ in range(1))
    part3 = ''.join(random.choice(symbols) for _ in range(2))
    
    passcode_list = list(part1 + part2 + part3)
    random.shuffle(passcode_list)
    
    return ''.join(passcode_list)

async def advance_flow(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user: object):
    step = user_progress.get(chat_id, 0)
    task_index = step // 2
    is_screenshot_step = step % 2 != 0

    if task_index >= len(TASKS):
        user_progress[chat_id] = 99 # Mark as completed
        
        # --- Firebase Account Creation Logic ---
        if not db:
            await context.bot.send_message(chat_id=chat_id, text="Error: Could not connect to the database. Please contact support.")
            return

        username = user.username.lower() if user.username else f"user{user.id}"
        user_doc_ref = db.collection('artifacts', APP_ID, 'users').document(username)
        
        try:
            user_doc = user_doc_ref.get()
            if user_doc.exists:
                passcode = user_doc.to_dict().get('passcode', 'NOT_FOUND')
                login_message = (
                    "✅ *Account Found!* ✅\n\n"
                    "You have already completed the tasks. Here are your login details:\n\n"
                    f"Username: `{username}`\n"
                    f"Passcode: `{passcode}`\n\n"
                    "Use these in the mini app to access your account."
                )
            else:
                passcode = generate_passcode()
                new_user_data = {
                    'passcode': passcode, 'totalTokens': 0,
                    'spinDetails': { 'dailyEarnings': 0, 'spinsLeft': 5, 'totalSpins': 0, 'totalWon': 0, 'lastSpinDate': None, 'spinAdCounter': 0 },
                    'lastRainPlayTime': None, 'rainFartsMissed': 0, 'rainEnabledByVideo': True,
                    'socialTasks': {}, 'referredBy': None, 'loginStreak': 0, 'lastLoginDate': None,
                    'referrerBonusAwarded': False, 'lastUpdated': firestore.SERVER_TIMESTAMP
                }
                user_doc_ref.set(new_user_data)
                login_message = (
                    "🎊 *Congratulations! Account Created!* 🎊\n\n"
                    "You've successfully completed all verification steps! Here are your *permanent* login details. **Save them!**\n\n"
                    f"Username: `{username}`\n"
                    f"Passcode: `{passcode}`\n\n"
                    "Use these to log into the iFart Mini App."
                )
            
            await context.bot.send_message(chat_id=chat_id, text=login_message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Firestore error for user {username}: {e}")
            await context.bot.send_message(chat_id=chat_id, text="A server error occurred while creating your account. Please try again later.")
            return

        # --- [NEW] Device Selection Step ---
        device_selection_message = "📱 *Almost there!* Select your device to get the correct version of the iFart Mini App."
        keyboard = [
            [
                InlineKeyboardButton("🍏 iOS", callback_data="select_ios"),
                InlineKeyboardButton("🤖 Android", callback_data="select_android")
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=chat_id,
            text=device_selection_message,
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
            "🔒 All submissions are verified before unlocking the app"
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
            f"⏱️ *Estimated time:* {1 + task_index} minute\n"
            f"🔑 *App Access:* {'Locked' if task_index < 3 else 'Almost there!'}\n\n"
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
    logger.info(f"User {user.first_name} ({user.username}) started the bot.")
    
    if not user.username:
        await update.message.reply_text("Please set a public Telegram @username in your profile settings to use this bot.")
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=WELCOME_MESSAGE,
        parse_mode='Markdown'
    )
    
    user_progress[chat_id] = 0
    await asyncio.sleep(1.5)
    await advance_flow(context, chat_id, user)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    if query.data == "request_proof":
        try:
            await query.message.delete()
        except Exception:
            logger.warning(f"Couldn't delete message for user {user.id}")
        
        user_progress[user.id] = user_progress.get(user.id, 0) + 1
        await advance_flow(context, user.id, user)

# --- [NEW] Device Selection Handler ---
async def device_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    chat_id = query.from_user.id
    selection = query.data
    
    if selection == "select_ios":
        app_url = IOS_MINI_APP_URL
        device_name = "iOS"
        daily_reminder_users[chat_id] = "ios" # Store preference
    else: # select_android
        app_url = ANDROID_MINI_APP_URL
        device_name = "Android"
        daily_reminder_users[chat_id] = "android" # Store preference

    final_message = f"🔓 The iFart Mini App ({device_name}) is now unlocked for you!"
    keyboard = [
        [InlineKeyboardButton(f"🚀 PLAY on {device_name}", web_app=WebAppInfo(url=app_url))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=final_message, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    logger.info(f"User {chat_id} selected {device_name} and received the app link.")


async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    step = user_progress.get(user.id, -1)
    is_screenshot_step = step % 2 != 0

    if is_screenshot_step:
        task_index = step // 2
        
        confirmation = (
            f"✅ *Verification Received!*\n\n"
            f"Step {task_index+1} completed successfully!\n\n"
            f"{len(TASKS) - (task_index+1)} steps remaining to unlock the app"
        )
        
        for i in range(3):
            await update.message.reply_text("🔍 Verifying" + "." * (i+1))
            await asyncio.sleep(0.5)
        
        await context.bot.send_message(
            chat_id=user.id,
            text=confirmation,
            parse_mode='Markdown'
        )
        
        user_progress[user.id] += 1
        await asyncio.sleep(1.5)
        await advance_flow(context, user.id, user)
    else:
        await update.message.reply_text(
            "⚠️ Please complete your current task first before sending screenshots",
            parse_mode='Markdown'
        )

# --- [MODIFIED] Daily Reminder ---
async def send_daily_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Sending daily reminders to {len(daily_reminder_users)} users")
    
    reminder_message = (
        "⏰ *Daily Reminder!*\n\n"
        "The iFart Mini App is waiting for you! Don't forget to play today 👇"
    )
    
    for chat_id, device in daily_reminder_users.copy().items():
        app_url = IOS_MINI_APP_URL if device == "ios" else ANDROID_MINI_APP_URL
        keyboard = [
            [InlineKeyboardButton("🚀 Play Now", web_app=WebAppInfo(url=app_url))],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
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
                del daily_reminder_users[chat_id]

# --- Main Bot Logic ---
def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    if not db:
        logger.error("Firestore database not initialized. Bot cannot start.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    job_queue = application.job_queue
    if job_queue:
        reminder_time = datetime.time(hour=9, minute=0, second=0, tzinfo=datetime.timezone.utc)
        job_queue.run_daily(send_daily_reminder, time=reminder_time)
        logger.info(f"Daily reminders scheduled for {reminder_time} UTC")

    # --- [MODIFIED] Handlers with specific patterns ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^request_proof$"))
    application.add_handler(CallbackQueryHandler(device_selection_handler, pattern="^select_(ios|android)$"))
    application.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    application.add_handler(CommandHandler("menu", start))

    logger.info("🚀 iFart Bot is running with updated tasks and device selection...")
    application.run_polling()

if __name__ == "__main__":
    main()

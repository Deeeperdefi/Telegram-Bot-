# -*- coding: utf-8 -*-
import logging
import datetime
import os
import asyncio
import random
import string
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import firebase_admin
from firebase_admin import credentials, firestore

# --- Configuration ---
# It's recommended to set your BOT_TOKEN as an environment variable for security.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
# The APP_ID should match the one in your web app for Firestore security rules.
APP_ID = 'ifart-miner-dev'
# Your bot's username, without the '@'
BOT_USERNAME = os.environ.get("BOT_USERNAME", "YourBotUsername")

# --- Firebase Admin SDK setup ---
# This setup is crucial for persisting user data.
try:
    # For deployment on platforms like Render or Heroku, use environment variables.
    firebase_creds_json = os.environ.get("FIREBASE_CREDS_JSON")
    if not firebase_creds_json:
        # Fallback for local development: check for a service account file.
        if os.path.exists('firebase-service-account.json'):
            with open('firebase-service-account.json') as f:
                firebase_creds_json = f.read()
            logging.info("Loaded Firebase credentials from firebase-service-account.json file.")
        else:
            raise ValueError("Firebase credentials not found. Set the FIREBASE_CREDS_JSON environment variable or create firebase-service-account.json.")

    firebase_creds_dict = json.loads(firebase_creds_json)
    cred = credentials.Certificate(firebase_creds_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logging.info("Firebase Admin SDK initialized successfully.")
except Exception as e:
    logging.error(f"FATAL: Failed to initialize Firebase Admin SDK: {e}")
    db = None # The bot cannot run without a database connection.


# --- Bot Content & Links ---
YOUTUBE_URL = "https://cutt.ly/GrYcicUY"
X_URL = "https://x.com/ifarttoken"
FACEBOOK_URL = "https://web.facebook.com/cryptoadvertiser11"
SPONSOR_URL = "https://www.profitableratecpm.com/h7636fr3k?key=e9c1b80bf6645940264046b0a5f6ce72"
MINI_APP_URL = "https://ifarttokenminiapp.xyz/"
TELEGRAM_GROUP_URL = "https://t.me/+h2YUHTxOo7ZlYWE8"
TELEGRAM_CHANNEL_URL = "https://t.me/ifarttoken"

WELCOME_MESSAGE = (
    "🎉 *Welcome to the iFart Token Airdrop Bot!* 🎉\n\n"
    "Get ready to complete simple tasks to earn iFart tokens. "
    "You can also earn more by inviting your friends!\n\n"
    "Use the menu below to navigate."
)

# --- Task Definitions (Corrected and Completed) ---
TASKS = [
    {
        "name": "group",
        "intro": "🌟 *Step 1/6: Join Our Community*\n\nJoin our exclusive Telegram group to connect with other iFart enthusiasts!",
        "button_text": "✨ Join Group & Verify",
        "url": TELEGRAM_GROUP_URL,
        "reward": 10,
    },
    {
        "name": "channel",
        "intro": "🚀 *Step 2/6: Stay Updated*\n\nSubscribe to our official Telegram channel for important announcements!",
        "button_text": "📢 Join Channel & Verify",
        "url": TELEGRAM_CHANNEL_URL,
        "reward": 10,
    },
    {
        "name": "sponsor",
        "intro": "💎 *Step 3/6: Support Our Sponsor*\n\nVisit our sponsor's website to help keep iFart running!",
        "button_text": "❤️ Visit Sponsor & Verify",
        "url": SPONSOR_URL,
        "reward": 20,
    },
    {
        "name": "youtube",
        "intro": "🎬 *Step 4/6: Subscribe on YouTube*\n\nWatch our latest videos to maximize your iFart experience!",
        "button_text": "🎥 Subscribe & Verify",
        "url": YOUTUBE_URL,
        "reward": 15,
    },
    {
        "name": "twitter",
        "intro": "🐦 *Step 5/6: Follow on X*\n\nFollow our official X (Twitter) account for real-time updates and news!",
        "button_text": "👣 Follow on X & Verify",
        "url": X_URL,
        "reward": 15,
    },
    {
        "name": "facebook",
        "intro": "👍 *Step 6/6: Like our Facebook Page*\n\nLike our Facebook page to complete the tasks and show your support!",
        "button_text": "👍 Like Page & Verify",
        "url": FACEBOOK_URL,
        "reward": 15,
    }
]

# --- Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Firestore Helper Functions ---
async def get_or_create_user(user_id: int, username: str, first_name: str) -> dict:
    """
    Gets user data from Firestore, or creates a new user document if one doesn't exist.
    This is key to making user data persistent.
    """
    if not db:
        logging.error("Firestore client not available. Cannot get or create user.")
        return None
    
    user_ref = db.collection(APP_ID).document('users').collection('user_data').document(str(user_id))
    doc = await asyncio.to_thread(user_ref.get)

    if doc.exists:
        return doc.to_dict()
    else:
        user_data = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'completed_tasks': [],
            'balance': 0.0,
            'referral_code': ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
            'referred_by': None,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        await asyncio.to_thread(user_ref.set, user_data)
        logging.info(f"Created new user profile for user_id: {user_id}")
        return user_data

# --- Core Bot Logic ---
async def send_next_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Identifies the next incomplete task and sends it to the user."""
    user = update.effective_user
    user_data = await get_or_create_user(user.id, user.username, user.first_name)
    if not user_data:
        await context.bot.send_message(chat_id=user.id, text="Sorry, there was a problem accessing your data. Please try again later.")
        return

    completed_tasks = user_data.get('completed_tasks', [])
    next_task = None
    for task in TASKS:
        if task['name'] not in completed_tasks:
            next_task = task
            break

    message_text = ""
    keyboard = None

    if next_task:
        message_text = next_task['intro']
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(text=next_task['button_text'], url=next_task['url'])],
            [InlineKeyboardButton(text="✅ I've Done It!", callback_data=f"complete_task_{next_task['name']}")],
            [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="main_menu")]
        ])
    else:
        message_text = "🎉 *Congratulations!* 🎉\n\nYou have completed all the airdrop tasks. You are a true iFart champion!\n\nKeep an eye on our channel for more ways to earn."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="main_menu")]])

    # Determine how to send the message (edit existing or send new)
    if update.callback_query:
        await update.callback_query.edit_message_text(text=message_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text=message_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command. Welcomes the user and shows the main menu."""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot.")
    
    if not db:
        await update.message.reply_text("Sorry, the bot is currently under maintenance. Please try again later.")
        return

    await get_or_create_user(user.id, user.username, user.first_name)
    
    # --- Referral Logic ---
    if len(context.args) > 0:
        referrer_id = context.args[0]
        if referrer_id.isdigit() and int(referrer_id) != user.id:
            user_ref = db.collection(APP_ID).document('users').collection('user_data').document(str(user.id))
            user_doc = await asyncio.to_thread(user_ref.get)
            if user_doc.exists and user_doc.to_dict().get('referred_by') is None:
                # Set referred_by for the new user
                await asyncio.to_thread(user_ref.update, {'referred_by': int(referrer_id)})
                
                # Reward the referrer
                referrer_ref = db.collection(APP_ID).document('users').collection('user_data').document(referrer_id)
                await asyncio.to_thread(referrer_ref.update, {'balance': firestore.Increment(50)}) # 50 token referral bonus
                logger.info(f"User {user.id} was referred by {referrer_id}. Referrer credited.")
                
                try:
                    await context.bot.send_message(
                        chat_id=int(referrer_id),
                        text=f"🎉 Congratulations! Your friend {user.first_name} joined using your link. You've earned 50 iFart tokens!"
                    )
                except Exception as e:
                    logger.warning(f"Could not notify referrer {referrer_id}: {e}")


    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 View Tasks", callback_data="view_tasks")],
        [InlineKeyboardButton("💰 My Wallet", callback_data="my_wallet")],
        [InlineKeyboardButton("🤝 Referral Program", callback_data="referral_program")],
        [InlineKeyboardButton("🚀 Open iFart Miner", web_app=WebAppInfo(url=MINI_APP_URL))],
    ])
    
    await update.message.reply_text(WELCOME_MESSAGE, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the main menu."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 View Tasks", callback_data="view_tasks")],
        [InlineKeyboardButton("💰 My Wallet", callback_data="my_wallet")],
        [InlineKeyboardButton("🤝 Referral Program", callback_data="referral_program")],
        [InlineKeyboardButton("🚀 Open iFart Miner", web_app=WebAppInfo(url=MINI_APP_URL))],
    ])
    
    menu_text = "👋 *Main Menu*\n\nWhat would you like to do?"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=menu_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text=menu_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


# --- Callback Query Handler ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles all button clicks from inline keyboards."""
    query = update.callback_query
    await query.answer() # Acknowledge the button press
    
    user = query.from_user
    
    if query.data == "main_menu":
        await show_menu(update, context)

    elif query.data == "view_tasks":
        await send_next_task(update, context)

    elif query.data.startswith("complete_task_"):
        task_name = query.data.split("_", 2)[2]
        
        task_info = next((task for task in TASKS if task["name"] == task_name), None)
        if not task_info:
            return

        user_ref = db.collection(APP_ID).document('users').collection('user_data').document(str(user.id))
        
        # Add task to completed list and increment balance
        await asyncio.to_thread(user_ref.update, {
            'completed_tasks': firestore.ArrayUnion([task_name]),
            'balance': firestore.Increment(task_info['reward'])
        })
        
        await query.edit_message_text(f"✅ Task '{task_name}' completed! You've earned {task_info['reward']} iFart tokens.")
        
        # Send the next task after a short delay
        await asyncio.sleep(1.5)
        await send_next_task(update, context)

    elif query.data == "my_wallet":
        user_data = await get_or_create_user(user.id, user.username, user.first_name)
        balance = user_data.get('balance', 0.0)
        wallet_text = (
            f"💰 *My Wallet*\n\n"
            f"Your current balance is: *{balance:.2f} iFart Tokens*.\n\n"
            "Keep completing tasks and referring friends to earn more!"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Open iFart Miner", web_app=WebAppInfo(url=MINI_APP_URL))],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]
        ])
        await query.edit_message_text(text=wallet_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    elif query.data == "referral_program":
        referral_link = f"https://t.me/{BOT_USERNAME}?start={user.id}"
        referral_text = (
            f"🤝 *Referral Program*\n\n"
            f"Invite your friends and earn *50 iFart tokens* for every friend who joins and starts the bot using your unique link!\n\n"
            f"Your referral link is:\n`{referral_link}`\n\n"
            "Share it everywhere!"
        )
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]])
        await query.edit_message_text(text=referral_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


def main() -> None:
    """Start the bot."""
    if not BOT_TOKEN or "YOUR_BOT_TOKEN_HERE" in BOT_TOKEN:
        logging.error("FATAL: BOT_TOKEN is not configured. Please set it as an environment variable.")
        return
        
    if not BOT_USERNAME or "YourBotUsername" in BOT_USERNAME:
        logging.error("FATAL: BOT_USERNAME is not configured. Please set it as an environment variable.")
        return

    if not db:
        logging.error("FATAL: Firestore database is not initialized. Bot cannot start.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", show_menu))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Run the bot until the user presses Ctrl-C
    logging.info("Bot is starting...")
    application.run_polling()
    logging.info("Bot has stopped.")

if __name__ == "__main__":
    main()

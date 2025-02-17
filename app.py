import os
import asyncio
import pickle
from datetime import datetime
from collections import deque
from telegram import (
    Update,
    InlineKeyboardButton,
    BotCommand,
    BotCommandScopeChat,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    CallbackContext,
    filters,
)
from dotenv import load_dotenv

# Add to top of app.py
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)



# Try to import bad words list; otherwise use an empty list.
try:
    from bad_words import inappropriate_words
except ImportError:
    inappropriate_words = []

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))
INACTIVITY_TIMEOUT = 604800  # 7 days in seconds
DONATION_LINK = os.getenv("DONATION_LINK", "https://example.com/donate")

# Data persistence file
DATA_FILE = "bot_data.pkl"

def load_data():
    try:
        with open(DATA_FILE, "rb") as f:
            data = pickle.load(f)
            return (
                data.get("blocked_users", set()),
                data.get("user_settings", {}),
                data.get("all_users", set()),
                data.get("user_reports", {}),
            )
    except (FileNotFoundError, EOFError):
        return set(), {}, set(), {}

def save_data():
    data = {
        "blocked_users": blocked_users,
        "user_settings": user_settings,
        "all_users": all_users,
        "user_reports": user_reports,
    }
    with open(DATA_FILE, "wb") as f:
        pickle.dump(data, f)

# Load persistent data
blocked_users, user_settings, all_users, user_reports = load_data()

# Global dictionaries and queues
waiting_users = deque()
active_chats = {}
chat_start_times = {}  # NEW: store connection time for each user in a chat
warning_counts = {}
user_inactivity = {}

# Utility function to update user activity
def update_activity(user_id):
    user_inactivity[user_id] = datetime.now()

# ========================
# Command Handlers
# ========================

async def start(update: Update, context: CallbackContext):
    if not update.message:
        return
    user_id = update.message.chat_id
    all_users.add(user_id)
    save_data()
    update_activity(user_id)
    await find(update, context)

async def help_command(update: Update, context: CallbackContext):
    if not update.message:
        return
    user_id = update.message.chat_id
    update_activity(user_id)
    help_text = (
        "*This bot is for anonymous chatting with strangers in Telegram*\n\n"
        "_Bot can send text, links, GIFs, stickers, photos, videos or voice messages_\n\n"
        "📖 *Available commands:*\n"
        "/find - Start a new chat\n"
        "/stop - End current chat\n"
        "/report - Report a user\n"
        "/settings - Configure preferences\n"
        "/donate - Support our work\n"
        "/help - Show help information\n\n"
        "If you have any questions, do not hesitate to get in touch @support_bot"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def id_command(update: Update, context: CallbackContext):
    if not update.message:
        return
    user_id = update.message.chat_id
    update_activity(user_id)
    await update.message.reply_text(f"Your unique ID: {user_id}", parse_mode="Markdown")

async def settings(update: Update, context: CallbackContext):
    if not update.message:
        return
    user_id = update.message.chat_id
    update_activity(user_id)
    keyboard = [
        [InlineKeyboardButton("🌐 Language", callback_data="set_lang")],
        [InlineKeyboardButton("🔒 Privacy", callback_data="set_privacy")],
        [InlineKeyboardButton("🚫 Blocked Users", callback_data="blocked_list")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚙️ User Settings:", reply_markup=reply_markup)

async def donate(update: Update, context: CallbackContext):
    if not update.message:
        return
    user_id = update.message.chat_id
    update_activity(user_id)
    await update.message.reply_text(
        f"Support our work and help keep the bot running!\n\n"
        f"Donation link: {DONATION_LINK}\n"
        "Thank you for your generosity! 💖"
    )

async def find(update: Update, context: CallbackContext):
    if not update.message:
        return
    user_id = update.message.chat_id
    update_activity(user_id)

    if user_id in blocked_users:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Contact Admin", url=f"tg://user?id=7849886561")]
        ])
        await update.message.reply_text(
            "_🚫 You are blocked and cannot send messages._\n\n_If you believe this is a mistake, contact the admin._", 
            reply_markup=keyboard
        )
        return

    if user_id in active_chats:
        await update.message.reply_text("You're already in a chat!\nUse /stop to leave your current chat.")
        return

    if waiting_users:
        partner_id = waiting_users.popleft()
        # In case the user accidentally picked themselves, put back and wait.
        if partner_id == user_id:
            waiting_users.appendleft(partner_id)
            await update.message.reply_text("⏳ Looking for a partner...")
            return

        # Establish active chat between the two users.
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        # Record connection time for both users.
        now = datetime.now()
        chat_start_times[user_id] = now
        chat_start_times[partner_id] = now

        msg = (
            "Partner found 😺\n\n"
            "/next — find a new partner\n"
            "/stop — stop this chat\n\n"
            "[https://t.me/KuuChatBot](https://t.me/KuuChatBot)"
        )
        await context.bot.send_message(user_id, msg, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        await context.bot.send_message(partner_id, msg, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    else:
        if user_id not in waiting_users:
            waiting_users.append(user_id)
            await update.message.reply_text("⏳ Looking for a partner...")
        else:
            await update.message.reply_text("You're already in the waiting queue.")

async def link_command(update: Update, context: CallbackContext):
    if not update.message:
        return
    user_id = update.message.chat_id
    update_activity(user_id)
    
    if user_id not in active_chats:
        await update.message.reply_text("You're not in a chat. Use /find to start one.")
        return

    # Check if connection time exists and at least 60 seconds have passed.
    connection_time = chat_start_times.get(user_id)
    if not connection_time or (datetime.now() - connection_time).total_seconds() < 60:
        seconds_left = 60 - (datetime.now() - connection_time).total_seconds()
        await update.message.reply_text(f"The /link command is unavailable within the first minute of chatting.\n\nPlease wait {int(seconds_left)} more seconds.")
        return

    partner_id = active_chats[user_id]
    user = await context.bot.get_chat(user_id)
    
    if not user.username:
        await update.message.reply_text("You do not have a username. Please create one first.")
        return
    
    user_username = user.username
    link_text = f"_Your partner's profile url:_ [Click me](https://t.me/{user_username})\n\n_Use /link to send your profile link to your partner._"
    await context.bot.send_message(partner_id, link_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    await update.message.reply_text("Your profile link has been sent to your partner.")

async def next_command(update: Update, context: CallbackContext):
    if not update.message:
        return
    user_id = update.message.chat_id
    update_activity(user_id)
    
    if user_id in waiting_users:
        await update.message.reply_text("You're already in the waiting queue.\n_Please wait for a partner._", parse_mode=ParseMode.MARKDOWN)
        return
    
    if user_id in active_chats:
        await stop(update, context)
    
    await find(update, context)

async def stop(update: Update, context: CallbackContext):
    if not update.message:
        return
    user_id = update.message.chat_id
    update_activity(user_id)
    
    if user_id in active_chats:
        partner_id = active_chats.get(user_id)
        if partner_id in active_chats:
            del active_chats[partner_id]
            if partner_id in chat_start_times:
                del chat_start_times[partner_id]
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("👍 Like", callback_data="like"),
                 InlineKeyboardButton("👎 Dislike", callback_data="dislike")]
            ])
            await context.bot.send_message(
                partner_id,
                "_Your partner has stopped the chat 😞\nType /find to find a new partner_\n\n[https://t.me/KuuChatBot](https://t.me/KuuChatBot)",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            await context.bot.send_message(
                partner_id, 
                "_If you wish, leave your feedback about your partner. It will help us find better partners for you in the future_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
        del active_chats[user_id]
        if user_id in chat_start_times:
            del chat_start_times[user_id]
        await update.message.reply_text(
            "_You stopped the chat 🙄_\nType /find to find a new partner\n\n[https://t.me/KuuChatBot](https://t.me/KuuChatBot)",
            parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text(
            "_✅ You have left the queue.\nType /find to find a new partner_\n\n[https://t.me/KuuChatBot](https://t.me/KuuChatBot)",
            parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            "_❌ You're not in a chat or queue.\nType /find to find a new partner_\n\n[https://t.me/KuuChatBot](https://t.me/KuuChatBot)",
            parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )

async def report_command(update: Update, context: CallbackContext):
    if not update.message:
        return
    user_id = update.message.chat_id
    update_activity(user_id)
    
    if user_id not in active_chats:
        await update.message.reply_text("You can only report users during an active chat.")
        return
    
    reason = " ".join(context.args) if context.args else "No reason provided"
    partner_id = active_chats[user_id]
    user_reports[partner_id] = reason
    save_data()
    
    await update.message.reply_text("✅ Your report has been submitted. Thank you for keeping our community safe!")
    await context.bot.send_message(
        partner_id,
        "⚠️ You have been reported by a chat partner. Please adhere to community guidelines."
    )

# ========================
# Admin Functionality
# ========================

async def admin_panel(update: Update, context: CallbackContext):
    if not update.message:
        return
    user_id = update.message.chat_id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ Unauthorized access!")
        return

    update_activity(user_id)
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🚫 Block User", callback_data="admin_block")],
        [InlineKeyboardButton("✅ Unblock User", callback_data="admin_unblock")],
        [InlineKeyboardButton("📜 View Reports", callback_data="admin_reports")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🛠️ Admin Panel:", reply_markup=reply_markup)

async def handle_admin_actions(update: Update, context: CallbackContext):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    user_id = query.from_user.id

    if user_id != ADMIN_USER_ID:
        return

    action = query.data
    if action == "admin_stats":
        stats_text = (
            f"📈 Bot Statistics\n\n"
            f"👥 Total Users: {len(all_users)}\n"
            f"💬 Active Chats: {len(active_chats) // 2}\n"
            f"🚫 Blocked Users: {len(blocked_users)}\n"
            f"⚠️ Pending Reports: {len(user_reports)}"
        )
        await query.edit_message_text(stats_text)
    elif action == "admin_broadcast":
        await query.edit_message_text("Enter broadcast message:")
        context.user_data["awaiting_broadcast"] = True
    elif action == "admin_block":
        await query.edit_message_text("Enter user ID to block:")
        context.user_data["awaiting_block"] = True
    elif action == "admin_unblock":
        await query.edit_message_text("Enter user ID to unblock:")
        context.user_data["awaiting_unblock"] = True
    elif action == "admin_reports":
        reports = "\n".join([f"{uid}: {reason}" for uid, reason in user_reports.items()])
        await query.edit_message_text(f"📜 User Reports:\n\n{reports or 'No pending reports'}")

async def handle_admin_input(update: Update, context: CallbackContext):
    if not update.message:
        return
    user_id = update.message.chat_id
    if user_id != ADMIN_USER_ID:
        return

    update_activity(user_id)

    if context.user_data.get("awaiting_broadcast"):
        text = update.message.text
        del context.user_data["awaiting_broadcast"]
        success, failures = 0, 0
        for uid in all_users:
            try:
                if text:
                    await context.bot.send_message(uid, f"📢 Admin Broadcast:\n\n{text}")
                elif update.message.photo:
                    await context.bot.send_photo(uid, update.message.photo[-1].file_id, caption=update.message.caption)
                elif update.message.video:
                    await context.bot.send_video(uid, update.message.video.file_id, caption=update.message.caption)
                elif update.message.document:
                    await context.bot.send_document(uid, update.message.document.file_id, caption=update.message.caption)
                elif update.message.animation:
                    await context.bot.send_animation(uid, update.message.animation.file_id, caption=update.message.caption)
                elif update.message.sticker:
                    await context.bot.send_sticker(uid, update.message.sticker.file_id)
                elif update.message.voice:
                    await context.bot.send_voice(uid, update.message.voice.file_id)
                elif update.message.video_note:
                    await context.bot.send_video_note(uid, update.message.video_note.file_id)
                success += 1
            except Exception:
                failures += 1
        await update.message.reply_text(f"📢 Broadcast completed: {success} successful, {failures} failed.")
        return

    if context.user_data.get("awaiting_block"):
        target = update.message.text.strip()
        try:
            target_id = int(target)
            blocked_users.add(target_id)
            save_data()
            await update.message.reply_text(f"User {target_id} has been blocked.")
        except ValueError:
            await update.message.reply_text("Invalid user ID.")
        del context.user_data["awaiting_block"]
        return

    if context.user_data.get("awaiting_unblock"):
        target = update.message.text.strip()
        try:
            target_id = int(target)
            if target_id in blocked_users:
                blocked_users.remove(target_id)
                save_data()
                await update.message.reply_text(f"User {target_id} has been unblocked.")
            else:
                await update.message.reply_text("User not found in blocked list.")
        except ValueError:
            await update.message.reply_text("Invalid user ID.")
        del context.user_data["awaiting_unblock"]
        return

async def full_command(update: Update, context: CallbackContext):
    if not update.message:
        return
    user_id = update.message.chat_id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ Unauthorized access!")
        return

    if not context.args:
        await update.message.reply_text("Please provide a user ID.")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return

    try:
        user = await context.bot.get_chat(target_id)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
        return

    user_details = (
        f"👤 User Details:\n\n"
        f"🆔 ID: {user.id}\n"
        f"👤 Username: @{user.username or 'N/A'}\n"
        f"📛 Name: {user.full_name}\n"
        f"📄 Bio: {getattr(user, 'bio', 'No bio')}\n"
        f"💬 In Chat: {'Yes' if target_id in active_chats else 'No'}"
    )
    await update.message.reply_text(user_details)
    if user.id in active_chats:
        await update.message.reply_text(f"Partner: {active_chats[user.id]}")
    else:
        await update.message.reply_text("No active chat.")

# ========================
# Message Handlers
# ========================

async def handle_message(update: Update, context: CallbackContext):
    if not update.message:
        return

    user_id = update.message.chat_id

    # Skip processing if the sender is the admin (unless in an awaiting admin state)
    if user_id == ADMIN_USER_ID:
        return

    update_activity(user_id)

    if user_id in blocked_users:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Contact Admin", url=f"tg://user?id=7849886561")]
        ])
        await update.message.reply_text(
            "🚫 You are blocked and cannot send messages. If you believe this is a mistake, contact the admin.",
            reply_markup=keyboard
        )
        return

    # Check for inappropriate content
    text = update.message.text.lower() if update.message.text else ""
    caption = update.message.caption.lower() if update.message.caption else ""
    if any(word in text or word in caption for word in inappropriate_words):
        warning_counts[user_id] = warning_counts.get(user_id, 0) + 1
        if warning_counts[user_id] >= 3:
            blocked_users.add(user_id)
            save_data()
            await cleanup_chat(user_id, context.bot)
            await update.message.reply_text("🚫 You have been blocked for inappropriate behavior.")
            return
        else:
            await update.message.reply_text("⚠️ Please avoid inappropriate content.")
            return  # Stop processing this message further

    # Forward the message to the active chat partner using copy_message
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        try:
            await context.bot.copy_message(
                chat_id=partner_id,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
        except Exception as e:
            await update.message.reply_text("⚠️ Your partner may have blocked the bot.")
            await stop(update, context)
    else:
        await update.message.reply_text("You're not in a chat. Use /find to start one.")

# ========================
# Inactivity and Cleanup
# ========================

async def handle_inactive_users(context: CallbackContext):
    now = datetime.now()
    for user_id, last_active in list(user_inactivity.items()):
        if (now - last_active).total_seconds() > INACTIVITY_TIMEOUT:
            await cleanup_chat(user_id, context.bot)
            await context.bot.send_message(user_id, "⏲️ Session expired due to inactivity")
            del user_inactivity[user_id]


            

async def cleanup_chat(user_id, bot):
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        if partner_id in active_chats:
            del active_chats[partner_id]
            if partner_id in chat_start_times:
                del chat_start_times[partner_id]
            await bot.send_message(partner_id, "⛔ Chat partner disconnected")
        del active_chats[user_id]
    if user_id in waiting_users:
        waiting_users.remove(user_id)
    if user_id in chat_start_times:
        del chat_start_times[user_id]

async def update_bot_menu(user_id, application):
    if user_id in waiting_users:
        commands = [("stop", "🛑 Stop Searching")]
    else:
        commands = [("find", "🚀 Find a Partner"), ("donate", "❤️ Donate & Support")]
    bot_commands = [BotCommand(cmd, desc) for cmd, desc in commands]
    await application.bot.set_my_commands(bot_commands, scope=BotCommandScopeChat(user_id))

# ========================
# Settings Callback Handler
# ========================

async def settings_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data
    if data == "set_lang":
        await query.edit_message_text("Language settings are not implemented yet.")
    elif data == "set_privacy":
        await query.edit_message_text("Privacy settings are not implemented yet.")
    elif data == "blocked_list":
        if blocked_users:
            blocked_list = "\n".join(str(uid) for uid in blocked_users)
        else:
            blocked_list = "No blocked users."
        await query.edit_message_text(f"Blocked Users:\n{blocked_list}")

# Add error handler function
async def error_handler(update: object, context: CallbackContext):
    """Handle errors in the telegram bot."""
    logger.error(msg="Exception occurred:", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred. The admin has been notified."
        )


# ========================
# Main Function
# ========================

def main():
    # Add at the beginning of main()
application.add_error_handler(error_handler)
    application = Application.builder().token(BOT_TOKEN).build()

    # Admin handlers (order matters)
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("full", full_command))
    application.add_handler(CallbackQueryHandler(handle_admin_actions, pattern=r"^admin_.*"))
    application.add_handler(MessageHandler(filters.ALL & filters.User(ADMIN_USER_ID), handle_admin_input))

    # User command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("find", find))
    application.add_handler(CommandHandler("link", link_command))
    application.add_handler(CommandHandler("next", next_command))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("donate", donate))

    # Message handler for regular (non-command) messages
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_feedback, pattern=r"^(like|dislike)$"))
    # Settings callback handler
    application.add_handler(CallbackQueryHandler(settings_callback, pattern=r"^(set_lang|set_privacy|blocked_list)$"))

    # Inactivity job: run every 5 minutes (300 seconds)
    # application.job_queue.run_repeating(handle_inactive_users, interval=300, first=10)

    try:
        application.run_polling()
    finally:
        save_data()

async def handle_feedback(update: Update, context: CallbackContext):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    if query.data == "like":
        await query.edit_message_text("👍 Thank you for your feedback!")
    elif query.data == "dislike":
        await query.edit_message_text("👎 Thank you for your feedback!")

if __name__ == "__main__":
    main()

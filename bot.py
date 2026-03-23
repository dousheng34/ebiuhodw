"""
SheerID Verification Telegram Bot
Automatically verifies students, military, teachers, and first responders via SheerID API.
"""
import asyncio
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

import config
import sheerid
import storage

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Conversation states
(
    CHOOSING_TYPE,      # User picks verification type
    COLLECTING_FIELDS,  # Bot collects fields one by one
    WAITING_FOR_DOC,    # Waiting for document upload
) = range(3)


# ─── /start ──────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = (
        f"👋 Hello, *{user.first_name}*!\n\n"
        "I'm *SheerPro Bot* — your automatic identity verification assistant powered by SheerID.\n\n"
        "I can verify you as:\n"
        "🎓 *Student* — unlock student discounts\n"
        "🪖 *Military* — military/veteran benefits\n"
        "👨‍🏫 *Teacher* — educator perks\n"
        "🚒 *First Responder* — first responder offers\n\n"
        "Use /verify to start verification.\n"
        "Use /status to check your verification status.\n"
        "Use /help for more info."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ─── /help ────────────────────────────────────────────────────────────────────
async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📖 *SheerPro Bot — Help*\n\n"
        "*Commands:*\n"
        "• /start — Welcome screen\n"
        "• /verify — Start a new verification\n"
        "• /status — Check your current verification status\n"
        "• /cancel — Cancel ongoing verification\n\n"
        "*How it works:*\n"
        "1. Choose your category (Student, Military, etc.)\n"
        "2. Enter your personal information step by step\n"
        "3. SheerID verifies your data instantly\n"
        "4. If needed, upload a supporting document\n"
        "5. Receive your verification result ✅\n\n"
        "*Privacy:* Your data is transmitted securely to SheerID and stored encrypted."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ─── /status ──────────────────────────────────────────────────────────────────
async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    record = await storage.get_verification(user_id)
    if not record:
        await update.message.reply_text(
            "❌ No verification found. Use /verify to start one.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Refresh from SheerID if we have a verification_id
    v_id = record.get("verification_id")
    if v_id:
        resp = await sheerid.get_verification_status(v_id)
        if "error" not in resp:
            new_status = sheerid.parse_result_step(resp)
            if new_status != record["status"]:
                await storage.update_status(user_id, new_status)
                record["status"] = new_status

    emoji = {"success": "✅", "pending_doc": "📋", "denied": "❌", "unknown": "❓"}.get(record["status"], "⏳")
    text = (
        f"*Your Verification Status*\n\n"
        f"Type: *{config.VERIFICATION_TYPES.get(record['verification_type'], record['verification_type'])}*\n"
        f"Status: {emoji} *{record['status'].upper()}*\n"
        f"Updated: {record.get('updated_at', 'N/A')[:19]}"
    )
    if record["status"] == "pending_doc":
        text += "\n\n📎 Please upload your supporting document by sending a photo or file."
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ─── /verify — Start conversation ─────────────────────────────────────────────
async def verify_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [
            InlineKeyboardButton("🎓 Student", callback_data="type:student"),
            InlineKeyboardButton("🪖 Military", callback_data="type:military"),
        ],
        [
            InlineKeyboardButton("👨‍🏫 Teacher", callback_data="type:teacher"),
            InlineKeyboardButton("🚒 First Responder", callback_data="type:first_responder"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔐 *Start Verification*\n\nChoose your category:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN,
    )
    return CHOOSING_TYPE


async def choose_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    v_type = query.data.split(":")[1]
    ctx.user_data["v_type"] = v_type
    ctx.user_data["fields"] = {}
    ctx.user_data["field_queue"] = list(config.REQUIRED_FIELDS[v_type])

    label = config.VERIFICATION_TYPES[v_type]
    await query.edit_message_text(
        f"✅ Category: *{label}*\n\nLet's collect your info step by step.\nType /cancel to stop at any time.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return await _ask_next_field(update, ctx)


async def _ask_next_field(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    queue = ctx.user_data.get("field_queue", [])
    if not queue:
        return await _submit_verification(update, ctx)

    next_field = queue[0]
    prompt = config.FIELD_PROMPTS.get(next_field, f"Enter *{next_field}*:")

    # Send to the right chat
    chat_id = (
        update.effective_chat.id
        if update.effective_chat
        else update.callback_query.message.chat_id
    )
    await ctx.bot.send_message(chat_id, prompt, parse_mode=ParseMode.MARKDOWN)
    return COLLECTING_FIELDS


async def collect_field(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    queue = ctx.user_data.get("field_queue", [])
    if not queue:
        return ConversationHandler.END

    current_field = queue[0]
    value = update.message.text.strip()

    # Basic validation
    if current_field == "birth_date":
        import re
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            await update.message.reply_text(
                "⚠️ Invalid date format. Please use *YYYY-MM-DD* (e.g. 1998-06-15):",
                parse_mode=ParseMode.MARKDOWN,
            )
            return COLLECTING_FIELDS

    ctx.user_data["fields"][current_field] = value
    ctx.user_data["field_queue"] = queue[1:]  # Remove collected field
    return await _ask_next_field(update, ctx)


async def _submit_verification(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    v_type = ctx.user_data["v_type"]
    user_data = ctx.user_data["fields"]
    user = update.effective_user

    await ctx.bot.send_message(chat_id, "⏳ Submitting your data to SheerID for verification...")

    resp = await sheerid.create_verification(v_type, user_data)
    result = sheerid.parse_result_step(resp)
    v_id = resp.get("verificationId", "")

    # Save to GitHub
    await storage.save_verification(
        telegram_user_id=user.id,
        username=user.username or user.first_name,
        verification_type=v_type,
        verification_id=v_id,
        status=result,
        user_data=user_data,
    )

    if result == "success":
        reward_url = resp.get("rewardCode", {}).get("codeValue", "")
        msg = (
            "✅ *Verification Successful!*\n\n"
            f"🎉 Congratulations! You've been verified as a *{config.VERIFICATION_TYPES[v_type]}*.\n"
        )
        if reward_url:
            msg += f"\n🎁 *Your promo code:* `{reward_url}`"
        await ctx.bot.send_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN)

    elif result == "pending_doc":
        await ctx.bot.send_message(
            chat_id,
            "📋 *Document Required*\n\n"
            "Instant verification was not successful. Please upload a supporting document:\n\n"
            "📎 Send a *photo* or *file* (PDF, JPEG, PNG) of:\n"
            "• School/Work ID card\n"
            "• Official letter or paystub\n"
            "• Enrollment confirmation / class schedule\n\n"
            "_Your document will be reviewed by SheerID within 1-2 business days._",
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAITING_FOR_DOC

    elif result == "denied":
        messages = resp.get("errorIds", [])
        err_text = ", ".join(messages) if messages else "Verification could not be completed."
        await ctx.bot.send_message(
            chat_id,
            f"❌ *Verification Denied*\n\n{err_text}\n\nYou can try again with /verify.",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await ctx.bot.send_message(
            chat_id,
            f"⚠️ *Unexpected result:* {result}\n\nPlease try again or contact support.",
            parse_mode=ParseMode.MARKDOWN,
        )

    ctx.user_data.clear()
    return ConversationHandler.END


async def receive_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    record = await storage.get_verification(user_id)
    if not record or not record.get("verification_id"):
        await update.message.reply_text("❌ No pending verification found.")
        return ConversationHandler.END

    await ctx.bot.send_message(chat_id, "⏳ Uploading your document to SheerID...")

    # Get file
    if update.message.document:
        tg_file = await update.message.document.get_file()
        filename = update.message.document.file_name or "document.pdf"
    else:
        tg_file = await update.message.photo[-1].get_file()
        filename = "photo.jpg"

    file_bytes = await tg_file.download_as_bytearray()
    resp = await sheerid.upload_document(record["verification_id"], bytes(file_bytes), filename)

    if "error" in resp:
        await ctx.bot.send_message(
            chat_id,
            f"⚠️ Upload failed: {resp['error']}\n\nPlease try again.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAITING_FOR_DOC

    await storage.update_status(user_id, "pending_review")
    await ctx.bot.send_message(
        chat_id,
        "✅ *Document uploaded successfully!*\n\n"
        "📬 SheerID will review your document within *1-2 business days*.\n"
        "Use /status to check your verification status.",
        parse_mode=ParseMode.MARKDOWN,
    )
    ctx.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.clear()
    await update.message.reply_text(
        "❌ Verification cancelled. Use /verify to start again.",
    )
    return ConversationHandler.END


# ─── Error handler ────────────────────────────────────────────────────────────
async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception:", exc_info=ctx.error)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set!")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Conversation handler for /verify flow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("verify", verify_start)],
        states={
            CHOOSING_TYPE: [CallbackQueryHandler(choose_type, pattern=r"^type:")],
            COLLECTING_FIELDS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, collect_field)
            ],
            WAITING_FOR_DOC: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, receive_document)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(conv_handler)
    app.add_error_handler(error_handler)

    # Set bot commands
    async def post_init(application: Application) -> None:
        await application.bot.set_my_commands([
            BotCommand("start", "Welcome screen"),
            BotCommand("verify", "Start verification"),
            BotCommand("status", "Check your status"),
            BotCommand("help", "Help & info"),
            BotCommand("cancel", "Cancel verification"),
        ])

    app.post_init = post_init

    logger.info("🤖 SheerPro Bot started. Polling for updates...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

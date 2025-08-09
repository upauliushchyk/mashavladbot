import os
import json
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import asyncio

ASK_NAME, ASK_DATE = range(2)
DATA_FILE = "events.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Как назовём событие?")
    return ASK_NAME

async def ask_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['event_name'] = update.message.text
    await update.message.reply_text("А когда оно? Введи в формате ГГГГ‑ММ‑ДД:")
    return ASK_DATE

async def save_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    text = update.message.text
    try:
        event_date = datetime.datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        await update.message.reply_text("Неправильный формат, попробуй YYYY-MM-DD")
        return ASK_DATE
    data = load_data()
    data[user_id] = {"event_name": context.user_data['event_name'], "event_date": text}
    save_data(data)
    await update.message.reply_text(f"✅ Событие «{context.user_data['event_name']}» назначено на {text}")
    return ConversationHandler.END

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    data = load_data()
    if user_id in data:
        del data[user_id]
        save_data(data)
        await update.message.reply_text("Напоминание остановлено.")
    else:
        await update.message.reply_text("У тебя нет активных событий.")
    return ConversationHandler.END

async def change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Хорошо, как назовём новое событие?")
    return ASK_NAME

async def daily_notifications(app):
    while True:
        today = datetime.date.today()
        for uid, info in load_data().items():
            d = datetime.datetime.strptime(info["event_date"], "%Y-%m-%d").date()
            diff = (d - today).days
            if diff > 0:
                msg = f"⏳ До «{info['event_name']}» осталось {diff} дн."
            elif diff == 0:
                msg = f"🎉 Сегодня «{info['event_name']}»! Поздравляю!"
            else:
                continue
            try:
                await app.bot.send_message(chat_id=int(uid), text=msg)
            except:
                pass
        await asyncio.sleep(86400)

async def main():
    token = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={ASK_NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_date)],
                ASK_DATE:[MessageHandler(filters.TEXT & ~filters.COMMAND, save_event)]},
        fallbacks=[CommandHandler("stop", stop)]
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("change", change))

    asyncio.create_task(daily_notifications(app))
    print("Bot is running...")
    await app.run_polling()

if __name__=="__main__":
    import asyncio
    asyncio.run(main())
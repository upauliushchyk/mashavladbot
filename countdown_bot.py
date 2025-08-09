import os
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo  # Python 3.9+; or use pytz if you prefer
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

# ----------------- Настройки -----------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")  # поставь сюда токен
# По умолчанию — Кипр
TZ = ZoneInfo("Asia/Nicosia")  # часовой пояс Кипра
# ------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=TZ)
# We'll keep one scheduled job per chat in memory for simplicity:
jobs_by_chat = {}  # chat_id -> job id


# helper: send reminder message
async def send_reminder(application, chat_id, text="Напоминание!"):
    try:
        await application.bot.send_message(chat_id=chat_id, text=text)
        logger.info("Sent reminder to %s", chat_id)
    except Exception as e:
        logger.error("Failed send to %s: %s", chat_id, e)


# command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"Привет! Твой chat_id = {chat_id}\n"
        "Чтобы задать дату и время первого напоминания используй:\n"
        "/setstart YYYY-MM-DDTHH:MM (например /setstart 2025-08-18T20:30)\n"
        "Чтобы изменить время ежедневных напоминаний: /settime HH:MM\n"
        "Остановить напоминания: /stop"
    )


async def setstart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Нужно передать дату и время в формате YYYY-MM-DDTHH:MM")
        return
    raw = context.args[0].strip()
    try:
        # parse like 2025-08-18T20:30
        dt = datetime.fromisoformat(raw)
        # interpret as local TZ (Cyprus)
        dt = dt.replace(tzinfo=TZ)
    except Exception:
        await update.message.reply_text("Неправильный формат. Пример: /setstart 2025-08-18T20:30")
        return

    # Default reminder text and daily time taken from dt.time()
    reminder_text = "Ты приехал на Кипр — не забудь важные дела! 🇨🇾"
    daily_time = dt.timetz()  # time with tzinfo

    # schedule a one-off "first" reminder if start in future, plus schedule daily cron starting next day (or same day if time in future)
    application = context.application

    # remove existing job for this chat if present
    if chat_id in jobs_by_chat:
        try:
            scheduler.remove_job(jobs_by_chat[chat_id])
        except Exception:
            pass
        jobs_by_chat.pop(chat_id, None)

    # If start in future, schedule first-date job (DateTrigger)
    now = datetime.now(tz=TZ)
    if dt > now:
        dt_trigger = DateTrigger(run_date=dt)
        job_first = scheduler.add_job(
            lambda: application.create_task(send_reminder(application, chat_id, reminder_text)),
            dt_trigger
        )
        logger.info("Scheduled first one-off reminder for %s at %s", chat_id, dt.isoformat())
    else:
        # If start is past or now, send immediately
        await send_reminder(application, chat_id, reminder_text)

    # schedule daily reminders at the specified time (starting from the next occurrence)
    # Use CronTrigger with timezone
    hh = dt.hour
    mm = dt.minute
    cron = CronTrigger(hour=hh, minute=mm, timezone=TZ)
    job = scheduler.add_job(
        lambda: application.create_task(send_reminder(application, chat_id, "Ежедневное напоминание!")),
        cron
    )
    jobs_by_chat[chat_id] = job.id

    await update.message.reply_text(
        f"Запланировано ежедневное напоминание в {hh:02d}:{mm:02d} (часовой пояс Кипра).\n"
        f"Первое напоминание: {dt.isoformat() if dt > now else 'сейчас (отправлено)'}."
    )


async def settime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Нужно передать время в формате HH:MM")
        return
    raw = context.args[0].strip()
    try:
        hh, mm = map(int, raw.split(":"))
        assert 0 <= hh < 24 and 0 <= mm < 60
    except Exception:
        await update.message.reply_text("Неправильный формат. Пример: /settime 09:00")
        return

    application = context.application
    # remove old job
    if chat_id in jobs_by_chat:
        try:
            scheduler.remove_job(jobs_by_chat[chat_id])
        except Exception:
            pass
        jobs_by_chat.pop(chat_id, None)

    # schedule new cron
    cron = CronTrigger(hour=hh, minute=mm, timezone=TZ)
    job = scheduler.add_job(
        lambda: application.create_task(send_reminder(application, chat_id, "Ежедневное напоминание!")),
        cron
    )
    jobs_by_chat[chat_id] = job.id
    await update.message.reply_text(f"Ежедневные напоминания перенесены на {hh:02d}:{mm:02d} (Asia/Nicosia).")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in jobs_by_chat:
        try:
            scheduler.remove_job(jobs_by_chat[chat_id])
        except Exception:
            pass
        jobs_by_chat.pop(chat_id, None)
        await update.message.reply_text("Напоминания остановлены.")
    else:
        await update.message.reply_text("Напоминаний не найдено.")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Не понимаю команду. Доступны: /start /setstart /settime /stop")


def main():
    token = BOT_TOKEN
    if not token:
        raise RuntimeError("Установи BOT_TOKEN в .env")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setstart", setstart))
    app.add_handler(CommandHandler("settime", settime))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    # start scheduler
    scheduler.start()

    # run bot
    logger.info("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()

import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
)

# ---------------- Настройки ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")  # В Render задашь в Environment
TZ = ZoneInfo("Asia/Nicosia")  # часовой пояс Кипра
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=TZ)
jobs_by_chat = {}
# --------------------------------------------


async def send_reminder(application, chat_id, text="Напоминание!"):
    """Отправка сообщения пользователю."""
    try:
        await application.bot.send_message(chat_id=chat_id, text=text)
        logger.info(f"Sent reminder to {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send to {chat_id}: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и инструкция."""
    await update.message.reply_text(
        "Привет! 🏝\n"
        "Команды:\n"
        "/setstart YYYY-MM-DDTHH:MM — установить дату и время первого напоминания\n"
        "/settime HH:MM — установить время ежедневных напоминаний\n"
        "/stop — остановить напоминания"
    )


async def setstart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка первого напоминания и ежедневных."""
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Формат: /setstart YYYY-MM-DDTHH:MM")
        return

    try:
        dt = datetime.fromisoformat(context.args[0]).replace(tzinfo=TZ)
    except Exception:
        await update.message.reply_text("Ошибка формата. Пример: /setstart 2025-08-18T20:30")
        return

    application = context.application

    # Удаляем старое расписание
    if chat_id in jobs_by_chat:
        scheduler.remove_job(jobs_by_chat[chat_id])
        jobs_by_chat.pop(chat_id, None)

    now = datetime.now(TZ)

    # Одноразовое напоминание в день приезда
    if dt > now:
        scheduler.add_job(
            lambda: application.create_task(
                send_reminder(application, chat_id, "Ты приехал на Кипр! 🇨🇾")
            ),
            DateTrigger(run_date=dt)
        )
    else:
        await send_reminder(application, chat_id, "Ты уже на Кипре! 🇨🇾")

    # Ежедневные напоминания
    cron = CronTrigger(hour=dt.hour, minute=dt.minute, timezone=TZ)
    job = scheduler.add_job(
        lambda: application.create_task(
            send_reminder(application, chat_id, "Ежедневное напоминание! 📅")
        ),
        cron
    )
    jobs_by_chat[chat_id] = job.id

    await update.message.reply_text(
        f"Напоминания установлены на {dt.hour:02d}:{dt.minute:02d} (время Кипра)"
    )


async def settime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменение времени ежедневных напоминаний."""
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Формат: /settime HH:MM")
        return

    try:
        hh, mm = map(int, context.args[0].split(":"))
    except Exception:
        await update.message.reply_text("Ошибка формата. Пример: /settime 09:00")
        return

    application = context.application
    if chat_id in jobs_by_chat:
        scheduler.remove_job(jobs_by_chat[chat_id])
        jobs_by_chat.pop(chat_id, None)

    cron = CronTrigger(hour=hh, minute=mm, timezone=TZ)
    job = scheduler.add_job(
        lambda: application.create_task(
            send_reminder(application, chat_id, "Ежедневное напоминание! 📅")
        ),
        cron
    )
    jobs_by_chat[chat_id] = job.id

    await update.message.reply_text(
        f"Время напоминаний изменено на {hh:02d}:{mm:02d} (Asia/Nicosia)"
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановка напоминаний."""
    chat_id = update.effective_chat.id
    if chat_id in jobs_by_chat:
        scheduler.remove_job(jobs_by_chat[chat_id])
        jobs_by_chat.pop(chat_id, None)
        await update.message.reply_text("Напоминания остановлены.")
    else:
        await update.message.reply_text("Напоминаний нет.")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Неизвестная команда. Попробуй /start")


def main():
    token = BOT_TOKEN
    if not token:
        raise RuntimeError("BOT_TOKEN не найден в переменных окружения")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setstart", setstart))
    app.add_handler(CommandHandler("settime", settime))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    scheduler.start()
    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()

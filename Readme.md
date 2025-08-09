# Telegram Reminder Bot

Простой Telegram-бот на Go, который присылает ежедневные напоминания в заданное время.

## Настройка

1. Получите токен бота у [BotFather](https://t.me/BotFather).
2. Узнайте ваш chat ID (например, с помощью getUpdates или сторонних ботов).
3. Создайте файл `.env` или установите переменные окружения:

```bash
export TELEGRAM_BOT_TOKEN="ваш_токен_бота"
export TELEGRAM_CHAT_ID="ваш_chat_id"
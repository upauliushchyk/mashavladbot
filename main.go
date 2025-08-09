package main

import (
	"fmt"
	"log"
	"os"
	"time"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

func main() {
	botToken := os.Getenv("TELEGRAM_BOT_TOKEN")
	chatIDStr := os.Getenv("TELEGRAM_CHAT_ID")

	if botToken == "" || chatIDStr == "" {
		log.Fatal("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
	}

	chatID, err := parseChatID(chatIDStr)
	if err != nil {
		log.Fatalf("Invalid TELEGRAM_CHAT_ID: %v", err)
	}

	bot, err := tgbotapi.NewBotAPI(botToken)
	if err != nil {
		log.Panic(err)
	}

	log.Printf("Authorized on account %s", bot.Self.UserName)

	loc, err := time.LoadLocation("Europe/Nicosia")
	if err != nil {
		log.Fatalf("Failed to load location: %v", err)
	}

	startTime := time.Date(2025, 8, 18, 20, 35, 0, 0, loc)

	go startDailyReminders(bot, chatID, startTime)

	select {}
}

func parseChatID(chatIDStr string) (int64, error) {
	var chatID int64
	_, err := fmt.Sscan(chatIDStr, &chatID)
	return chatID, err
}

func startDailyReminders(bot *tgbotapi.BotAPI, chatID int64, startTime time.Time) {
	now := time.Now().In(startTime.Location())
	var waitDuration time.Duration

	if now.Before(startTime) {
		waitDuration = startTime.Sub(now)
	} else {
		next := time.Date(now.Year(), now.Month(), now.Day(), startTime.Hour(), startTime.Minute(), 0, 0, startTime.Location())
		if !now.Before(next) {
			next = next.Add(24 * time.Hour)
		}
		waitDuration = next.Sub(now)
	}

	log.Printf("Waiting %v until first reminder", waitDuration)
	time.Sleep(waitDuration)

	ticker := time.NewTicker(24 * time.Hour)
	defer ticker.Stop()

	for {
		sendReminder(bot, chatID)
		<-ticker.C
	}
}

func sendReminder(bot *tgbotapi.BotAPI, chatID int64) {
	msg := tgbotapi.NewMessage(chatID, "Напоминание! Не забудь про поездку на Кипр!")
	_, err := bot.Send(msg)
	if err != nil {
		log.Printf("Failed to send message: %v", err)
	} else {
		log.Printf("Sent reminder to chat %d", chatID)
	}
}

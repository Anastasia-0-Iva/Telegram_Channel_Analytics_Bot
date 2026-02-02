import telebot
from config import BOT_TOKEN
from basic_structure import conclusion

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['start'])
def hi_sms(message):
    text = 'Привет! На связи бот - маркетинговый анализатор. \n'\
           'Готов выгрузить данные по активности подписчиков твоего телеграмм канала и дать рекомендации, полученные в ходе статистического анализа. \n'\
           'Пришли @username или ссылку канала и количество дней через пробел.'
    bot.reply_to(message, text)


@bot.message_handler(content_types=['text'])
def analyzer(message):
    try:
        text = message.text.strip()
        if not text:
            bot.reply_to(message, 'Укажите канал.')
            return
        parts = text.split()
        channel = parts[0]

        if not (channel.startswith('@') or channel.startswith('https://')):
            bot.reply_to(message, 'Канал должен начинаться с @ или https://')
            return

        days = 30

        if len(parts) > 1:
            try:
                days = int(parts[1])
                if not 1 <= days <= 365:
                    bot.reply_to(message, 'Количество дней должно быть от 1 до 365.')
                    return
            except ValueError:
                bot.reply_to(message, 'Количество дней должно быть числом.')
                return

        wait_msg = bot.reply_to(message, 'Анализирую канал...')

        result = conclusion(channel, days)

        bot.delete_message(message.chat.id, wait_msg.message_id)
        bot.reply_to(message, result)

    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)[:200]}")
        print(f"Ошибка: {e}")


if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()








import asyncio
import nest_asyncio
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from datetime import datetime, timedelta, timezone
from config import API_ID, API_HASH
   #  @nordfilnews

class ChannelAnalyzer:
    def __init__(self, client):
        self.client = client

    async def get_stats(self, client, limit=200, start_date=None):
        data = []
        async for message in self.client.iter_messages(client, limit=limit):
            text_content = message.text or message.message or ""
            has_text = bool(text_content.strip())
            has_media = bool(message.media)

            data.append({
                'id': message.id,
                'date': message.date.strftime("%d.%m.%Y %H:%M"),
                'date_obj': message.date,
                'hour': message.date.hour,
                'weekday': message.date.strftime("%A"),
                'message_obj': message,
                'views': message.views or 0,
                'replies': message.replies or 0,
                'reactions': message.reactions or 0,
                'forwards': message.forwards or 0,
                'has_text': has_text,
                'text_content': text_content,
                'has_media': has_media
            })

        if start_date:
            filtered = []
            for post in data:
                if post['date_obj'] >= start_date:
                    filtered.append(post)
            return filtered

        return data

    #Вовлеченность аудитории
    def calculate_engagement(self, message):
        if message.reactions: #Считаем реакции
            reactions_count = sum(i.count for i in message.reactions.results)
        else:
            reactions_count = 0

        forwards_count = message.forwards or 0 #Считаем репосты
        views_count = message.views or 1 #Считаем просмотры

        #Результаты вовлеченности
        engagement = (reactions_count + forwards_count) / (views_count or 1) * 100

        return round(engagement, 2)

    #Определяем тип поста
    def get_content_type(self, message_obj):
        if hasattr(message_obj, 'poll') and message_obj.poll:
            return 'poll'
        elif hasattr(message_obj, 'media') and message_obj.media:
            return 'media'
        elif hasattr(message_obj, 'text') and message_obj.text:
            len_txt = len(message_obj.text)
            if len_txt > 500:
                return 'long_text'
            else:
                return 'short_text'
        else:
            return None

    #Определяем самый интересный тип контента
    def analyze_content_preference(self, data):
        type_stats = {}
        for post in data:
            msg = post['message_obj']
            content_type = self.get_content_type(msg)
            engagement = post.get('engagement')

            if content_type not in type_stats:
                type_stats[content_type] = {
                    'engagements': [],  # Все значения ER для этого типа
                    'total_posts': 0,
                    'total_views': 0
                }

            type_stats[content_type]['engagements'].append(engagement)
            type_stats[content_type]['total_posts'] += 1
            type_stats[content_type]['total_views'] += post['views']

        recommendations = []
        for content_type, data in type_stats.items():
            if data['total_posts'] >= 3:
                avg_engagement = sum(data['engagements']) / len(data['engagements'])
                avg_views = data['total_views'] / data['total_posts']

                recommendations.append({
                    'type': content_type,
                    'avg_engagement': round(avg_engagement, 2),
                    'avg_views': round(avg_views, 2),
                    'posts_count': data['total_posts']
                })

        recommendations.sort(key=lambda x: x['avg_engagement'], reverse=True)

        content_descriptions = {
            'media': 'Изображения/Видео',
            'poll': 'Опросы/Голосования',
            'short_text': 'Короткие тексты (<500 символов)',
            'long_text': 'Длинные тексты (500+ символов)',
            None: 'Другое'
        }
        for rec in recommendations:
            rec['description'] = content_descriptions.get(rec['type'], 'Неизвестный тип')

        return recommendations

    #Высчитываем лучшее время для публикации
    def analyze_best_time(self, data):
        hour_stats = {}

        for post in data:
            hour = post.get('hour')
            engagement = post['engagement']

            if hour not in hour_stats:
                hour_stats[hour] = []
            hour_stats[hour].append(engagement)

        if not hour_stats:
            return None

        best_hour = None
        best_avg_engagement = 0

        for hour, engagements in hour_stats.items():
            if len(engagements) >= 2:
                avg_engagement = sum(engagements) / len(engagements)
                if avg_engagement > best_avg_engagement:
                    best_avg_engagement = avg_engagement
                    best_hour = hour

        return best_hour, round(best_avg_engagement, 2)

    # Высчитываем лучшее кол-во текста для поста
    def analyze_best_txt(self, data):
        length_stats = {}

        for post in data:
            if post.get('has_text'):
                msg_obj = post.get('message_obj')
                if msg_obj and hasattr(msg_obj, 'text') and msg_obj.text:
                    text_length = len(msg_obj.text)
                    engagement = post.get('engagement', 0)

                    if text_length not in length_stats:
                        length_stats[text_length] = []
                    length_stats[text_length].append(engagement)

        if not length_stats:
            return None, 0

        best_length = None
        best_avg_engagement = 0

        for length, engagements in length_stats.items():
            avg_engagement = sum(engagements) / len(engagements)
            if avg_engagement > best_avg_engagement:
                best_avg_engagement = avg_engagement
                best_length = length

        return best_length, round(best_avg_engagement, 2)

#ВЫВОД
def conclusion(channel, days):
    nest_asyncio.apply()

    analyzer = ChannelAnalyzer(None)
    lines = []

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Уникальное имя сессии для каждого вызова
    import time
    session_name = f'session_{int(time.time())}_{hash(channel)}'

    client = TelegramClient(
        session_name,  # Уникальное имя
        API_ID,
        API_HASH,
        loop=loop
    )

    async def analyze():
        # Подключаемся как анонимный пользователь
        await client.start()

        # Для публичных каналов можно работать без полной авторизации
        if not await client.is_user_authorized():
            # Устанавливаем анонимный режим
            await client.sign_in(phone='')

        # Нормализуем канал
        if channel.startswith('https://'):
            target = channel
        elif channel.startswith('@'):
            target = channel
        else:
            target = f'@{channel}'

        start_date = datetime.now(timezone.utc) - timedelta(days=days - 1)
        lines.append(f"Анализ за последние {days} дней (с {start_date.strftime('%d.%m.%Y')})")

        try:
            # Получаем информацию о канале
            entity = await client.get_entity(target)
            full_info = await client(GetFullChannelRequest(entity))
            subscribers = full_info.full_chat.participants_count
            lines.append(f"\nАнализ канала: {channel}")
            lines.append(f"Подписчиков: {subscribers:,}")
        except Exception as e:
            lines.append(f"\n⚠Не удалось получить данные о подписчиках: {e}")
            subscribers = None

        # Анализируем посты
        analyzer.client = client
        stats = await analyzer.get_stats(target, limit=200, start_date=start_date)

        if not stats:
            lines.append(f"\nЗа последние {days} дней постов не найдено")
            return

        lines.append(f"\nПроанализировано постов: {len(stats)}")

        lines.append("СТАТИСТИКА ПОСЛЕДНИХ ПОСТОВ:")

        for post in stats:
            engagement = analyzer.calculate_engagement(post['message_obj'])
            post['engagement'] = engagement
            lines.append(f"Дата: {post['date']} | Просмотры: {post['views']} | Вовлечённость аудитории: {engagement}%")

        lines.append("\nРЕКОМЕНДАЦИИ:")

        # Тип контента
        recommendations = analyzer.analyze_content_preference(stats)
        if recommendations:
            best = recommendations[0]
            lines.append(f"Лучший тип контента: {best['type']} ({best['description']})")
            lines.append(f"- Средняя вовлечённость: {best['avg_engagement']}%")
            lines.append(f"- Средние просмотры: {best['avg_views']:.0f}")
            lines.append(f"- Рекомендация: делайте больше контента типа '{best['type']}'!")

        # Лучшее время
        best_hour, best_engagement = analyzer.analyze_best_time(stats)
        if best_hour is not None:
            lines.append(f"\nЛучшее время для публикации: {best_hour}:00")
            lines.append(f"- Вовлечённость в это время: {best_engagement}%")
            lines.append(f"- Рекомендуемый интервал: {best_hour}:00-{best_hour + 1}:00")

        # Длина текста
        best_length, best_engagement_txt = analyzer.analyze_best_txt(stats)
        if best_length is not None:
            lines.append(f"\nОптимальная длина текста: {best_length} символов")
            lines.append(f"- Вовлечённость аудитории при такой длине: {best_engagement_txt}%")
            lines.append(f"- Рекомендация: старайтесь укладываться в ~{best_length} знаков")

        if subscribers:
            # Рассчитываем среднюю охватность
            avg_views = sum(p['views'] for p in stats) / len(stats)
            reach_percent = (avg_views / subscribers) * 100
            lines.append(f"\nОХВАТ: {avg_views:.0f} просмотров в среднем")
            lines.append(f"- Это {reach_percent:.1f}% от аудитории")

    loop.run_until_complete(analyze())

    return "\n".join(lines)

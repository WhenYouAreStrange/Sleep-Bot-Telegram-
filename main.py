import random
import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Токен, который ты получил от BotFather
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# Данные о времени
sleep_schedule = {
    "6:00": ["20:45", "22:15"],
    "6:30": ["21:15", "22:45"],
    "7:00": ["21:45", "23:15"],
    "7:30": ["22:15", "23:45"],
    "8:00": ["22:45", "00:15"],
    "8:30": ["23:15", "00:45"],
    "9:00": ["23:45", "01:15"],
    "9:30": ["00:15", "01:45"],
}


# Функция для чтения советов и упражнений из текстовых файлов
def load_tips(filename="sleep_tips.txt"):
    with open(filename, "r", encoding="utf-8") as file:
        tips = file.readlines()
    return [tip.strip() for tip in tips]


def load_exercises(filename="sleep_exercises.txt"):
    with open(filename, "r", encoding="utf-8") as file:
        exercises = file.readlines()
    return [exercise.strip() for exercise in exercises]


sleep_tips = load_tips()
sleep_exercises = load_exercises()

# Состояния для ConversationHandler
LOGGING_SLEEP, LOGGING_WAKE = range(2)

# Словарь для хранения данных о сне пользователя
sleep_data = {}

# Словарь для хранения даты последнего ввода данных о сне
last_log_date = {}

# Словарь для хранения последнего отправленного упражнения
last_exercise = {}

# Словарь для хранения последнего отправленного совета
last_tip = {}

# Словарь для хранения достижений пользователей
user_achievements = {}


# Функция для проверки корректности времени
def is_valid_time(time_str):
    match = re.match(r"^([01]?[0-9]|2[0-3]):([0-5][0-9])$", time_str)
    return bool(match)


# Функция для проверки достижений пользователя
def check_achievements(user_id):
    user_data = sleep_data.get(user_id, [])
    if user_id not in user_achievements:
        user_achievements[user_id] = []

    if len(user_data) >= 3 and "Начинающий сонник" not in user_achievements[user_id]:
        user_achievements[user_id].append("Начинающий сонник")
        return "Вы получили достижение: Начинающий сонник (Логирование сна в течение 3 дней подряд)!"

    if len(user_data) >= 7 and "Продвинутый сонник" not in user_achievements[user_id]:
        user_achievements[user_id].append("Продвинутый сонник")
        return "Вы получили достижение: Продвинутый сонник (Логирование сна в течение 7 дней подряд)!"

    if len(user_data) >= 30 or "Мастер сна" not in user_achievements[user_id]:
        user_achievements[user_id].append("Мастер сна")
        return "Вы получили достижение: Мастер сна (Логирование сна в течение 30 дней подряд)!"

    if (
        all(
            datetime.strptime(entry["sleep_time"], "%H:%M").hour < 22
            for entry in user_data[-5:]
        )
        and "Ранний пташка" not in user_achievements[user_id]
    ):
        user_achievements[user_id].append("Ранний пташка")
        return "Вы получили достижение: Ранний пташка (Ложиться спать до 22:00 в течение 5 дней подряд)!"

    if (
        all(
            datetime.strptime(entry["sleep_time"], "%H:%M").hour >= 0
            for entry in user_data[-5:]
        )
        and "Ночной сова" not in user_achievements[user_id]
    ):
        user_achievements[user_id].append("Ночной сова")
        return "Вы получили достижение: Ночной сова (Ложиться спать после 00:00 в течение 5 дней подряд)!"

    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton(time, callback_data=time)]
        for time in sleep_schedule.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Выберите время, когда нужно проснуться:", reply_markup=reply_markup
    )


async def show_times(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    wake_time = query.data
    sleep_times = sleep_schedule[wake_time]

    response_text = f'Если нужно проснуться в {wake_time}, то лучше лечь спать в одно из следующих времён: {", ".join(sleep_times)}'
    await query.edit_message_text(text=response_text)


async def send_tips(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    tip = random.choice(sleep_tips)

    # Проверка, чтобы не отправлять подряд два одинаковых совета
    while user_id in last_tip and tip == last_tip[user_id]:
        tip = random.choice(sleep_tips)

    last_tip[user_id] = tip
    await update.message.reply_text(f"Совет по улучшению сна: {tip}")


async def send_exercises(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    exercise = random.choice(sleep_exercises)

    # Проверка, чтобы не отправлять подряд два одинаковых упражнения
    while user_id in last_exercise and exercise == last_exercise[user_id]:
        exercise = random.choice(sleep_exercises)

    last_exercise[user_id] = exercise
    await update.message.reply_text(f"Упражнение для улучшения сна: {exercise}")


async def log_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    today = datetime.now().date()

    if user_id in last_log_date and last_log_date[user_id] == today:
        await update.message.reply_text(
            "Вы уже вводили данные о сне сегодня. Пожалуйста, попробуйте снова завтра."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Пожалуйста, введите время, когда вы легли спать (в формате ЧЧ:ММ):"
    )
    return LOGGING_SLEEP


async def log_wake(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    sleep_time = update.message.text

    if not is_valid_time(sleep_time):
        await update.message.reply_text(
            "Некорректное время. Пожалуйста, введите время в формате ЧЧ:ММ (например, 22:30)."
        )
        return LOGGING_SLEEP

    sleep_data.setdefault(user_id, []).append({"sleep_time": sleep_time})
    await update.message.reply_text(
        "Пожалуйста, введите время, когда вы проснулись (в формате ЧЧ:ММ):"
    )
    return LOGGING_WAKE


async def save_sleep_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    wake_time = update.message.text

    if not is_valid_time(wake_time):
        await update.message.reply_text(
            "Некорректное время. Пожалуйста, введите время в формате ЧЧ:ММ (например, 06:30)."
        )
        return LOGGING_WAKE

    sleep_data[user_id][-1]["wake_time"] = wake_time
    last_log_date[user_id] = datetime.now().date()

    await update.message.reply_text(
        f'Данные о сне сохранены: Легли спать в {sleep_data[user_id][-1]["sleep_time"]}, проснулись в {wake_time}.'
    )

    achievement_message = check_achievements(user_id)
    if achievement_message:
        await update.message.reply_text(achievement_message)

    return ConversationHandler.END


def calculate_sleep_duration(sleep_time: str, wake_time: str) -> float:
    sleep_dt = datetime.strptime(sleep_time, "%H:%M")
    wake_dt = datetime.strptime(wake_time, "%H:%M")
    if wake_dt < sleep_dt:
        wake_dt += timedelta(days=1)
    duration = (wake_dt - sleep_dt).seconds / 3600
    return duration


async def send_weekly_report(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user_id = update.message.from_user.id
    if user_id not in sleep_data or len(sleep_data[user_id]) == 0:
        await update.message.reply_text("Нет данных о сне за последнюю неделю.")
        return

    last_week_data = sleep_data[user_id][-7:]
    durations = [
        calculate_sleep_duration(entry["sleep_time"], entry["wake_time"])
        for entry in last_week_data
    ]
    avg_duration = sum(durations) / len(durations)

    plt.figure(figsize=(10, 5))
    plt.plot(durations, marker="o")
    plt.title("Продолжительность сна за последнюю неделю")
    plt.xlabel("Дни")
    plt.ylabel("Часы сна")
    plt.grid(True)
    plt.savefig("weekly_report.png")

    await update.message.reply_text(
        f"Средняя продолжительность сна за последнюю неделю: {avg_duration:.2f} часов."
    )
    await update.message.reply_photo(photo=open("weekly_report.png", "rb"))


async def send_monthly_report(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user_id = update.message.from_user.id
    if user_id not in sleep_data or len(sleep_data[user_id]) == 0:
        await update.message.reply_text("Нет данных о сне за последний месяц.")
        return

    last_month_data = sleep_data[user_id][-30:]
    durations = [
        calculate_sleep_duration(entry["sleep_time"], entry["wake_time"])
        for entry in last_month_data
    ]
    avg_duration = sum(durations) / len(durations)

    plt.figure(figsize=(10, 5))
    plt.plot(durations, marker="o")
    plt.title("Продолжительность сна за последний месяц")
    plt.xlabel("Дни")
    plt.ylabel("Часы сна")
    plt.grid(True)
    plt.savefig("monthly_report.png")

    await update.message.reply_text(
        f"Средняя продолжительность сна за последний месяц: {avg_duration:.2f} часов."
    )
    await update.message.reply_photo(photo=open("monthly_report.png", "rb"))


async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    achievements = user_achievements.get(user_id, [])

    if not achievements:
        await update.message.reply_text("У вас пока нет достижений.")
    else:
        await update.message.reply_text(f'Ваши достижения: {", ".join(achievements)}')


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("tips", send_tips))
    application.add_handler(CommandHandler("exercises", send_exercises))
    application.add_handler(CommandHandler("weekly_report", send_weekly_report))
    application.add_handler(CommandHandler("monthly_report", send_monthly_report))
    application.add_handler(CommandHandler("achievements", show_achievements))

    # Обработчик для записи данных о сне
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("log_sleep", log_sleep)],
        states={
            LOGGING_SLEEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, log_wake)],
            LOGGING_WAKE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_sleep_data)
            ],
        },
        fallbacks=[],
    )
    application.add_handler(conv_handler)

    # Обработчик для выбора времени пробуждения
    application.add_handler(CallbackQueryHandler(show_times))

    application.run_polling()


if __name__ == "__main__":
    main()

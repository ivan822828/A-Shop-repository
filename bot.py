import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

# ========== НАСТРОЙКА ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен из переменных окружения
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    logger.error("❌ BOT_TOKEN не найден!")
    exit(1)

# Состояния для ConversationHandler
SELECTING_CATEGORY, SELECTING_FRUIT = range(2)

# ========== КАТЕГОРИИ ТОВАРОВ (1-й УРОВЕНЬ) ==========
CATEGORIES = {
    "fruits": {
        "name": "🍎 Фрукты",
        "description": "Свежие и сочные фрукты"
    },
    "vegetables": {
        "name": "🥕 Овощи",
        "description": "Экологически чистые овощи"
    },
    "berries": {
        "name": "🍓 Ягоды",
        "description": "Сладкие лесные и садовые ягоды"
    },
    "exotic": {
        "name": "🥭 Экзотика",
        "description": "Тропические фрукты со всего мира"
    }
}

# ========== ФРУКТЫ (2-й УРОВЕНЬ) ==========
FRUITS = {
    "apples": {
        "name": "🍎 Яблоки",
        "price": "150 руб/кг",
        "description": "Сочные красные яблоки. Сорт: Голден"
    },
    "bananas": {
        "name": "🍌 Бананы",
        "price": "120 руб/кг",
        "description": "Спелые бананы из Эквадора"
    },
    "peaches": {
        "name": "🍑 Персики",
        "price": "250 руб/кг",
        "description": "Сочные персики, выращенные в Краснодарском крае"
    },
    "pears": {
        "name": "🍐 Груши",
        "price": "180 руб/кг",
        "description": "Сладкие и сочные груши сорта Конференция"
    }
}

# Реквизиты для оплаты
PAYMENT_DETAILS = """
💳 **Реквизиты для оплаты:**

🏦 **Сбербанк**
Номер карты: `2202 1234 5678 9010`
Получатель: Иван Иванов

📌 **После оплаты отправьте скриншот в этот чат.**
"""

# ========== FLASK ==========
app = Flask(__name__)

# ========== БОТ ==========
updater = Updater(token=TOKEN, use_context=True)
dp = updater.dispatcher

# Временное хранилище данных пользователя
user_data = {}

# ========== ОБРАБОТЧИКИ ==========

def start(update, context):
    """Главное меню с категориями товаров (1-й уровень)"""
    user_id = update.effective_user.id
    user_data[user_id] = {}
    
    keyboard = []
    for cat_id, cat_info in CATEGORIES.items():
        button_text = f"{cat_info['name']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"cat_{cat_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "🍏 **Добро пожаловать в фруктовый магазин!**\n\n"
        "👇 Выберите категорию товаров:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return SELECTING_CATEGORY

def category_selected(update, context):
    """Показывает фрукты в выбранной категории (2-й уровень)"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    cat_id = query.data.replace("cat_", "")
    category = CATEGORIES.get(cat_id)
    
    if not category:
        query.edit_message_text("❌ Категория не найдена")
        return ConversationHandler.END
    
    # Сохраняем выбранную категорию
    user_data[user_id] = {"category_id": cat_id, "category": category}
    
    # Для категории "Фрукты" показываем конкретные фрукты
    if cat_id == "fruits":
        keyboard = [
            [InlineKeyboardButton(FRUITS['apples']['name'], callback_data="fruit_apples")],
            [InlineKeyboardButton(FRUITS['bananas']['name'], callback_data="fruit_bananas")],
            [InlineKeyboardButton(FRUITS['peaches']['name'], callback_data="fruit_peaches")],
            [InlineKeyboardButton(FRUITS['pears']['name'], callback_data="fruit_pears")],
            [InlineKeyboardButton("🔙 Назад к категориям", callback_data="back_to_categories")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            f"**{category['name']}**\n\n"
            f"{category['description']}\n\n"
            f"👇 Выберите фрукт:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return SELECTING_FRUIT
    else:
        # Для других категорий (пока заглушка)
        keyboard = [[InlineKeyboardButton("🔙 Назад к категориям", callback_data="back_to_categories")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            f"**{category['name']}**\n\n"
            f"{category['description']}\n\n"
            f"🛒 В этой категории пока нет товаров.\n\n"
            f"Выберите другую категорию:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return SELECTING_CATEGORY

def fruit_selected(update, context):
    """Показывает информацию о выбранном фрукте"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    fruit_id = query.data.replace("fruit_", "")
    fruit = FRUITS.get(fruit_id)
    
    if not fruit:
        query.edit_message_text("❌ Фрукт не найден")
        return ConversationHandler.END
    
    # Сохраняем выбранный фрукт
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["fruit"] = fruit
    
    # Кнопки для подтверждения
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить заказ", callback_data="confirm_order")],
        [InlineKeyboardButton("🔙 Назад к фруктам", callback_data="back_to_fruits")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_order")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    fruit_text = (
        f"**{fruit['name']}**\n\n"
        f"{fruit['description']}\n\n"
        f"💰 **Цена: {fruit['price']}**\n\n"
        f"Подтвердите заказ:"
    )
    
    query.edit_message_text(
        fruit_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return SELECTING_FRUIT

def confirm_order(update, context):
    """Подтверждение заказа и показ реквизитов"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    
    if user_id not in user_data or "fruit" not in user_data[user_id]:
        query.edit_message_text("❌ Ошибка. Начните заново: /start")
        return ConversationHandler.END
    
    fruit = user_data[user_id]["fruit"]
    
    # Формируем итоговое сообщение
    order_text = (
        f"✅ **ЗАКАЗ ПОДТВЕРЖДЕН!**\n\n"
        f"**{fruit['name']}**\n\n"
        f"{fruit['description']}\n\n"
        f"💰 **ИТОГО К ОПЛАТЕ: {fruit['price']}**\n\n"
    )
    
    final_text = order_text + PAYMENT_DETAILS
    
    # Кнопка для нового заказа
    keyboard = [[InlineKeyboardButton("🛍️ Новый заказ", callback_data="new_order")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        final_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return ConversationHandler.END

def back_to_categories(update, context):
    """Возврат к списку категорий (1-й уровень)"""
    query = update.callback_query
    query.answer()
    
    keyboard = []
    for cat_id, cat_info in CATEGORIES.items():
        button_text = f"{cat_info['name']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"cat_{cat_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "🍏 **Выберите категорию товаров:**",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return SELECTING_CATEGORY

def back_to_fruits(update, context):
    """Возврат к списку фруктов (2-й уровень)"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    category = user_data.get(user_id, {}).get("category", {})
    
    keyboard = [
        [InlineKeyboardButton(FRUITS['apples']['name'], callback_data="fruit_apples")],
        [InlineKeyboardButton(FRUITS['bananas']['name'], callback_data="fruit_bananas")],
        [InlineKeyboardButton(FRUITS['peaches']['name'], callback_data="fruit_peaches")],
        [InlineKeyboardButton(FRUITS['pears']['name'], callback_data="fruit_pears")],
        [InlineKeyboardButton("🔙 Назад к категориям", callback_data="back_to_categories")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        f"**{category.get('name', 'Фрукты')}**\n\n"
        f"👇 Выберите фрукт:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return SELECTING_FRUIT

def new_order(update, context):
    """Начать новый заказ"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    user_data[user_id] = {}
    
    keyboard = []
    for cat_id, cat_info in CATEGORIES.items():
        button_text = f"{cat_info['name']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"cat_{cat_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "🛍️ **Новый заказ**\n\n👇 Выберите категорию:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return SELECTING_CATEGORY

def cancel_order(update, context):
    """Отмена заказа"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    user_data.pop(user_id, None)
    
    keyboard = [[InlineKeyboardButton("🛍️ Начать заново", callback_data="new_order")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "❌ Заказ отменен.\n\nМожете начать новый заказ:",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

def help_command(update, context):
    """Команда /help"""
    update.message.reply_text(
        "📖 **Помощь**\n\n"
        "/start - Начать заказ\n"
        "/help - Эта справка\n"
        "/cancel - Отменить текущий заказ",
        parse_mode="Markdown"
    )

def cancel(update, context):
    """Отмена через команду"""
    user_id = update.message.from_user.id
    user_data.pop(user_id, None)
    update.message.reply_text("❌ Заказ отменен. /start - новый заказ")
    return ConversationHandler.END

def unknown(update, context):
    """Обработка неизвестных команд"""
    update.message.reply_text("❌ Неизвестная команда. Используйте /start")

# ========== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ==========

# ConversationHandler для основного процесса заказа
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        SELECTING_CATEGORY: [
            CallbackQueryHandler(category_selected, pattern="^cat_"),
            CallbackQueryHandler(back_to_categories, pattern="^back_to_categories$"),
            CallbackQueryHandler(new_order, pattern="^new_order$")
        ],
        SELECTING_FRUIT: [
            CallbackQueryHandler(fruit_selected, pattern="^fruit_"),
            CallbackQueryHandler(back_to_fruits, pattern="^back_to_fruits$"),
            CallbackQueryHandler(back_to_categories, pattern="^back_to_categories$"),
            CallbackQueryHandler(confirm_order, pattern="^confirm_order$"),
            CallbackQueryHandler(cancel_order, pattern="^cancel_order$")
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

dp.add_handler(conv_handler)
dp.add_handler(CommandHandler("help", help_command))
dp.add_handler(CallbackQueryHandler(new_order, pattern="^new_order$"))
dp.add_handler(MessageHandler(filters.COMMAND, unknown))

# ========== FLASK МАРШРУТЫ ==========
@app.route('/')
def index():
    return "✅ Fruit Shop Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(), updater.bot)
        dp.process_update(update)
        return 'ok', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'error', 500

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ != "__main__":
    # Для Gunicorn
    pass

import configparser
import logging
import os

from geolocation import GeoLocation
from utils import get_btn_text_from_cb_data

from telegram.constants import PARSEMODE_HTML
from telegram import (
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
    Update
)
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    ChosenInlineResultHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    CallbackContext,
    Filters,
    PicklePersistence
)

HELLO_MSG = 'Привіт! Я — ЕкспресоБот.\n' \
            'Моя головна ціль — автоматизовувати підтримку клієнтів служби доставки Експресо шляхом ' \
            'розуміння природньої мови (NLP).\n\n'
AUTH_SUCCESS_MSG = 'Авторизація успішна.'
ALREADY_AUTH_MSG = 'Неможливо авторизуватися: користувач уже авторизований.'

SIGN_IN_BTN = 'Реєстрація'
CREATE_SHIPMENT_BTN = 'Створити посилку'
GET_SHIPMENT_BTN = 'Отримати дані про посилку'
EDIT_SHIPMENT_BTN = 'Змінити дані про посилку'
NEAREST_BTN = 'Побудувати маршрут до найближчого відділення'
CONTACT_OPERATOR_BTN = 'З\'єднатися з оператором'

CREATE_SHIPMENT_CB = 'create_shipment'
GET_SHIPMENT_CB = 'get_shipment'
EDIT_SHIPMENT_CB = 'edit_shipment'
NEAREST_CB = 'nearest'
CONTACT_OPERATOR_CB = 'contact_operator'

SELECTED_FUNCTION_MSG = 'Обрана функція "{}".'

MENU_KEYBOARD = [
    [InlineKeyboardButton(CREATE_SHIPMENT_BTN, callback_data=CREATE_SHIPMENT_CB)],
    [InlineKeyboardButton(GET_SHIPMENT_BTN, callback_data=GET_SHIPMENT_CB)],
    [InlineKeyboardButton(EDIT_SHIPMENT_BTN, callback_data=EDIT_SHIPMENT_CB)],
    [InlineKeyboardButton(NEAREST_BTN, callback_data=NEAREST_CB)],
    [InlineKeyboardButton(CONTACT_OPERATOR_BTN, callback_data=CONTACT_OPERATOR_CB)]
]
MENU_MARKUP = InlineKeyboardMarkup(MENU_KEYBOARD, one_time_keyboard=True, resize_keyboard=True)

CONTACT, LOCATION = range(2)
END = ConversationHandler.END


def get_tokens(filename='config/config.ini') -> tuple:
    config = configparser.ConfigParser()
    config.read(filename)
    default = config['DEFAULT']
    return default['TELEGRAM_TOKEN'], default['GCP_TOKEN']


def start(update: Update, context: CallbackContext) -> None or int:
    try:
        if context.user_data['contact']:
            update.message.reply_text(ALREADY_AUTH_MSG)
            intro(update, context)

    except KeyError:
        contact_keyboard = KeyboardButton(text=SIGN_IN_BTN, request_contact=True)
        custom_keyboard = [[contact_keyboard]]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard, one_time_keyboard=True)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{HELLO_MSG} Для початку роботи натисніть кнопку «{SIGN_IN_BTN}», '
                 'після чого необхідно дозволити Telegram передати боту Ваш номер телефону.',
            reply_markup=reply_markup
        )
        return CONTACT


def contact(update: Update, context: CallbackContext) -> None:
    user_contact = update.message.contact
    context.user_data['contact'] = user_contact
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=AUTH_SUCCESS_MSG
    )
    intro(update, context)


def intro(update: Update, _: CallbackContext) -> int:
    update.message.reply_text(
        text='Як я можу допомогти?\n'
             'Введіть своє питання вручну або перегляньте список доступних команд, скориставшись командою /menu.'
    )
    return END


def menu(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Оберіть функцію з меню, представленого нижче:',
        reply_markup=MENU_MARKUP
    )


def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    callback_data = query.data
    # context.bot.send_message(
    #     chat_id=update.effective_chat.id,
    #     text=SELECTED_FUNCTION_MSG.format(get_btn_text_from_cb_data(query.message, callback_data))
    # )
    not_implemented = ['create_shipment', 'get_shipment', 'edit_shipment', 'contact_operator']  # TODO
    if callback_data in not_implemented:
        query.delete_message()
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Функція "{get_btn_text_from_cb_data(query.message, callback_data)}" в розробці.'
        )


def nearest(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.delete_message()  # TODO consider replacing with 'edit_message_text' to add interactivity

    location_keyboard = KeyboardButton(text='Надіслати поточне місцезнаходження', request_location=True)
    custom_keyboard = [[location_keyboard]]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, one_time_keyboard=True)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Для побудови маршруту до найближчого відділення потрібно надати доступ до місцезнаходження. '
             'Надати доступ?',
        reply_markup=reply_markup
    )
    return LOCATION


def location(update: Update, context: CallbackContext) -> int:
    user_location = update.message.location
    origin = (user_location.latitude, user_location.longitude)
    result = GeoLocation.get_nearest_office_lat_lon(origin, gcp_token)  # destination, distance

    reply_markup = ReplyKeyboardRemove()
    if type(result) == tuple:
        destination, distance = result
        url = GeoLocation.get_url_from_lat_lon(origin, destination)

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Маршрут побудовано: до найближчого відділення <b>{distance}</b>; '
                 f'перейдіть <a href="{url}">за посиланням</a>, щоб переглянути запропонований маршрут.',
            reply_markup=reply_markup,
            parse_mode=PARSEMODE_HTML,
            disable_web_page_preview=True
        )
    elif type(result) == str:  # result contains error message
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=result,
            reply_markup=reply_markup
        )
    return END


def cancel(update: Update, _: CallbackContext) -> int:
    update.message.reply_text(
        'Успішно скасовано.',
        reply_markup=ReplyKeyboardRemove()
    )
    return END


def echo(update, context):
    logger.info(f'{update.message.from_user} wrote {update.message.text}')
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

if __name__ == '__main__':
    logger = logging.getLogger(__name__)

    data_dir = 'data'
    if not os.path.exists(f'{os.getcwd()}/{data_dir}'):
        os.mkdir(data_dir)
    persistence = PicklePersistence(filename='data/persistent')

    telegram_token, gcp_token = get_tokens()
    updater = Updater(
        token=telegram_token,
        persistence=persistence,
        use_context=True,
    )
    dispatcher = updater.dispatcher

    cancel_handler = CommandHandler('cancel', cancel)

    authorization_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CONTACT: [MessageHandler(Filters.contact, contact)]
        },
        fallbacks=[cancel_handler],
        name='authorization_handler',
        # persistent=True
    )

    location_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                callback=nearest,
                pattern=NEAREST_CB
            )],
        states={
            LOCATION: [MessageHandler(Filters.location, location)]
        },
        fallbacks=[cancel_handler],
        name='location_handler',
        # per_message=True
        # persistent=True
    )

    menu_handler = CommandHandler('menu', menu)

    dispatcher.add_handler(authorization_handler)
    dispatcher.add_handler(location_handler)
    dispatcher.add_handler(menu_handler)
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(cancel_handler)

    echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
    dispatcher.add_handler(echo_handler)

    updater.start_polling()

    updater.idle()

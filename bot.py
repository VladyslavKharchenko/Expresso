import configparser
import logging
import os

from bot.utils import GeoLocation
from bot.utils import get_btn_text_from_cb_data

from telegram.constants import PARSEMODE_HTML
from telegram import (
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
    Update,
    Contact
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    CallbackContext,
    Filters,
    PicklePersistence
)

TELEGRAM_TOKEN = ''
GCP_TOKEN = ''

HELLO_MSG = 'Привіт! Я — ЕкспресоБот.\n' \
            'Моя головна ціль — автоматизовувати підтримку клієнтів служби доставки Експресо шляхом ' \
            'розуміння природньої мови (NLP).\n\n'
AUTH_SUCCESS_MSG = 'Авторизація успішна: {}'
ALREADY_AUTH_MSG = 'Неможливо авторизуватися: користувач уже авторизований як {}.'
DIALOG_START_MSG = 'Користувач {} шукає вільного оператора.'
NOT_CONTACT_MSG = 'Надіслане повідомлення не є контактом! Надішліть контакт.'

ADMIN = 'оператор'
ADMIN_SUDO = 'старший оператор'
USER = 'користувач'

SIGN_IN_TEXT = 'Реєстрація'
CREATE_SHIPMENT_TEXT = 'Створити посилку'
GET_SHIPMENT_TEXT = 'Отримати дані про посилку'
EDIT_SHIPMENT_TEXT = 'Змінити дані про посилку'
NEAREST_TEXT = 'Побудувати маршрут до найближчого відділення'
CHAT_WITH_OPERATOR_TEXT = 'З\'єднатися з оператором'
CHAT_WITH_USER_TEXT = 'З\'єднатися з користувачем'
END_CHAT_TEXT = 'Так, завершити чат'
CONTINUE_CHAT_TEXT = 'Ні, продовжити спілкування з оператором'
EDIT_ADMINS_TEXT = 'Відредагувати список операторів'
ADD_ADMIN_TEXT = 'Надати користувачу права оператора'
ADD_ADMIN_SUDO_TEXT = 'Надати користувачу права старшого оператора'
REMOVE_ADMIN_TEXT = 'Позбавити користувача прав оператора'

CREATE_SHIPMENT_CB = 'create_shipment'
GET_SHIPMENT_CB = 'get_shipment'
EDIT_SHIPMENT_CB = 'edit_shipment'
NEAREST_CB = 'nearest'
CHAT_WITH_OPERATOR_CB = 'chat_with_operator'
CHAT_WITH_USER_CB = 'chat_with_user'
END_CHAT_CB = 'end_chat'
CONTINUE_CHAT_CB = 'continue_chat'
EDIT_ADMINS_CB = 'edit_admins'
ADD_ADMIN_CB = 'add_admin'
ADD_ADMIN_SUDO_CB = 'add_admin_sudo'
REMOVE_ADMIN_CB = 'remove_admin'

SELECTED_FUNCTION_MSG = 'Обрана функція "{}".'

MENU_USER_KEYBOARD = [
    [InlineKeyboardButton(CREATE_SHIPMENT_TEXT, callback_data=CREATE_SHIPMENT_CB)],
    [InlineKeyboardButton(GET_SHIPMENT_TEXT, callback_data=GET_SHIPMENT_CB)],
    [InlineKeyboardButton(EDIT_SHIPMENT_TEXT, callback_data=EDIT_SHIPMENT_CB)],
    [InlineKeyboardButton(NEAREST_TEXT, callback_data=NEAREST_CB)],
    [InlineKeyboardButton(CHAT_WITH_OPERATOR_TEXT, callback_data=CHAT_WITH_OPERATOR_CB)]
]

MENU_ADMIN_SUDO_KEYBOARD = [
    [InlineKeyboardButton(CREATE_SHIPMENT_TEXT, callback_data=CREATE_SHIPMENT_CB)],
    [InlineKeyboardButton(GET_SHIPMENT_TEXT, callback_data=GET_SHIPMENT_CB)],
    [InlineKeyboardButton(EDIT_SHIPMENT_TEXT, callback_data=EDIT_SHIPMENT_CB)],
    [InlineKeyboardButton(NEAREST_TEXT, callback_data=NEAREST_CB)],
    [InlineKeyboardButton(CHAT_WITH_OPERATOR_TEXT, callback_data=CHAT_WITH_OPERATOR_CB)],
    [InlineKeyboardButton(EDIT_ADMINS_TEXT, callback_data=EDIT_ADMINS_CB)]
]

MENU_USER_MARKUP = InlineKeyboardMarkup(MENU_USER_KEYBOARD, one_time_keyboard=True, resize_keyboard=True)
MENU_ADMIN_SUDO_MARKUP = InlineKeyboardMarkup(MENU_ADMIN_SUDO_KEYBOARD, one_time_keyboard=True, resize_keyboard=True)

CHAT_KEYBOARD = [
    [InlineKeyboardButton(END_CHAT_TEXT, callback_data=END_CHAT_CB)],
    [InlineKeyboardButton(CONTINUE_CHAT_TEXT, callback_data=CONTINUE_CHAT_CB)]
]
CHAT_MARKUP = InlineKeyboardMarkup(CHAT_KEYBOARD, one_time_keyboard=True, resize_keyboard=True)

EDIT_ADMINS_KEYBOARD = [
    [InlineKeyboardButton(ADD_ADMIN_TEXT, callback_data=ADD_ADMIN_CB)],
    [InlineKeyboardButton(ADD_ADMIN_SUDO_TEXT, callback_data=ADD_ADMIN_SUDO_CB)],
    [InlineKeyboardButton(REMOVE_ADMIN_TEXT, callback_data=REMOVE_ADMIN_CB)]
]
EDIT_ADMINS_MARKUP = InlineKeyboardMarkup(EDIT_ADMINS_KEYBOARD)

CONTACT, LOCATION, WAITING_FOR_CHAT, CHAT, EDIT_ADMINS, ADD_ADMIN, ADD_ADMIN_SUDO, REMOVE_ADMIN = range(8)
END = ConversationHandler.END


def get_tokens(filename='config/config.ini') -> tuple:
    config = configparser.ConfigParser()
    config.read(filename)
    default = config['DEFAULT']
    return default['TELEGRAM_TOKEN'], default['GCP_TOKEN']


def get_user_type(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id in context.bot_data['admins']:
        if context.bot_data['admins'][user_id]['sudo']:
            return ADMIN_SUDO
        return ADMIN
    return USER


def _add_admin(user_contact: Contact, context: CallbackContext, sudo=False):
    user_id = user_contact.user_id
    first_name = user_contact.first_name

    admins = context.bot_data['admins']
    admins[user_id] = {}

    new_admin = admins[user_id]
    new_admin['name'] = first_name
    new_admin['is_available'] = False
    new_admin['sudo'] = sudo
    return True


def _remove_admin(user_contact: Contact, context: CallbackContext):
    user_id = user_contact.user_id
    admins = context.bot_data['admins']
    del admins[user_id]
    return True


def _get_admin_name_by_id(user_id: int, context: CallbackContext):
    return context.bot_data['admins'][user_id]['name']


def start(update: Update, context: CallbackContext) -> None or int:
    try:
        if context.user_data['contact']:
            user_type = get_user_type(update, context)
            update.message.reply_text(ALREADY_AUTH_MSG.format(user_type))
            intro(update, context)

    except KeyError:
        contact_keyboard = KeyboardButton(text=SIGN_IN_TEXT, request_contact=True)
        custom_keyboard = [[contact_keyboard]]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard, one_time_keyboard=True)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{HELLO_MSG} Для початку роботи натисніть кнопку «{SIGN_IN_TEXT}», '
                 'після чого необхідно дозволити Telegram передати боту Ваш номер телефону.',
            reply_markup=reply_markup
        )
        return CONTACT


def contact(update: Update, context: CallbackContext) -> None:
    user_contact = update.message.contact
    context.user_data['contact'] = user_contact
    user_type = get_user_type(update, context)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=AUTH_SUCCESS_MSG.format(user_type)
    )
    intro(update, context)


def intro(update: Update, _: CallbackContext) -> int:
    update.message.reply_text(
        text='Як я можу допомогти?\n'
             'Введіть своє питання вручну або перегляньте список доступних команд, скориставшись командою /menu.'
    )
    return END


def menu(update: Update, context: CallbackContext) -> None:
    user_type = get_user_type(update, context)
    if user_type == ADMIN_SUDO:
        markup = MENU_ADMIN_SUDO_MARKUP
    elif (user_type == USER) or (user_type == ADMIN):
        markup = MENU_USER_MARKUP
    else:
        raise Exception(f'Menu for {user_type} does not exist!')

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Оберіть функцію з меню, представленого нижче.\nДля відміни скористайтесь /cancel.',
        reply_markup=markup
    )


def menu_pressed(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    callback_data = query.data
    not_implemented = ['create_shipment', 'get_shipment', 'edit_shipment']  # TODO
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
    result = GeoLocation.get_nearest_office_lat_lon(origin, GCP_TOKEN)  # destination, distance

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


def check_operators_available(update: Update, context: CallbackContext) -> int:
    msg = 'Перевіряю наявність вільних операторів'
    query = update.callback_query
    query.edit_message_text(msg + '...')

    operators = context.bot_data['admins']
    user_id = update.effective_user.id

    for operator_id in operators:
        if operators[operator_id]['is_available']:
            custom_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton(CHAT_WITH_USER_TEXT, callback_data=CHAT_WITH_USER_CB)]]
            )
            context.bot.send_message(
                chat_id=operator_id,
                text=DIALOG_START_MSG.format(user_id),
                reply_markup=custom_markup  # TODO create chat backups for model training
            )
    return WAITING_FOR_CHAT

    # for _ in range(61):
    #     for second in range(4):
    #         sleep(1)
    #         query.edit_message_text(msg + '.' * second)
    # check_operators_available(update, context)


def connect_operator_with_user(update: Update, context: CallbackContext) -> int:
    operator_id = update.effective_user.id
    operator_name = _get_admin_name_by_id(operator_id, context)
    user_id = int(update.effective_message.text.split()[1])

    context.bot_data['admins'][operator_id]['is_available'] = False
    context.bot_data['chats'][user_id] = operator_id
    context.bot_data['chats'][operator_id] = user_id

    custom_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(
            CHAT_WITH_OPERATOR_TEXT,
            callback_data=CHAT_WITH_OPERATOR_CB
        )]]
    )

    context.bot.send_message(
        chat_id=user_id,
        text=f'Доброго дня! Мене звати {operator_name}, я оператор служби доставки Expresso.',
        reply_markup=custom_markup
    )
    query = update.callback_query
    query.answer()
    query.edit_message_reply_markup()
    query.edit_message_text(
        f'Чат з користувачем {user_id} почато. '
        f'Від вашого імені було надіслано привітальне повідомлення.\n'
        f'Якшо ви вважаєте, що питання користувача було вирішено, ви можете завершити чат, '
        f'скориставшись командою /quit.'
    )
    return CHAT


def connect_user_with_operator(update: Update, _: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_reply_markup()
    return CHAT


def chat(update: Update, context: CallbackContext) -> int:
    current_user_id = update.effective_user.id
    other_user_id = context.bot_data['chats'][current_user_id]

    context.bot.send_message(
        chat_id=other_user_id,
        text=update.message.text
    )
    return CHAT


def check_if_resolved(update: Update, context: CallbackContext) -> int:
    current_user_id = update.effective_user.id
    other_user_id = context.bot_data['chats'][current_user_id]

    if current_user_id in context.bot_data['admins']:
        context.bot.send_message(
            chat_id=current_user_id,
            text='Отримуємо відповідь від користувача...',
        )
        context.bot.send_message(
            chat_id=other_user_id,
            text='Чи було вирішено ваше питання?',
            reply_markup=CHAT_MARKUP
        )
    return CHAT


def end_chat(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_reply_markup()
    query.edit_message_text('Дякуємо за відгук, він буде переданий відповідальному оператору.\nЗвертайтесь!')

    current_user_id = update.effective_user.id
    other_user_id = context.bot_data['chats'][current_user_id]

    context.bot.send_message(
        chat_id=other_user_id,
        text=f'Питання користувача {current_user_id} було успішно вирішено!'
    )

    del context.bot_data['chats'][current_user_id]
    del context.bot_data['chats'][other_user_id]

    return END


def continue_chat(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    operator_id = context.bot_data['chats'][user_id]
    operator_name = _get_admin_name_by_id(operator_id, context)

    query = update.callback_query
    query.answer()
    query.edit_message_reply_markup()
    query.edit_message_text(f'Оператор {operator_name} залишатиметься на лінії для подальшого спілкування.')

    context.bot.send_message(
        chat_id=operator_id,
        text=f'Питання користувача {user_id} не було вирішено! Продовжіть спілкування'
    )
    return CHAT


def edit_admins(update: Update, _: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_reply_markup(EDIT_ADMINS_MARKUP)
    return EDIT_ADMINS


def ask_for_admin_contact(update: Update, _: CallbackContext) -> int:
    cb = update.callback_query.data
    update.callback_query.edit_message_text('Надішліть контакт користувача, до якого слід застосувати обрану дію.')
    if cb == ADD_ADMIN_CB:
        return ADD_ADMIN
    elif cb == ADD_ADMIN_SUDO_CB:
        return ADD_ADMIN_SUDO
    elif cb == REMOVE_ADMIN_CB:
        return REMOVE_ADMIN
    else:
        raise Exception(f'Callback is unknown: get_forwarded_message(), cb={cb}')


def add_admin(update: Update, context: CallbackContext) -> int:
    user_contact = update.message.contact
    if not user_contact:
        update.message.reply_text(NOT_CONTACT_MSG)
        return ADD_ADMIN
    if _add_admin(user_contact, context):
        update.message.reply_text('Користувачу були надані права оператора.')
        return END


def add_admin_sudo(update: Update, context: CallbackContext) -> int:
    user_contact = update.message.contact
    if not user_contact:
        update.message.reply_text(NOT_CONTACT_MSG)
        return ADD_ADMIN_SUDO
    if _add_admin(user_contact, context, sudo=True):
        update.message.reply_text('Користувачу були надані права старшого оператора.')
        return END


def remove_admin(update: Update, context: CallbackContext) -> int:
    user_contact = update.message.contact
    if not user_contact:
        update.message.reply_text(NOT_CONTACT_MSG)
        return REMOVE_ADMIN
    if _remove_admin(user_contact, context):
        update.message.reply_text('Користувач був позбавлений прав оператора.')
        return END


def model(update: Update, _: CallbackContext) -> None:
    logger.info(f'{update.message.from_user} wrote {update.message.text}')
    # context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    global TELEGRAM_TOKEN, GCP_TOKEN

    data_dir = 'data'
    if not os.path.exists(f'{os.getcwd()}/{data_dir}'):
        os.mkdir(data_dir)
    persistence = PicklePersistence(filename='data/persistent')

    TELEGRAM_TOKEN, GCP_TOKEN = get_tokens()
    updater = Updater(
        token=TELEGRAM_TOKEN,
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
    )

    location_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                callback=nearest,
                pattern=NEAREST_CB
            )],
        states={
            LOCATION: [
                MessageHandler(
                    filters=Filters.location,
                    callback=location
                )
            ]
        },
        fallbacks=[cancel_handler],
        name='location_handler',
    )

    chat_with_operator_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                callback=check_operators_available,
                pattern=CHAT_WITH_OPERATOR_CB
            ),
            CallbackQueryHandler(
                callback=connect_operator_with_user,
                pattern=CHAT_WITH_USER_CB
            )
        ],
        states={
            WAITING_FOR_CHAT: [
                CallbackQueryHandler(
                    callback=connect_user_with_operator,
                    pattern=CHAT_WITH_OPERATOR_CB
                )
            ],
            CHAT: [
                MessageHandler(
                    filters=Filters.text & (~ Filters.command),
                    callback=chat
                ),
                CommandHandler(
                    command='quit',
                    callback=check_if_resolved
                ),
                CallbackQueryHandler(
                    callback=end_chat,
                    pattern=END_CHAT_CB
                ),
                CallbackQueryHandler(
                    callback=continue_chat,
                    pattern=CONTINUE_CHAT_CB
                )
            ]
        },
        fallbacks=[cancel_handler],
        name='chat_with_operator_handler'
    )

    edit_admins_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                callback=edit_admins,
                pattern=EDIT_ADMINS_CB
            )
        ],
        states={
            EDIT_ADMINS: [
                CallbackQueryHandler(
                    callback=ask_for_admin_contact,
                    pattern=ADD_ADMIN_CB
                ),
                CallbackQueryHandler(
                    callback=ask_for_admin_contact,
                    pattern=ADD_ADMIN_SUDO_CB
                ),
                CallbackQueryHandler(
                    callback=ask_for_admin_contact,
                    pattern=REMOVE_ADMIN_CB
                )
            ],
            ADD_ADMIN: [
                MessageHandler(
                    filters=Filters.all,
                    callback=add_admin
                )
            ],
            ADD_ADMIN_SUDO: [
                MessageHandler(
                    filters=Filters.all,
                    callback=add_admin_sudo
                )
            ],
            REMOVE_ADMIN: [
                MessageHandler(
                    filters=Filters.all,
                    callback=remove_admin
                )
            ]
        },
        fallbacks=[cancel_handler],
        name='edit_admins_handler'
    )

    menu_handler = CommandHandler('menu', menu)
    text_message_handler = MessageHandler(Filters.text & (~Filters.command), model)

    dispatcher.add_handler(authorization_handler)
    dispatcher.add_handler(location_handler)
    dispatcher.add_handler(chat_with_operator_handler)
    dispatcher.add_handler(edit_admins_handler)
    dispatcher.add_handler(menu_handler)
    dispatcher.add_handler(CallbackQueryHandler(menu_pressed))
    dispatcher.add_handler(cancel_handler)
    dispatcher.add_handler(text_message_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

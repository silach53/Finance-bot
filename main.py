import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

import handler

with open('help.txt', encoding='utf-8') as file:
    help_mes = file.read()


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    update.message.reply_markdown_v2(f'''Hi {user.mention_markdown_v2()}!\
    \nДля получения инструкций наберите: "/help"''')


def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(help_mes)


def message_handler(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id

    # Защита от несанкционированного доступа
    if not (chat_id in handler.spreadsheet_id):
        update.message.reply_text("Access denied\n Your chat_id: ", chat_id)
        return

    mes = update.message.text
    mes_list = mes.split()
    # Стандартизуем получаемое сообщение
    for i in range(len(mes_list)):
        mes_list[i] = mes_list[i].lower().strip()

    operation_type = mes_list[0]

    # По типу операции - обрабатываем пришедшее сообщение
    if operation_type == 'б':
        mess = f"{handler.balance(chat_id)}\n{handler.short_balance(chat_id)}\n{handler.bills_view(chat_id)}"

    elif operation_type == 'частые':
        mess = handler.frequency_analysis(int(mes_list[-1]), chat_id)

    elif operation_type == 'часто':
        mess = handler.frequency_analysis(int(mes_list[-1]), chat_id)

    elif operation_type == 'перевод':
        mess = handler.transfer(mes_list[1:], chat_id)

    elif operation_type == 'баланс':
        mess = handler.balance(chat_id)

    elif operation_type == 'бал':
        mess = handler.short_balance(chat_id)

    elif operation_type == 'счета':
        mess = handler.bills_view(chat_id)

    elif operation_type == 'отмена':
        mess = handler.cancel(chat_id)

    elif operation_type == 'sync':
        mess = handler.sync_with_print()
    else:
        mess = handler.in_out_come(mes_list, chat_id)

    update.message.reply_text(mess)


def main() -> None:
    # При пером запуске сформируем словари
    handler.creat_bills()
    handler.creat_categories()

    # Берем токен из файла, чтобы оно не лежало в коде
    with open('token.txt') as token_file:
        token = token_file.read()
    updater = Updater(token)

    # Запускаем бота
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

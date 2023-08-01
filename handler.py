import httplib2
import googleapiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Сохранено в кеш
id_s = [464517799, 987893288]
bills = {464517799: {}, 987893288: {}}
bills_cer = {464517799: {}, 987893288: {}}
categories = {464517799: {}, 987893288: {}}
categories_income = {464517799: {}, 987893288: {}}
last = {'Расходы': 'B1', 'Доходы': 'B2', 'Категории': 'B3', 'Счета': 'B4', 'Technical': 'B10'}

# Сопоставление пользователя по chat_id его таблице
spreadsheet_id = {464517799: '1jBf4mwvzHqzvZRNWhUwRgm3ghF0M6_FzzLDfsfTkFGg',
                  987893288: '1HAwjdfmZpdGSXBU8kUvCZDhxgkMpuiJ3bwtrl2GLJPI'}

# Вклюнаем google api
CREDENTIALS_FILE = 'creds.json'
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    CREDENTIALS_FILE,
    ['https://www.googleapis.com/auth/spreadsheets',
     'https://www.googleapis.com/auth/drive'])

httpAuth = credentials.authorize(httplib2.Http())
service = googleapiclient.discovery.build('sheets', 'v4', http=httpAuth)
TZ = 'Europe/Moscow'


# Функция узнающая количество строк в конкретной таблице
def last_on_page(gid, chat_id):
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id[chat_id],
        range=f"Technical!{last[gid]}",
        majorDimension='ROWS'
    ).execute()

    return values['values'][0][0]


# Берет нужную сумму из технической таблицы - нужно, тк мы не хотим менять код,
# чтобы выводить другие комбинации счетов
def sum_of(n, chat_id):
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id[chat_id],
        range=f"Technical!B{n}",
        majorDimension='ROWS'
    ).execute()

    return values['values'][0][0]


# Для каждого пользователя побегаем - читаем счета и обновляем их в словарях
def creat_bills():
    for chat_id in id_s:

        values = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id[chat_id],
            range=f"Счета!C2:D{last_on_page('Счета', chat_id)}",
            majorDimension='ROWS'
        ).execute()

        cer = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id[chat_id],
            range=f"Счета!K2:K{last_on_page('Счета', chat_id)}",
            majorDimension='ROWS'
        ).execute()['values']
        
        bills_list = values['values']
        for i in range(len(bills_list)):
            synonyms = bills_list[i][1].split(',')
            bills[chat_id][bills_list[i][0].lower()] = bills_list[i][0]

            for x in synonyms:
                bills[chat_id][x.strip().lower()] = bills_list[i][0]

            bills_cer[chat_id][bills_list[i][0]] = cer[i][0]


# Для каждого пользователя побегаем - читаем категории и обновляем их в словарях
def creat_categories():
    for chat_id in id_s:

        values = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id[chat_id],
            range=f"Категории!C2:E{last_on_page('Категории', chat_id)}",
            majorDimension='ROWS'
        ).execute()

        categories_list = values['values']
        for i in range(len(categories_list)):
            synonyms = categories_list[i][2].split(',')
            categories[chat_id][categories_list[i][1].lower()] = categories_list[i][1]

            for x in synonyms:
                categories[chat_id][x.strip().lower()] = categories_list[i][1]

            categories_income[chat_id][categories_list[i][1]] = categories_list[i][0]


# Если пользователь изминил синонимы - надо обновить их в словорях
def sync():
    creat_bills()
    creat_categories()


# Нужная для удобного вызова из message_handler
def sync_with_print():
    sync()
    return 'Синхронизировано'


# Нужная для стандартизации времени в таблице
def time_string():
    now = datetime.now()
    return f"{str(now.day)}.{str(now.month)}.{str(now.year)} {str(now.hour)}:" \
           f"{str(now.minute)}:{str(now.second)}"


# Заисывает в нужную таблицу доходы и рассходы
def write(where, what, chat_id):
    last_row = int(last_on_page(where, chat_id)) + 1

    # Преполагаем, что where = 'Расходы'
    last_col = 'G'

    if where == 'Доходы':
        last_col = 'F'

    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id[chat_id],
        body={
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{where}!A{last_row}:{last_col}{last_row}",
                 "majorDimension": "ROWS",
                 "values": [what]}
            ]
        }
    ).execute()


# Переводит лист в строчку
def end_of_list_to_str(array):
    ans = ""
    for x in array:
        ans += x + " "
    return ans


# Узнает баланс конкретного пользователя по всем считам
def balance(chat_id):
    # вдруг, пользователь что то поменял - надо синхронизировать
    sync()
    # Читаем значения счетов
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id[chat_id],
        range=f"Счета!C2:F{last_on_page('Счета', chat_id)}",
        majorDimension='ROWS'
    ).execute()['values']

    # Создаем сточку из счетов - для вывода
    ans = ""
    for x in values:
        ans += (x[0] + " " + x[-1] + " " + bills_cer[chat_id][x[0]] + "\n")
    ans += "Всего денег: " + sum_of(7, chat_id) + " ₽\n"
    return ans


# Из другой части таблицы, выводим желаемые счета
def short_balance(chat_id):
    ans = ""

    # Узнаем до какой сточки читать
    last_in_short = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id[chat_id],
        range=f"Technical!E1",
        majorDimension='ROWS'
    ).execute()['values'][0][0]

    # читаем счета
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id[chat_id],
        range=f"Technical!C2:E{last_in_short}",
        majorDimension='ROWS'
    ).execute()['values']

    # формируем сообщение
    for x in values:
        ans += x[0] + " " + x[1] + x[2] + "\n"
    return ans


'''Аналогичная короткому выводу - выводит часть таблицы в которой "счет" - это сумма счетов
функция нужна если хочется сравнить цифры в приложении банка - с тем. что написано в таблице
'''


def bills_view(chat_id):
    ans = ""

    last_in_bills = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id[chat_id],
        range=f"Technical!H1",
        majorDimension='ROWS'
    ).execute()['values'][0][0]
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id[chat_id],
        range=f"Technical!F2:H{last_in_bills}",
        majorDimension='ROWS'
    ).execute()['values']
    for x in values:
        ans += x[0] + " " + x[1] + x[2] + "\n"
    return ans


# Просто вписывает пустоту на место удаляемых транзакций
def erase(what, last_row, chat_id):
    we = ["", "", "", "", "", ""]
    if what == "Расходы":
        we.append("")
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id[chat_id],
        body={
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{what}!A{last_row}:G{last_row}",
                 "majorDimension": "ROWS",
                 "values": [we]}
            ]
        }
    ).execute()


# При ошибочном вводе надо удалить самые последнюю записанную транзакцию
def cancel(chat_id):
    last_1 = last_on_page('Расходы', chat_id)
    last_2 = last_on_page('Доходы', chat_id)

    # Случай кода транзакций нет
    if last_1 == "1" and last_2 == "1":
        return "Отменено"
    # В доходах пусто - удаляем из расходов
    if last_2 == "1":
        erase("Расходы", last_1, chat_id)
        return "Отменено"
    # В расходах пусто - удаляем из доходов
    if last_1 == "1":
        erase("Доходы", last_2, chat_id)
        return "Отменено"

    # смотрим дату и время последних строк
    values_1 = datetime.strptime(service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id[chat_id],
        range=f"Расходы!A{last_1}",
        majorDimension='ROWS'
    ).execute()['values'][0][0], "%d.%m.%Y %H:%M:%S")

    values_2 = datetime.strptime(service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id[chat_id],
        range=f"Доходы!A{last_2}",
        majorDimension='ROWS'
    ).execute()['values'][0][0], "%d.%m.%Y %H:%M:%S")

    # Сравниваем время
    if values_1 > values_2:

        # Если это расходы: проверим - вдруг это был перевод удалим две строки
        type_of_deletable = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id[chat_id],
            range=f"Расходы!C{last_1}",
            majorDimension='ROWS'
        ).execute()['values'][0][0]

        erase("Расходы", last_1, chat_id)
        if type_of_deletable == "Перевод":
            erase("Расходы", int(last_1) - 1, chat_id)

    else:
        erase("Доходы", last_2, chat_id)
    return "Отменено"


# Обрабатывает записи транзации расходов и доходов
def in_out_come(mes_list, chat_id):
    bil = ""
    flag = ""
    if not (mes_list[0] in bills[chat_id]):
        flag = "Счет не распознан. Операция будет произведена с основным счетом\n"
        # Читаем счета и находим основной счет
        main = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id[chat_id],
            range=f"Счета!B2:C{last_on_page('Счета', chat_id)}",
            majorDimension='ROWS'
        ).execute()['values']
        for x in main:
            # проверяем столбец в котом записано, основной он или нет
            if x[0] == '1':
                bil = x[1]
                mes_list[0] = x[1].lower()
    else:
        bil = bills[chat_id][mes_list[0]]
    # Генерируем сточку которая будет записана в таблицу - временно сохранив ее в список
    what = [time_string(), bil]

    if mes_list[1] in categories[chat_id]:
        cat = categories[chat_id][mes_list[1]]
    else:
        cat = 'Нераспознанное'
    what.append(cat)
    what.append(mes_list[2].replace('.', ','))
    what.append(end_of_list_to_str(mes_list[3:]))
    what.append(bills_cer[chat_id][bil])
    # Распределяем категории - между доходом и расходом
    if cat in categories_income[chat_id]:
        cat_i = categories_income[chat_id][cat]
    else:
        # если не нашлось - пусть будет не расспознанный расход
        cat_i = "0"

    # Записываем в таблицу и возвращаем сообщение об успехе
    if cat_i == '0':
        what.append('Расходы')
        write('Расходы', what, chat_id)
        return (flag + f"Записан расход {mes_list[2].replace('.', ',')}"
                       f"{bills_cer[chat_id][bills[chat_id][mes_list[0]]]}\nКатегории: " + cat + f"\nСо счета: {bil}")
    else:
        write('Доходы', what, chat_id)
        return (flag + f"Записан доход {mes_list[2].replace('.', ',')}"
                       f"{bills_cer[chat_id][bills[chat_id][mes_list[0]]]}\nКатегории: " + cat + f"\nСо счета: {bil}")


# Перевод между счетами
def transfer(mes_list, chat_id):
    # Если пользователь не указал сумму пришедшую на второй счет -будем считать, что это сумма ушедшая с первого
    if len(mes_list) < 4:
        mes_list.append(mes_list[2])

    if not ((mes_list[0] in bills[chat_id]) and (mes_list[1] in bills[chat_id])):
        return "Один из счетов не распознан\nПовторите ввод"

    # По шаблону создаем сточки с нужными типами данных
    what_1 = [time_string(), bills[chat_id][mes_list[0]], 'Перевод', float(mes_list[2].replace(',', '.')),
              end_of_list_to_str(mes_list[4:]), bills_cer[chat_id][bills[chat_id][mes_list[0]]], 'Перевод']

    what_2 = [time_string(), bills[chat_id][mes_list[1]], 'Перевод', -float(mes_list[3].replace(',', '.')),
              end_of_list_to_str(mes_list[4:]), bills_cer[chat_id][bills[chat_id][mes_list[1]]], 'Перевод']

    write('Расходы', what_1, chat_id)
    write('Расходы', what_2, chat_id)
    return f"Перевод с {bills[chat_id][mes_list[0]]} на {bills[chat_id][mes_list[1]]} выполнен"


# Выводит N самых частых комбинаций ввода
def frequency_analysis(n, chat_id):
    di = {}
    # Сохраняем себе все данные расходов
    li = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id[chat_id],
        range=f"Расходы!B2:D{last_on_page('Расходы', chat_id)}",
        majorDimension='ROWS'
    ).execute()['values']
    # делаем частотный анализ через словарь - +1 если встретели комбинацию "счет категория сумма"
    for x in li:
        if (x[0] + ' ' + x[1] + ' ' + x[2]) in di:
            di[x[0] + ' ' + x[1] + ' ' + x[2]] += 1
        else:
            di[x[0] + ' ' + x[1] + ' ' + x[2]] = 1

    # Сохраняем себе все данные доходов
    li = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id[chat_id],
        range=f"Доходы!B2:D{last_on_page('Доходы', chat_id)}",
        majorDimension='ROWS'
    ).execute()['values']

    # делаем частотный анализ через словарь - +1 если встретели комбинацию "счет категория сумма"
    for x in li:
        combination = f"{x[0]} {x[1]} {x[2]}"
        if combination in di:
            di[combination] += 1
        else:
            di[combination] = 1
    # Переводим словарь в лист и соритруем его
    ans = sorted([[di[x], x] for x in di], key=lambda y: -y[0])
    repl = ""
    # формируем ответ из n самый частых
    for i in range(min(len(ans), n)):
        repl += f"{ans[i][1]}: {ans[i][0]}\n"
    return repl

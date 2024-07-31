import base64
import json
import hashlib
import requests
import telebot
import time
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import threading
from pymongo import MongoClient
import schedule
from datetime import datetime, timedelta

API_TOKEN = '7390133664:AAEqsc_1k9fYdTFvK2JjUfRjIa-brxEej0Q'
LIQPAY_PUBLIC_KEY = 'sandbox_i38312250017'  # Test public key
LIQPAY_PRIVATE_KEY = 'sandbox_FRDaasO0MmnhPbbp9U3d8DylKxr6ah8ppwkWKCcY'  # Test private key

bot = telebot.TeleBot(API_TOKEN)

# MongoDB connection
client = MongoClient('mongodb+srv://seksikoleg5:se4HivNRYKdydnzc@cluster0.pdc2rrh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0', 
                     tls=True, tlsAllowInvalidCertificates=True)
db = client['botUsers']
users_collection = db['users']
news_collection = client['test']['news']
members_collection = db['members']

# Администраторы
admins = [635258639]  # Замените на реальные chat_id администраторов

# Состояния
class States:
    WELCOME = "WELCOME"
    CHOOSING_OPTION = "CHOOSING_OPTION"
    CHOOSING_DIRECTION = "CHOOSING_DIRECTION"
    CHOOSING_MEMBERS = "CHOOSING_MEMBERS"
    CHOOSING_FORMAT = "CHOOSING_FORMAT"
    LEAVE_CONTACT = "LEAVE_CONTACT"
    PAYMENT = "PAYMENT"
    ENTERING_NEWS = "ENTERING_NEWS"

# Время ожидания в секундах
WAITING_TIME = 3600*24  # 24 часа
user_states = {}
user_contacts = {}
user_directions = {}
user_formats = {}
user_order_ids = {}
last_interaction_times = {}


# Функция для отправки напоминаний
def send_reminders():
    while True:
        current_time = time.time()
        for chat_id, last_time in last_interaction_times.items():
            if current_time - last_time > WAITING_TIME:
                bot.send_message(chat_id, "Вы еще здесь? Чем я могу помочь?")
                last_interaction_times[chat_id] = current_time  # Обновляем время последнего взаимодействия
        time.sleep(60)  # Проверяем каждые 60 секунд

# Запускаем поток для отправки напоминаний
reminder_thread = threading.Thread(target=send_reminders)
reminder_thread.daemon = True
reminder_thread.start()

# Обновляем время последнего взаимодействия
def update_last_interaction(chat_id):
    last_interaction_times[chat_id] = time.time()
    # Обновляем в MongoDB
    users_collection.update_one(
        {'user_id': chat_id},
        {'$set': {'last_interaction': time.time()}},
        upsert=True
    )

# Приветствие
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_states[message.chat.id] = States.WELCOME
    bot.send_message(message.chat.id, "Привіт! Я чат-бот і асистент Академії Aurum 😊\n\n"
                                  "Мене звуть Aurum bot 🤖\n"
                                  "Я асистент Академії Aurum 🏫\n"
                                  "Я допоможу тобі вибрати потрібне для тебе 🙂\n"
                                  "✨ Довідатися більше про нашу Академію\n"
                                  "📚 Ознайомитися і вибрати потрібний тренінг\n"
                                  "📰 Отримувати свіжі круті новини\n"
                                  "📱 Стежити за нами в соц мережах\n"
                                  "📝 Записатися на тренінг і оплатити курс 💳")


    first_question(message.chat.id)
    update_last_interaction(message.chat.id)

    # Добавляем пользователя в MongoDB с полем payment_status
    users_collection.update_one(
        {'user_id': message.chat.id},
        {'$set': {
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'last_interaction': time.time(),
            'state': States.WELCOME
        }},
        upsert=True
    )
    
@bot.callback_query_handler(func=lambda call: call.data in ["want_to_be_rehabilitologist", "want_to_upgrade_qualification", "want_to_participate_in_events"])
def handle_first_question_response(call):
    chat_id = call.message.chat.id
    response = call.data

    # Запис відповіді в MongoDB
    users_collection.update_one(
        {"user_id": chat_id},
        {"$set": {"first_question": response}},
        upsert=True
    )

    second_question(chat_id)

@bot.callback_query_handler(func=lambda call: call.data in ["offline", "online"])
def handle_second_question_response(call):
    chat_id = call.message.chat.id
    response = call.data

    # Запис відповіді в MongoDB
    users_collection.update_one(
        {"user_id": chat_id},
        {"$set": {"second_question": response}},
        upsert=True
    )

    third_question(chat_id)
    
def first_question(chat_id):
    markups = InlineKeyboardMarkup()
    buttons = [
        InlineKeyboardButton("Хочу стати реабілітологом", callback_data="want_to_be_rehabilitologist"),
        InlineKeyboardButton("Хочу підвищити кваліфікацію ", callback_data="want_to_upgrade_qualification"),
        InlineKeyboardButton("Хочу брати участі в заходах, які організовує Академія", callback_data="want_to_participate_in_events")
    ]
    markups.add(*buttons)
    bot.send_message(chat_id, "Що саме тебе пов'язує з реабілітацією?", reply_markup=markups)
    
def second_question(chat_id, message_id=None):
    bot.send_message(chat_id, "Дякую за твою відповідь, будеш отримувати круті інсайти на дану тему")
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("Офлайн", callback_data="offline"),
        InlineKeyboardButton("Онлайн", callback_data="online"),
    )
    bot.send_message(chat_id, "Навчання проходить у форматі онлайн і офлайн. Якому ти надаєш перевагу?👇", reply_markup=markup)

def third_question(chat_id, message_id=None):
    bot.send_message(chat_id, "Дякую за твою відповідь, будеш отримувати круті інсайти на дану тему")
    markups = ReplyKeyboardMarkup(resize_keyboard=True)
    button_main_menu = KeyboardButton("Головне меню")
    button_contact = KeyboardButton("Надіслати мій контакт", request_contact=True)
    markups.add(button_main_menu, button_contact)
    markups.row_width = 2
    bot.send_message(chat_id, "Наші менеджери можуть підказати і розповісти про всі подробиці навчання. Ти можеш залишити номер і з тобою зв'яжуться.")
    bot.send_message(chat_id, "Якщо ти засекречений агент) то можеш сам переглянути розклад на нашому сайті у вкладці Розклад ", reply_markup=markups)

@bot.message_handler(func=lambda message: message.text == "Головне меню")
def handle_main_menu_request(message):
    send_main_menu(message.chat.id)
    
@bot.message_handler(func=lambda message: message.text == "Навчання")
def handle_main_menu_request(message):
    learn_plan_menu(message.chat.id)
    
@bot.message_handler(func=lambda message: message.text == "Про нас")
def handle_main_menu_request(message):
    aboutUs_menu(message.chat.id)
    
@bot.message_handler(func=lambda message: message.text == "Наші контакти")
def handle_main_menu_request(message):
    our_contacts(message.chat.id)
    
@bot.message_handler(func=lambda message: message.text == "Детальніше про нас")
def handle_main_menu_request(message):
    detail_aboutUs(message.chat.id)

@bot.message_handler(func=lambda message: message.text == "Про наше навчання")
def handle_main_menu_request(message):
    about_learning(message.chat.id)
    
@bot.message_handler(func=lambda message: message.text == "Засновники")
def handle_main_menu_request(message):
    about_founders(message.chat.id)
    
@bot.message_handler(func=lambda message: message.text == "Чому ми?")
def handle_main_menu_request(message):
    why_we(message.chat.id)
    
@bot.message_handler(func=lambda message: message.text == "💪Спікери")
def handle_main_menu_request(message):
    members_menu(message.chat.id)
    
@bot.message_handler(func=lambda message: message.text == "Повернутися до меню")
def handle_main_menu_request(message):
    #members_menu(message.chat.id)
    send_main_menu(message.chat.id)
    
@bot.message_handler(func=lambda message: message.text == "Модуль 1")
def handle_main_menu_request(message):
    first_module(message.chat.id)
    
@bot.message_handler(func=lambda message: message.text == "Модуль 2")
def handle_main_menu_request(message):
    second_module(message.chat.id)
    
@bot.message_handler(func=lambda message: message.text == "Модуль 3")
def handle_main_menu_request(message):
    third_module(message.chat.id)
    
@bot.message_handler(func=lambda message: message.text == "Актуальні заходи")
def handle_main_menu_request(message):
    actual_events(message.chat.id)
    
@bot.message_handler(func=lambda message: message.text == "Коли?")
def handle_main_menu_request(message):
    when_event(message.chat.id)

@bot.message_handler(func=lambda message: message.text == "Де?")
def handle_main_menu_request(message):
    where_event(message.chat.id)

@bot.message_handler(func=lambda message: message.text == "Вартість")
def handle_main_menu_request(message):
    cost_event(message.chat.id)

@bot.message_handler(func=lambda message: message.text == "План конгресу")
def handle_main_menu_request(message):
    plan_event(message.chat.id)
    
@bot.message_handler(func=lambda message: message.text == "Розклад семінарів")
def handle_main_menu_request(message):
    schelude_seminars(message.chat.id) 

def send_main_menu(chat_id, message_id=None):
    markup = InlineKeyboardMarkup()
    markups = ReplyKeyboardMarkup(resize_keyboard=True)
    button_contact = KeyboardButton("Надіслати мій контакт", request_contact=True)
    button_aboutUs = KeyboardButton("Про нас")
    button_contacts = KeyboardButton("Наші контакти")
    button_members_menu = KeyboardButton("💪Спікери")
    button_training_menu = KeyboardButton("Навчання")
    button_events = KeyboardButton("Актуальні заходи")
    button_schedule = KeyboardButton("Розклад семінарів")
    markups.add(button_members_menu, button_training_menu, button_aboutUs, button_contacts, button_contact, button_events, button_schedule)
    bot.send_message(chat_id, "Обирай кнопками, що цікавить👇", reply_markup=markups)
    markup.row_width = 1
    buttons = [
    #    InlineKeyboardButton("Узнать больше про нашу Академию", callback_data="learn_about_academy"),
     #   InlineKeyboardButton("Получать свежие крутые новости", callback_data="get_news"),
      #  InlineKeyboardButton("Следить за нами в соц сетях", callback_data="follow_us")
    ]

    # Добавляем кнопку "Ввести новость" только для администраторов
    if chat_id in admins:
        buttons.append(InlineKeyboardButton("Ввести новость", callback_data="enter_news"))

    # Добавляем кнопку "Перейти к оплате", если тренинг был выбран, но не оплачен
   # if user_states.get(chat_id) == States.PAYMENT:
       # buttons.append(InlineKeyboardButton("Перейти к оплате", callback_data="payment"))

    markup.add(*buttons)
    
    if message_id:
        bot.edit_message_text("🤗Я допоможу тобі вибрати потрібне:", chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, "🤗Я допоможу тобі вибрати потрібне:", reply_markup=markup)

    update_last_interaction(chat_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_welcome_response(call):
    update_last_interaction(call.message.chat.id)
    if call.data == "learn_about_academy":
        bot.edit_message_text("Наша Академия предлагает...", call.message.chat.id, call.message.message_id)
    elif call.data == "choose_training":
        choose_training(call.message.chat.id, call.message.message_id)
    elif call.data == "want_to_upgrade_qualification":
        second_question(call.message.chat.id, call.message.message_id)
    elif call.data == "want_to_be_rehabilitologist":
        second_question(call.message.chat.id, call.message.message_id)
    elif call.data == "want_to_participate_in_events":
        second_question(call.message.chat.id, call.message.message_id)
    elif call.data == ("offline"):
        third_question(call.message.chat.id, call.message.message_id)
    elif call.data == ("online"):
        third_question(call.message.chat.id, call.message.message_id)
    elif call.data == ("members"):
        members_menu(call.message.chat.id, call.message.message_id)
    elif call.data == ("aboutUs"):
        aboutUs_menu(call.message.chat.id, call.message.message_id)
    elif call.data == "get_news":
        bot.edit_message_text("Вы будете получать свежие новости...", call.message.chat.id, call.message.message_id)
    elif call.data == "follow_us":
        bot.edit_message_text("Вы можете следить за нами в соц сетях...", call.message.chat.id, call.message.message_id)
    elif call.data == "enter_news":
        enter_news(call.message.chat.id, call.message.message_id)
    elif call.data.startswith("direction_"):
        handle_direction_response(call)
    elif call.data.startswith("format_"):
        handle_format_response(call)
    elif call.data == "main_menu":
        send_main_menu(call.message.chat.id, call.message.message_id)
    elif call.data == "leave_contact":
        request_contact(call.message)
    elif call.data == "use_current_contact":
        user_states[call.message.chat.id] = States.PAYMENT
        create_liqpay_invoice(call.message)
    elif call.data == "check_payment":
        check_payment_status(call.message)
    elif call.data == "payment":
        create_liqpay_invoice(call.message)
    elif call.data.startswith("member_"):
        handle_member_response(call)
        
def our_contacts(chat_id, message_id=None):
    markup = InlineKeyboardMarkup()
    buttons = [
        InlineKeyboardButton("Інстаграм📸", url="https://www.instagram.com/aurumfitnessclinic?igsh=cmcyZXVmZjJ3dTlx"),
        InlineKeyboardButton("Наш сайт🌐", url="ya-reabilitolog.com.ua")
    ]
    markup.add(*buttons)
    
    bot.send_message(chat_id, """📞 Номери телефону: 
                     - +380443338596
                     - +380687123141
                     """)
    bot.send_message(chat_id, "📧 EMAIL: clinicaurum@gmail.com", reply_markup=markup)
    

def aboutUs_menu(chat_id, message_id=None):
    markups = ReplyKeyboardMarkup(resize_keyboard=True)
    bot.send_message(chat_id, "«Aurum» - тренінговий центр з навчання тренерів і керівників у сфері фітнесу.")
    bot.send_message(chat_id, "Допомагаємо тренерам і менеджерам в фітнес-індустрії підвищувати професійні навички для оздоровлення нації і залучення українців до спорту.")
    button_detail = KeyboardButton("Детальніше про нас")
    button_founders = KeyboardButton("Засновники")
    button_learning = KeyboardButton("Про наше навчання")
    button_why = KeyboardButton("Чому ми?") 
    button_main_menu = KeyboardButton("Головне меню")
    markups.add(button_detail, button_founders, button_learning, button_why, button_main_menu)
    bot.send_message(chat_id, "Що ще тобі розповісти?👇", reply_markup=markups)
    
def detail_aboutUs(chat_id, message_id=None):
    bot.send_message(chat_id, """
Ми, Академія реабілітації Aurum Fitness Clinic, уже впродовж 7 років допомагаємо людям ставати здоровішими та сильнішими, використовуючи індивідуальний підхід до клієнта 🏥 - а це складання індивідуального плану реабілітації, що охоплює:

- 👨‍⚕️ лікарський контроль
- 💪 заняття з фізичної терапії
- 🔗 підвісні системи
- 🛠 інноваційне обладнання з механотерапії
- ⚡ фізіотерапію

Великий досвід маємо допомагаючи військовим. На практиці та досвіді спеціалістів, що сягає понад 15 років, ми створили курс, який допоможе діючим спеціалістам з реабілітації, реабілітологу-початківцю, лікарю або фахівцю, який хоче підвищити кваліфікацію, пройти з нами весь шлях від зустрічі клієнта до його відновлення 🏆.
""")
    bot.send_message(chat_id, "Що ще тобі розповісти?👇")

def about_learning(chat_id, message_id=None):
    bot.send_message(chat_id, """
З чого складається наше навчання? 📚

Загальний курс складається з 3-х модулів. Кожен модуль буде розділений на декілька етапів. 

🔧 Практична частина - всі матеріали будуть відпрацьовані на новітньому обладнанні.

📑 Презентаційні матеріали - доступ до матеріалів та чат Боту за напрямом «Академія Реабілітації».

🎥 Відео-супровід - всі матеріали будуть представлені у форматі відео для зручного використання і практичної реалізації.

📝 Іспит буде після кожного напрямку.
""")

    bot.send_message(chat_id, "Що ще тобі розповісти?👇")

def about_founders(chat_id, message_id=None):
    member_info = get_member_info('samsyi')
    response_text = """
**САМСІЙ РОМАН** 🎓

● Член правління Всеукраїнської Асоціації Фізичної та Медичної Реабілітації;
● Керівник експертної групи з впровадження та використання інноваційного та високотехнологічного обладнання в сфері охорони здоров’я.

Я починав зі спортивної кар’єри, займався легкою атлетикою, метанням молота, списа. 🏅 Бачив і перемоги, і програші. З часом через травми постало питання вибору майбутнього шляху.

Я вже навчався в університеті фізичної культури на факультеті реабілітаційного напрямку. Починав з олімпійського спорту, потім – рекреація і фітнес, і закінчив реабілітаційним напрямком. 🏋️‍♂️

З 18 років працював з пацієнтами неврологічного напрямку в домашніх умовах. 🏠
"""

    response_text_part2 = """
В ХХХХ році мене запросили в мережу клубів «СпортЛенд», де я сформував школу реабілітації та фітнесу. Став основним методистом мережі та управлінцем в трьох клубах. Запровадив систему консультацій перед тренуваннями, завдяки чому продаж персональних занять збільшився на 60%. 📈

Після цього я перейшов на позицію головного менеджера по роботі з фітнес-напрямками в клубі EnerGym, де з 0 налагодив роботу команди. 💪

В 2015 році я поїхав до Великобританії, де навчався менеджменту та організації реабілітаційних оздоровчих комплексів. 🇬🇧

Після повернення відкрив першу і єдину фітнес-клініку Aurum, де зібрали обладнання та методики роботи з клієнтами, яким немає аналогів в Україні. 🏥

Зараз я виводжу діяльність на більш глобальний рівень та займаюсь маршрутизацією реабілітаційних програм для військових разом з Всеукраїнською Асоціацією Фізичної та Медичної Реабілітації. 🪖

Маючи ці знання та досвід, зі своєю командою ми створили Курс “я Фізіотерапевт”, який допоможе спеціалісту набути знань та довести клієнта з першої зустрічі до повного відновлення. 📚
"""
    member_info = get_member_info("samsyi")
    if member_info:
        if 'imgUrl' in member_info:
            bot.send_photo(chat_id, member_info['imgUrl'], caption=response_text)
            bot.send_message(chat_id, response_text_part2)
            bot.send_message(chat_id, "Що ще тобі розповісти?👇")
        else:
            bot.send_message(chat_id, response_text)
    else:
        bot.send_message(chat_id, "Информация о члене команды не найдена.")

def why_we(chat_id, message_id=None):
    bot.send_message(chat_id, """
Наша авторська методика заснована на доказових методиках, міжнародних протоколах та особистій практиці дієвих кейсів нашого досвіду! 🌍📊

Ви зможете підвищити свою цінність як спеціаліста, бути ефективнішим для свого пацієнта, розширити спектр послуг пройшовши наше навчання. 📈💪

Завдяки знанням, отриманим у нас - ви зможете провести пацієнта від першої зустрічі до повного відновлення. 🏥🔄

Ви зможете збільшити кількість своїх потенційних гостей. 👥🔝

Структуруєте послідовність дій з пацієнтом, та навички взаємодії в команді. 🗂️🤝

Оволодієте новими програмами, які допоможуть вийти вам на новий рівень у реабілітації. 🚀📚 """)
    bot.send_message(chat_id, "Що ще тобі розповісти?👇")
    
    
def learn_plan_menu(chat_id, message_id=None):
    bot.send_message(chat_id, "Повний курс «Я фізичний терапевт» складається з трьох модулів")
    markups = ReplyKeyboardMarkup(resize_keyboard=True)
    first_module = KeyboardButton("Модуль 1")
    second_module = KeyboardButton("Модуль 2")
    third_module = KeyboardButton("Модуль 3")
    main_menu = KeyboardButton("Головне меню")
    markups.add(first_module, second_module, third_module, main_menu)
    bot.send_message(chat_id, "Дізнатися інформацію та придбати модуль можна нижче👇", reply_markup=markups)

def first_module(chat_id, message_id=None):
    bot.send_message(chat_id, """Модуль 1. 🩺 Діагностичні методи функціонування, котрі спеціаліст може використовувати без додаткового обладнання.
1. 🦴 Вертебрологічна діагностика. Ортопедична діагностика верхніх та нижніх кінцівок
2. 💆‍♂️ Міофасціальний реліз (МФР) 
3. 🏋️‍♂️ Прикладна кінезіологія
4. 🧘‍♂️ Остеопатичні методи діагностики. Коригуюча практика.""")
    create_liqpay_invoice(chat_id, 'module_1')

def second_module(chat_id, message_id=None):
    bot.send_message(chat_id, """Модуль 2. Фізичні не апаратні методи лікування в реабілітації. Протоколи проведення відновлення, етапи та методики.

1. Levitas, Redcord система підвісних тренажерів 🏋️‍♂️✨
2. Реабілітаційні напрямки масажу, тейпування 💆‍♂️🩹
3. Інструментальна мобілізація м'яких тканин 🔧💪
4. Метод Dry Needling (“сухої” голки) 🪡🔍""")
    create_liqpay_invoice(chat_id, 'module_2')

def third_module(chat_id, message_id=None):
    bot.send_message(chat_id, """Модуль 3. Особливості реабілітації на прикладі представленого обладнання, діючих методів та сучасних можливостей.

1. Додаткове обладнання. Покращення отриманих знань на практиці та реалізація в компонуванні на прикладі індивідуальних випадків (ортопедія, вертебрологія) 🛠📚
2. Апаратні методи. Практичні навички роботи на фізіотерапевтичному обладнанні 🏥💡 (Магнітотерапія, лазеротерапія; електростимуляція; пресотерапія, ударно-хвильова терапія, локальна діатермія) ⚡️🔬
3. Мобільність та гнучкість для пацієнтів різних категорій (підгострий період реабілітації) 🤸‍♂️🔄
4. Унікальна практика ведення реального пацієнта 🧑‍⚕️📝""")
    create_liqpay_invoice(chat_id, 'module_3')

def members_menu(chat_id, message_id=None):
    user_states[chat_id] = States.CHOOSING_MEMBERS
    markup = InlineKeyboardMarkup()
    markups = ReplyKeyboardMarkup(resize_keyboard=True)
    button_main_menu = KeyboardButton("Головне меню")
    button_members_menu = KeyboardButton("💪Спікери")
    markups.add(button_main_menu, button_members_menu)
    
    markup.row_width = 1
    
    markup.add(
        InlineKeyboardButton("Самсій Роман", callback_data="member_samsyi_roman"),
        InlineKeyboardButton("Подольски Василь", callback_data="member_podolski_vasyl"),
        InlineKeyboardButton("Литвинчук Михайло", callback_data="member_litvinchuk_myhail"),
        InlineKeyboardButton("Кожевников Данил", callback_data="member_kozh_danyl"),
        
    )
    bot.send_message(chat_id, "Хто з методистів тебе цікавить👇", reply_markup=markup)
    #bot.edit_message_text("👇Хто з методистів тебе цікавить", chat_id, message_id, reply_markup=markup)
    update_last_interaction(chat_id)

def get_member_info(id_name):
    member_info = members_collection.find_one({'id_name': id_name})
    if member_info:
        return member_info
    return None


def handle_member_response(call):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    button_main_menu = KeyboardButton("Повернутися до меню")
    markup.add(button_main_menu)
    member_id_name = call.data.split("_")[1]
    member_info = get_member_info(member_id_name)
    if member_info:
        response_text = f"{member_info['name']}\n"
        if 'imgUrl' in member_info:
            bot.send_photo(call.message.chat.id, member_info['imgUrl'], caption=response_text)
            bot.send_message(call.message.chat.id, member_info['about'], reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, response_text)
    else:
        bot.send_message(call.message.chat.id, "Информация о члене команды не найдена.")

def actual_events(chat_id, message_id=None):
    markups = ReplyKeyboardMarkup(resize_keyboard=True)
    button_date = KeyboardButton("Коли?")
    button_where = KeyboardButton("Де?")
    button_cost = KeyboardButton("Вартість")
    button_plan = KeyboardButton("План конгресу")
    button_main_menu = KeyboardButton("Головне меню")
    markups.add(button_date, button_where, button_cost, button_plan, button_main_menu)
    bot.send_message(chat_id, "3-денний наймасштабніший конгрес з реабілітації", reply_markup=markups)
    bot.send_message(chat_id, "Обирай кнопками, що цікавить👇")

def when_event(chat_id, message_id=None):
    bot.send_message(chat_id, "29-31 серпня")
    
def where_event(chat_id, message_id=None):
    bot.send_message(chat_id, "Aurum Fitness Clinic")
    
def cost_event(chat_id, message_id=None):
    bot.send_message(chat_id, "100 грн")
    
def plan_event(chat_id, message_id=None):
    bot.send_message(chat_id, """Перший день 
11:00 - 15:00
1. ВІЗУАЛЬНА ДІАГНОСТИКА ДЛЯ СКРИНІНГУ М’ЯЗОВОЇ ДИСФУНКЦІЇ ОПОРНО-РУХОВОГО АПАРАТУ:
План + 
(Самсій Подольські )

План + 
Візуальна діагностика для скринінгу мʼязової дисфункції ОДА
-Анамнез, опитування
-Фізикальне і мануальне дослідження
-Лабораторні та інструментальні методи обстеження 
Скарги:
-Повʼязані з травматизацією нервових структур 
- Повʼязані з враженням звʼязкового і суглобового апарата сегментів
-Повʼязані з повною чи частковою компресією судин
Порушення 
- зміни рухового стереотипу
- виявлення заблокованих сегментів і суглобів 
-постави в вертикальній і горизонтальній площині

16:00-19:00
2. Остеопатичний підхід в практиці реабілітолога.
- діагностика
- корегуюча практика внутрішньокісткових дисфункцій.
- ведення пацієнта
Подольскі. (лікар ФРМ)

""")
    bot.send_message(chat_id, """Другий день 

15:00 - 19:00
3. Методики для мобілізації, пасивного та пасивно-активного задіювання, пошкоджених тканин, чи регіону.
Постізометрична релаксація (ПІР) , пропріоцептивна нейром'язова фасилітація ПНФ, міофісціальний реліз. 
Фізіологія впливу на міофібрілярний матрікс і нервову систему; анатомічний атлас ;
""")
    bot.send_message(chat_id, """Третій день 
11:00 - 14:00
3. «Метод сухої голки» Практичне застосування у фізичній терапії.
Кожевніков Данило (фізичний терапевт)

15:00- 17:00
4. Мобілізація мʼяких тканин (блейд). ІММТ – неінвазивна методика, що дозволяє швидко та ефективно опрацювати фасціальні порушення.

17:00 -19:00 Підвісні системи. Практична реалізація найбільш - розповсюджених порушень ортопедичного напряму на прикладі роботи з (поясом нижніх кінцівок, поясу верхніх кінцівок).
""")

def schelude_seminars(chat_id, message_id=None):
    markups = ReplyKeyboardMarkup(resize_keyboard=True)
    
    markups.add(
        KeyboardButton("Січень"),
        KeyboardButton("Лютий"),
        KeyboardButton("Березень"),
        KeyboardButton("Квітень"),
        KeyboardButton("Травень"),
        KeyboardButton("Червень"),
        KeyboardButton("Липень"),
        KeyboardButton("Серпень"),
        KeyboardButton("Вересень"),
        KeyboardButton("Жовтень"),
        KeyboardButton("Листопад"),
        KeyboardButton("Грудень"),
        KeyboardButton("Головне меню")
    )
    bot.send_message(chat_id, "Оберіть місяць👇", reply_markup=markups)
    

def choose_training(chat_id, message_id=None):
    user_states[chat_id] = States.CHOOSING_DIRECTION
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("Физиотерапевт", callback_data="direction_physiotherapist"),
        InlineKeyboardButton("Реабилитолог", callback_data="direction_rehabilitologist"),
        InlineKeyboardButton("Спортивная медицина", callback_data="direction_sports_medicine"),
    )
    bot.send_message(chat_id, "Обирай кнопками, що цікавить👇", reply_markup=markup)
    


def handle_direction_response(call):
    direction = call.data
    user_directions[call.message.chat.id] = direction
    user_states[call.message.chat.id] = States.CHOOSING_FORMAT
    bot.edit_message_text("Спасибо за твой выбор, будешь получать крутые инсайты на данную тему.", call.message.chat.id, call.message.message_id)
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("Онлайн", callback_data="format_online"),
        InlineKeyboardButton("Оффлайн", callback_data="format_offline"),
        InlineKeyboardButton("Назад", callback_data="choose_training"),
    )
    bot.send_message(call.message.chat.id, "Обучение проходит в формате онлайн и оффлайн. Какой ты предпочитаешь?", reply_markup=markup)
    update_last_interaction(call.message.chat.id)

def handle_format_response(call):
    format = call.data
    user_formats[call.message.chat.id] = format
    user_states[call.message.chat.id] = States.LEAVE_CONTACT
    bot.edit_message_text("Теперь вам нужно оставить контакт.", call.message.chat.id, call.message.message_id)
    request_contact(call.message)
    update_last_interaction(call.message.chat.id)

def request_contact(message):
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    button_contact = KeyboardButton("Надіслати мій контакт", request_contact=True)
    button_main_menu = KeyboardButton("Головне меню")
    markup.add(button_contact, button_main_menu)
    bot.send_message(message.chat.id, "Пожалуйста, отправьте ваш контакт или введите его вручную.", reply_markup=markup)
    update_last_interaction(message.chat.id)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if message.contact is not None:
        user_contacts[message.chat.id] = message.contact.phone_number
        bot.send_message(message.chat.id, "Дякую! Наші менеджери незабаром зв'яжуться з Вами.")
        user_states[message.chat.id] = States.PAYMENT
        users_collection.update_one(
            {'user_id': message.chat.id},
            {'$set': {'contact': message.contact.phone_number}},
            upsert=True
        )
        #create_liqpay_invoice(message)
        update_last_interaction(message.chat.id)

def create_liqpay_invoice(chat_id, module_name):
    amount = 50.00  # Сумма платежа
    currency = 'UAH'
    description = f'Оплата за {module_name}'
    order_id = f'order_{chat_id}_{int(time.time())}'
    user_order_ids[chat_id] = order_id

    liqpay_data = {
        'public_key': LIQPAY_PUBLIC_KEY,
        'version': '3',
        'action': 'pay',
        'amount': amount,
        'currency': currency,
        'description': description,
        'order_id': order_id,
        'sandbox': 1  # Удалите или замените на 0 для реальных платежей
    }
    liqpay_data_str = base64.b64encode(json.dumps(liqpay_data).encode('utf-8')).decode('utf-8')
    liqpay_signature = base64.b64encode(hashlib.sha1(f'{LIQPAY_PRIVATE_KEY}{liqpay_data_str}{LIQPAY_PRIVATE_KEY}'.encode('utf-8')).digest()).decode('utf-8')

    payment_url = f'https://www.liqpay.ua/api/3/checkout?data={liqpay_data_str}&signature={liqpay_signature}'
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Сплатити", url=payment_url),
        types.InlineKeyboardButton("Підтвердити оплату", callback_data="check_payment"),
    )

    user_directions[chat_id] = module_name
    bot.send_message(chat_id, f"Будь ласка, перейдіть за посиланням для оплати. Після оплати потрібно її підтвердити (через 10-15 секунд)", reply_markup=markup)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    handle_successful_payment(message.chat.id)
    update_last_interaction(message.chat.id)

def check_payment_status(message):
    order_id = user_order_ids.get(message.chat.id)
    if not order_id:
        bot.send_message(message.chat.id, "Заказ не найден.")
        return
    
    url = 'https://www.liqpay.ua/api/request'
    liqpay_data = {
        'public_key': LIQPAY_PUBLIC_KEY,
        'version': '3',
        'action': 'status',
        'order_id': order_id
    }
    liqpay_data_str = base64.b64encode(json.dumps(liqpay_data).encode('utf-8')).decode('utf-8')
    liqpay_signature = base64.b64encode(hashlib.sha1(f'{LIQPAY_PRIVATE_KEY}{liqpay_data_str}{LIQPAY_PRIVATE_KEY}'.encode('utf-8')).digest()).decode('utf-8')

    response = requests.post(url, data={'data': liqpay_data_str, 'signature': liqpay_signature})
    response_data = response.json()

    if response_data['status'] == 'sandbox':
        handle_successful_payment(message.chat.id)
    else:
        bot.send_message(message.chat.id, "Платеж не был завершен. Пожалуйста, попробуйте еще раз.")

def handle_successful_payment(chat_id):
    module_name = user_directions.get(chat_id, "выбранный тренинг")
    bot.send_message(chat_id, f"Дякую за оплату! Наші менеджери зв'яжуться з вами для подальших інструкцій.")
    
    # Обновляем информацию об оплате в MongoDB
    users_collection.update_one(
        {'user_id': chat_id},
        {'$set': {
            'state': States.WELCOME,
            f'payment_status_{module_name}': 'Paid'
        }},
        upsert=True
    )


def monitor_and_send_urgent_news():
    last_checked = datetime.now()
    while True:
        urgent_news = news_collection.find({'isUrgent': True, 'sent': {'$ne': True}})
        for news in urgent_news:
            send_urgent_news_to_users(news)
            # Обновляем новость как отправленную
            news_collection.update_one({'_id': news['_id']}, {'$set': {'sent': True}})
        last_checked = datetime.now()
        time.sleep(1)

# Функция для отправки срочных новостей всем пользователям
def send_urgent_news_to_users(news):
    users = users_collection.find({})
    for user in users:
        if 'imageUrl' in news:
            bot.send_photo(user['user_id'], news['imageUrl'], caption=f"{news['title']}\n{news['content']}")
        else:
            bot.send_message(user['user_id'], f"{news['title']}\n{news['content']}/n{news['imageUrl']}")


# Функция для отправки не срочных новостей
def send_non_urgent_news():
    today = datetime.combine(datetime.now().date(), datetime_time()) # Get the current date in UTC
    non_urgent_news = news_collection.find({
        'isUrgent': False,
        'sendDate': {'$lte': today},
        'sent': {'$ne': True}
    })
    for news in non_urgent_news:
        send_non_urgent_news_to_users(news)
        # Update the news as sent
        news_collection.update_one({'_id': news['_id']}, {'$set': {'sent': True}})

def send_non_urgent_news_to_users(news):
    users = users_collection.find({})
    for user in users:
        if 'imageUrl' in news:
            bot.send_photo(user['user_id'], news['imageUrl'], caption=f"НОВОСТЬ: {news['title']}\n{news['content']}")
        else:
            bot.send_message(user['user_id'], f"НОВОСТЬ: {news['title']}\n{news['content']}")

# Планировщик для отправки не срочных новостей
schedule.every().day.at("18:20").do(send_non_urgent_news)

# Ввод новостей
def enter_news(chat_id, message_id):
    if chat_id not in admins:
        bot.send_message(chat_id, "Извините, только администраторы могут добавлять новости.")
        return

    user_states[chat_id] = States.ENTERING_NEWS
    bot.edit_message_text("Пожалуйста, введите текст новости, которую вы хотите отправить:", chat_id, message_id)
    update_last_interaction(chat_id)

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == States.ENTERING_NEWS)
def handle_entering_news(message):
    if message.chat.id not in admins:
        bot.send_message(message.chat.id, "Извините, только администраторы могут добавлять новости.")
        return

    news_text = message.text
    news_collection.insert_one({
        'text': news_text,
        'created_at': datetime.now()
    })
    bot.send_message(message.chat.id, "Новость успешно добавлена!")
    send_main_menu(message.chat.id)

    # Рассылка новости всем пользователям
    users = users_collection.find()
    for user in users:
        bot.send_message(user['user_id'], f"Свежая новость: {news_text}")

    update_last_interaction(message.chat.id)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

def send_daily_news():
    # Получаем новости за последние 24 часа
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    recent_news = news_collection.find({'created_at': {'$gte': yesterday}})
    
    for news in recent_news:
        news_text = news['text']
        users = users_collection.find()
        for user in users:
            bot.send_message(user['user_id'], f"Свежая новость: {news_text}")

# Запуск планировщика
scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()

urgent_news_thread = threading.Thread(target=monitor_and_send_urgent_news)
urgent_news_thread.daemon = True
urgent_news_thread.start()

bot.polling(none_stop=True)

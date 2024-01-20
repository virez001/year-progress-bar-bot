import os
import requests
from datetime import datetime
from PIL import Image, ImageDraw
from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import pytz

# Token de acceso del bot de Telegram
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Lista de usuarios y sus horas de envío programadas
user_scheduled_times = {}

def start(update, context):
    chat_id = update.message.chat_id
    context.user_data['chat_id'] = chat_id

    user_scheduled_times[chat_id] = {'time': datetime.now(pytz.timezone('America/New_York')).replace(hour=12, minute=0, second=0, microsecond=0),
                                     'image_sent': False}

    update.message.reply_text(f"Bienvenido al bot. Por defecto la hora de envío es {user_scheduled_times[chat_id]['time'].strftime('%H:%M')}. Use /edit para editar la hora.")

def edit(update, context):
    chat_id = update.message.chat_id
    if chat_id in user_scheduled_times:
        update.message.reply_text("Ingresa la nueva hora en formato HH:MM.")
        context.user_data['edit_mode'] = True
    else:
        update.message.reply_text("Primero utiliza /start para registrarte en el bot.")

def set_new_time(update, context):
    chat_id = update.message.chat_id
    user_message = update.message.text

    try:
        new_hour, new_minute = map(int, user_message.split(':'))
        if 0 <= new_hour < 24 and 0 <= new_minute < 60:
            if chat_id in user_scheduled_times and context.user_data.get('edit_mode', False):
                user_scheduled_times[chat_id]['time'] = datetime.now(pytz.timezone('America/New_York')).replace(
                    hour=new_hour, minute=new_minute, second=0, microsecond=0)
                update.message.reply_text(f"Hora de envío actualizada a las {user_scheduled_times[chat_id]['time'].strftime('%H:%M')}.")
                context.user_data['edit_mode'] = False
            else:
                update.message.reply_text("Primero utiliza /start para registrarte en el bot.")
        else:
            update.message.reply_text("Por favor, ingresa una hora y minutos válidos.")
    except ValueError:
        update.message.reply_text("Por favor, ingresa la hora en el formato HH:MM.")

def send_image(chat_id):
    file_path = os.path.join(os.path.dirname(__file__), 'progress_bar.jpg')
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    files = {'photo': open(file_path, 'rb')}
    data = {'chat_id': chat_id}

    response = requests.post(url, files=files, data=data)

    print(f"Respuesta de Telegram API para el chat ID {chat_id}:", response.text)

def send_progress_bar_image():
    current_time = datetime.now(pytz.timezone('America/New_York'))
    for chat_id, data in user_scheduled_times.items():
        if current_time.hour == data['time'].hour and current_time.minute == data['time'].minute:
            if not data['image_sent']:
                print(f"Enviando imagen a {chat_id}...")
                create_progress_bar_image()
                send_image(chat_id)
                user_scheduled_times[chat_id]['image_sent'] = True
            else:
                print(f"Imagen ya enviada a {chat_id} en esta ejecución.")
        else:
            user_scheduled_times[chat_id]['image_sent'] = False
            print(f"No es hora de enviar la imagen a {chat_id}.")

def create_progress_bar_image():
    current_date = datetime.now(pytz.timezone('America/New_York'))
    start_of_year = datetime(current_date.year, 1, 1, tzinfo=pytz.timezone('America/New_York'))
    end_of_year = datetime(current_date.year + 1, 1, 1, tzinfo=pytz.timezone('America/New_York'))

    progress_percentage = (current_date - start_of_year) / (end_of_year - start_of_year) * 100

    image = Image.new("RGB", (400, 40), "white")
    draw = ImageDraw.Draw(image)

    draw.rectangle([0, 0, progress_percentage * 4, 40], fill='green')

    draw.text((10, 10), f"EL   PROGRESO   DE   {current_date.year}   ES   DE   {progress_percentage:.2f} %", fill='black')


    image.save("progress_bar.jpg")  # Cambia la ruta del archivo si es necesario

def main():
    updater = Updater(token=TELEGRAM_BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Handlers
    start_handler = CommandHandler('start', start)
    edit_handler = CommandHandler('edit', edit)
    
    # Agregar el handler para el comando /edit
    dispatcher.add_handler(edit_handler)

    # Agregar el handler para recibir la nueva hora después del comando /edit
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, set_new_time))

    dispatcher.add_handler(start_handler)

    # Job para enviar la imagen diariamente
    scheduler = BackgroundScheduler(timezone=pytz.timezone('America/New_York'))
    scheduler.add_job(send_progress_bar_image, 'interval', minutes=1)  # Cambiado a cada minuto para pruebas
    scheduler.start()

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()


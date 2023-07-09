from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, DateTime
from dotenv import load_dotenv
import datetime
import telebot
import logging
import os

load_dotenv()

# Initialize the Telegram Bot API
token = os.environ.get('TOKEN')
bot = telebot.TeleBot(token, parse_mode='MARKDOWN')

# Create the database engine and metadata
engine = create_engine('sqlite:///notes.db')
metadata = MetaData()

# Define the notes table
notes = Table('notes', metadata,
              Column('id', Integer, primary_key=True),
              Column('user_id', Integer),
              Column('note_text', String),
              Column('timestamp', DateTime(), default=datetime.datetime.now())
)

metadata.create_all(engine)

# Enable logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if message.text == '/help':
        response = '''
        📝 Welcome to the Note Saver Bot!
        
        To use this bot, you can use the following commands:
        - `/save note`: 💾 Save a note.
        - `/update id new-note`: 🖊 Update a note.
        - `/delete id`: 🗑 Delete a note .
        - `/notes`: 📒 List your saved notes.
        '''
    else:
        response = '''
        📝 Welcome to the Note Saver Bot! 
        Send `/save note` to save it.
        '''

    bot.reply_to(message, response)


@bot.message_handler(commands=['save'])
def save_note(message):
    # Extract the user ID and note text from the message
    user_id = message.chat.id
    note_text = message.text.replace('/save', '').strip()
    timestamp = datetime.datetime.fromtimestamp(message.date)

    if not note_text:
        bot.reply_to(message, '🚫 Нельзя сохранить пустую заметку!')
        return

    # Insert the note into the database
    with engine.connect() as connection:
        connection.execute(notes.insert().values(user_id=user_id, note_text=note_text, timestamp=timestamp))
        connection.commit()

    bot.reply_to(message, '✅ Заметка успешно сохранена!')


@bot.message_handler(commands=['update'])
def update_note(message):
    # Extract the user ID, note ID, and updated text from the message
    user_id = message.chat.id
    command, note_id, *note_text_parts = message.text.split(' ')
    note_text = ' '.join(note_text_parts)

    # Update the note in the database
    with engine.connect() as connection:
        update_query = (
            notes.update()
            .where(notes.c.user_id == user_id)
            .where(notes.c.id == note_id)
            .values(note_text=note_text)
        )
        result = connection.execute(update_query)
        connection.commit()
        updated_rows = result.rowcount

    if updated_rows > 0:
        bot.reply_to(message, f'✏  Заметка {note_id} обновлена!')
    else:
        bot.reply_to(message, '🚫  Такая заметка не найдена.')


@bot.message_handler(commands=['notes'])
def list_notes(message):
    # Retrieve the user's notes from the database
    user_id = message.chat.id
    with engine.connect() as connection:
        select_query = notes.select().where(notes.c.user_id == user_id).order_by(notes.c.timestamp)
        result = connection.execute(select_query)
        notes_list = result.fetchall()

    if len(notes_list) > 0:
        response = '📃 *Cохраненные заметки*:\n\n'
        for note in notes_list:
            note_text = note.note_text
            timestamp = note.timestamp.strftime('%d-%m-%Y %H:%M:%S')
            response += '*{})*  {} `(Добавлено: {})`\n'.format(note.id, note_text, timestamp)
    else:
        response = '⚪ Пока нет ни одной заметки.'

    bot.send_message(message.chat.id, response)


@bot.message_handler(commands=['delete'])
def delete_note(message):
    # Extract the user ID and note ID from the message
    user_id = message.chat.id
    note_id = message.text.replace('/delete', '').strip()

    # Delete the note from the database
    with engine.connect() as connection:
        delete_query = notes.delete().where(notes.c.user_id == user_id).where(notes.c.id == note_id)
        result = connection.execute(delete_query)
        deleted_rows = result.rowcount
        connection.commit()

    if deleted_rows > 0:
        bot.reply_to(message, '❌ Заметка {} была успешно удалена!'.format(note_id))
    else:
        bot.reply_to(message, 'Такая заметка не найдена. 🚫')


# Start the bot
bot.polling()

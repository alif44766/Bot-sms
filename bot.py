import telebot
import sqlite3
import time
import os
from telebot import types

# --- কনফিগারেশন ---
API_TOKEN = '8463139658:AAECrUe1JeoVV7MoQgyG3Pj452RsfoYV0E8'
ADMIN_URL = 'https://t.me/ftcaiw24'
NUMBERS_DIR = 'numbers/'
SMS_DB_PATH = 'sms/sms_db.db'

bot = telebot.TeleBot(API_TOKEN)

# ইউজারের প্রগ্রেস সেভ রাখার জন্য (ডিকশনারি)
user_data = {} 

# ফাইল থেকে নাম্বার পড়ার ফাংশন
def get_numbers_from_file(server_name):
    file_path = os.path.join(NUMBERS_DIR, f"{server_name}.txt")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    btn_get = types.InlineKeyboardButton("🚀 Get Number", callback_data="select_server")
    btn_admin = types.InlineKeyboardButton("👨‍💻 Admin", url=ADMIN_URL)
    markup.add(btn_get, btn_admin)
    bot.send_message(message.chat.id, "বটে স্বাগতম! সার্ভিস বেছে নিন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "select_server")
def select_server(call):
    markup = types.InlineKeyboardMarkup()
    # ফোল্ডারের ফাইল অনুযায়ী বাটন তৈরি
    files = [f.replace('.txt', '') for f in os.listdir(NUMBERS_DIR) if f.endswith('.txt')]
    for server in files:
        markup.add(types.InlineKeyboardButton(f"🔹 {server.upper()}", callback_data=f"srv_{server}"))
    bot.edit_message_text("একটি সার্ভার সিলেক্ট করুন:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("srv_"))
def handle_number_request(call):
    server = call.data.split("_")[1]
    user_id = call.from_user.id
    
    numbers = get_numbers_from_file(server)
    
    # ইনডেক্স ঠিক করা (১ থেকে শুরু)
    if user_id not in user_data or user_data[user_id].get('server') != server:
        index = 0
    else:
        index = user_data[user_id]['index'] + 1

    if index < len(numbers):
        phone = numbers[index]
        user_data[user_id] = {'server': server, 'index': index, 'current_phone': phone}
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Get Next Number", callback_data=f"srv_{server}"))
        markup.add(types.InlineKeyboardButton("📩 Get SMS", callback_data=f"check_sms_{phone}"))
        
        bot.edit_message_text(f"✅ সার্ভার: {server.upper()}\n🔢 সিরিয়াল: {index + 1}\n📞 নাম্বার: `{phone}`", 
                              call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "এই সার্ভারে আর কোন নাম্বার নেই!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("check_sms_"))
def check_sms(call):
    phone = call.data.split("_")[2]
    request_time = int(time.time())
    
    if not os.path.exists(SMS_DB_PATH):
        bot.answer_callback_query(call.id, "SMS Database পাওয়া যায়নি!", show_alert=True)
        return

    try:
        conn = sqlite3.connect(SMS_DB_PATH)
        cursor = conn.cursor()
        
        # ১ মিনিট আগে থেকে ১ মিনিট পরের রেঞ্জ (৬০ সেকেন্ড)
        cursor.execute("SELECT message FROM sms_logs WHERE phone = ? AND timestamp BETWEEN ? AND ?", 
                       (phone, request_time - 60, request_time + 60))
        result = cursor.fetchone()
        conn.close()

        if result:
            bot.send_message(call.message.chat.id, f"📩 নাম্বার: `{phone}`\n💬 মেসেজ: \n`{result[0]}`", parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "মেসেজ পাওয়া যায়নি। ১ মিনিট অপেক্ষা করে আবার চেষ্টা করুন।", show_alert=True)
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)}", show_alert=True)

bot.polling(none_stop=True)

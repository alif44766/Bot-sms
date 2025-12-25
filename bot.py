
import telebot
import time
import requests
import os
from telebot import types

# --- কনফিগারেশন ---
API_TOKEN = '8463139658:AAECrUe1JeoVV7MoQgyG3Pj452RsfoYV0E8'
FIREBASE_URL = 'https://otp-bot-611a8-default-rtdb.firebaseio.com' 
ADMIN_PASSWORD = '1122'
ADMIN_URL = 'https://t.me/ftcaiw24'
GROUP_URL = 'https://t.me/ftc_sms_chat'  # ওটিপি না পেলে এখানে যাবে
CHANNEL_URL = 'https://t.me/ftc_sms'      # আপডেটের জন্য চ্যানেল
NUMBERS_DIR = 'numbers/'

bot = telebot.TeleBot(API_TOKEN)

# ফায়ারবেজ হেল্পার ফাংশন
def db_save(path, data):
    requests.put(f"{FIREBASE_URL}/{path}.json", json=data)

def db_get(path):
    res = requests.get(f"{FIREBASE_URL}/{path}.json")
    return res.json()

# --- মেইন মেনু ---
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_get = types.InlineKeyboardButton("🚀 Get Number", callback_data="select_server")
    btn_admin = types.InlineKeyboardButton("👨‍💻 Admin", url=ADMIN_URL)
    btn_group = types.InlineKeyboardButton("👥 Support Group", url=GROUP_URL)
    btn_channel = types.InlineKeyboardButton("📢 Update Channel", url=CHANNEL_URL)
    
    markup.add(btn_get)
    markup.add(btn_admin, btn_group)
    markup.add(btn_channel)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🔐 *Online OTP System Active* ✅\n\nনাম্বার নিতে নিচের বাটন চাপুন। সব ধরনের আপডেটের জন্য আমাদের চ্যানেলে জয়েন থাকুন।", 
                     parse_mode="Markdown", reply_markup=main_menu())

# --- ইউজার সেকশন (সার্ভার লিস্ট) ---
@bot.callback_query_handler(func=lambda call: call.data == "select_server")
def select_server(call):
    markup = types.InlineKeyboardMarkup()
    if not os.path.exists(NUMBERS_DIR): os.makedirs(NUMBERS_DIR)
    
    files = [f.replace('.txt', '') for f in os.listdir(NUMBERS_DIR) if f.endswith('.txt')]
    
    if not files:
        markup.add(types.InlineKeyboardButton("⬅️ Back to Home", callback_data="back_home"))
        bot.edit_message_text("❌ কোনো সার্ভার পাওয়া যায়নি!", call.message.chat.id, call.message.message_id, reply_markup=markup)
        return

    for s in files:
        markup.add(types.InlineKeyboardButton(f"🔹 {s.upper()}", callback_data=f"srv_{s}"))
    
    markup.add(types.InlineKeyboardButton("⬅️ Back to Home", callback_data="back_home"))
    bot.edit_message_text("একটি সার্ভার সিলেক্ট করুন:", call.message.chat.id, call.message.message_id, reply_markup=markup)

# --- নাম্বার ডেলিভারি লজিক ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("srv_"))
def handle_number(call):
    server = call.data.split("_")[1]
    user_id = str(call.from_user.id)
    
    file_path = os.path.join(NUMBERS_DIR, f"{server}.txt")
    if not os.path.exists(file_path):
        bot.answer_callback_query(call.id, "ফাইলটি পাওয়া যায়নি!", show_alert=True)
        return

    with open(file_path, 'r') as f:
        numbers = [line.strip() for line in f.readlines() if line.strip()]

    progress = db_get(f"user_progress/{user_id}")
    index = (progress['index'] + 1) if (progress and progress.get('server') == server) else 0

    if index < len(numbers):
        phone = numbers[index]
        db_save(f"user_progress/{user_id}", {"index": index, "server": server})
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("🔄 Get Next Number", callback_data=f"srv_{server}"))
        markup.add(types.InlineKeyboardButton("📩 Get SMS", callback_data=f"check_{phone}"))
        markup.add(types.InlineKeyboardButton("📢 Channel", url=CHANNEL_URL), 
                   types.InlineKeyboardButton("⬅️ Back", callback_data="select_server"))
        
        bot.edit_message_text(f"🌍 *Server:* {server.upper()}\n🔢 *Serial:* {index + 1}\n☎️ *Number:* `{phone}`", 
                              call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="select_server"))
        bot.edit_message_text("❌ এই সার্ভারে আর কোনো নাম্বার নেই!", call.message.chat.id, call.message.message_id, reply_markup=markup)

# --- এসএমএস চেক লজিক ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def check_sms(call):
    phone = call.data.split("_")[1]
    now = int(time.time())
    
    data = db_get(f"sms_logs/{phone}")
    
    if data and abs(now - data['timestamp']) <= 60:
        response = f"🔐 *New OTP Received* ✅\n\n☎️ *Number:* `{phone}`\n💬 *Message:*\n`{data['message']}`"
        bot.send_message(call.message.chat.id, response, parse_mode="Markdown")
    else:
        # ওটিপি না পেলে গ্রুপে জয়েন করতে বলা
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👥 Join Group for OTP", url=GROUP_URL))
        bot.send_message(call.message.chat.id, "❌ মেসেজ এখনো আসেনি। যদি ওটিপি না পান তবে আমাদের গ্রুপে যোগাযোগ করুন।", 
                         reply_markup=markup)
        bot.answer_callback_query(call.id, "অপেক্ষা করুন...", show_alert=False)

# --- ব্যাক টু হোম বাটন ---
@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def back_home(call):
    bot.edit_message_text("🔐 *Online OTP System Active* ✅\n\nসার্ভার থেকে নাম্বার নিতে বাটন চাপুন।", 
                          call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=main_menu())

# --- এডমিন সেকশন (আগের মতো) ---
@bot.message_handler(func=lambda m: m.text and m.text.lower() == 'admin')
def admin_login(message):
    msg = bot.reply_to(message, "🔐 এডমিন পাসওয়ার্ড দিন:")
    bot.register_next_step_handler(msg, process_password)

def process_password(message):
    if message.text == ADMIN_PASSWORD:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Add Number", callback_data="adm_add"),
                   types.InlineKeyboardButton("🗑️ Delete Server", callback_data="adm_del"))
        markup.add(types.InlineKeyboardButton("⬅️ Exit Admin", callback_data="back_home"))
        bot.send_message(message.chat.id, "✅ এডমিন লগইন সফল!", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ ভুল পাসওয়ার্ড!")

@bot.callback_query_handler(func=lambda call: call.data == "adm_add")
def adm_add_srv(call):
    bot.edit_message_text("সার্ভারের নাম লিখুন:", call.message.chat.id, call.message.message_id)
    bot.register_next_step_handler(call.message, get_srv_name)

def get_srv_name(message):
    server = message.text.lower()
    msg = bot.send_message(message.chat.id, f"📦 {server}-এর জন্য নাম্বার দিন (প্রতি লাইনে একটি):")
    bot.register_next_step_handler(msg, lambda m: final_add(m, server))

def final_add(message, server):
    nums = message.text.strip()
    if not os.path.exists(NUMBERS_DIR): os.makedirs(NUMBERS_DIR)
    with open(os.path.join(NUMBERS_DIR, f"{server}.txt"), 'a') as f:
        f.write(nums + "\n")
    bot.send_message(message.chat.id, f"✅ {server}-এ নাম্বার সেভ হয়েছে!", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "adm_del")
def adm_del_list(call):
    markup = types.InlineKeyboardMarkup()
    files = [f.replace('.txt', '') for f in os.listdir(NUMBERS_DIR) if f.endswith('.txt')]
    for s in files:
        markup.add(types.InlineKeyboardButton(f"🗑️ Delete {s}", callback_data=f"conf_del_{s}"))
    markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_home"))
    bot.edit_message_text("কোনটি ডিলিট করবেন?", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("conf_del_"))
def conf_del(call):
    srv = call.data.split("_")[2]
    os.remove(os.path.join(NUMBERS_DIR, f"{srv}.txt"))
    bot.answer_callback_query(call.id, f"✅ {srv} ডিলিট করা হয়েছে।", show_alert=True)
    adm_del_list(call)

# --- কনসোল আপডেট কমান্ড ---
@bot.message_handler(func=lambda m: m.text and m.text.startswith("DB_ADD:"))
def remote_db_add(message):
    try:
        raw_data = message.text.replace("DB_ADD:", "").split("|")
        phone = raw_data[0].strip()
        msg_text = raw_data[1].strip()
        now = int(time.time())
        db_save(f"sms_logs/{phone}", {"message": msg_text, "timestamp": now})
        bot.reply_to(message, f"✅ Database Updated: {phone}")
    except:
        pass

if __name__ == "__main__":
    if not os.path.exists(NUMBERS_DIR): os.makedirs(NUMBERS_DIR)
    print("🤖 Bot is Running with Support Group & Update Channel...")
    bot.polling(none_stop=True)

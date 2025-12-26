import telebot
import time
import requests
import threading
from flask import Flask
from telebot import types

# --- কনফিগারেশন ---
API_TOKEN = '8463139658:AAECrUe1JeoVV7MoQgyG3Pj452RsfoYV0E8'
FIREBASE_URL = 'https://otp-bot-611a8-default-rtdb.firebaseio.com' 
ADMIN_PASSWORD = '1122'
ADMIN_URL = 'https://t.me/ftcaiw24'
GROUP_URL = 'https://t.me/ftc_sms_chat'
CHANNEL_URL = 'https://t.me/ftc_sms'

bot = telebot.TeleBot(API_TOKEN)

# --- ১. রেন্ডার কিপ-এলাইভ (Flask Server) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "🔥 Firebase Bot is Running!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_flask).start()

# --- ২. ফায়ারবেজ হেল্পার ফাংশন ---
def db_put(path, data):
    requests.put(f"{FIREBASE_URL}/{path}.json", json=data)

def db_get(path):
    try:
        res = requests.get(f"{FIREBASE_URL}/{path}.json")
        return res.json()
    except:
        return None

def db_delete(path):
    requests.delete(f"{FIREBASE_URL}/{path}.json")

# --- ৩. মেইন মেনু ---
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🚀 Get Number", callback_data="select_server"))
    markup.add(types.InlineKeyboardButton("👨‍💻 Admin", url=ADMIN_URL),
               types.InlineKeyboardButton("👥 Group", url=GROUP_URL))
    markup.add(types.InlineKeyboardButton("📢 Channel", url=CHANNEL_URL))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🔐 *Online OTP System Active* ✅\n\nফায়ারবেজ ডাটাবেজ থেকে নাম্বার নিতে নিচের বাটন চাপুন।", 
                     parse_mode="Markdown", reply_markup=main_menu())

# --- ৪. ইউজার সেকশন (ফায়ারবেজ থেকে সার্ভার লোড) ---
@bot.callback_query_handler(func=lambda call: call.data == "select_server")
def select_server(call):
    markup = types.InlineKeyboardMarkup()
    
    # ফায়ারবেজ থেকে সার্ভার লিস্ট আনা
    servers_data = db_get("servers")
    
    if not servers_data:
        markup.add(types.InlineKeyboardButton("⬅️ Back to Home", callback_data="back_home"))
        bot.edit_message_text("❌ ডাটাবেজে কোনো সার্ভার নেই!", call.message.chat.id, call.message.message_id, reply_markup=markup)
        return

    # সার্ভারগুলোর বাটন তৈরি
    for srv_name in servers_data.keys():
        markup.add(types.InlineKeyboardButton(f"🔹 {srv_name.upper()}", callback_data=f"srv_{srv_name}"))
    
    markup.add(types.InlineKeyboardButton("⬅️ Back to Home", callback_data="back_home"))
    bot.edit_message_text("একটি সার্ভার সিলেক্ট করুন:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("srv_"))
def handle_number(call):
    server = call.data.split("_")[1]
    user_id = str(call.from_user.id)
    
    # ফায়ারবেজ থেকে ঐ সার্ভারের নাম্বার লিস্ট আনা
    numbers = db_get(f"servers/{server}")
    
    if not numbers or not isinstance(numbers, list):
        bot.answer_callback_query(call.id, "এই সার্ভারে কোনো নাম্বার নেই!", show_alert=True)
        return

    # ইউজারের প্রগ্রেস চেক
    progress = db_get(f"user_progress/{user_id}")
    index = (progress['index'] + 1) if (progress and progress.get('server') == server) else 0

    if index < len(numbers):
        phone = numbers[index]
        # ইউজারের প্রগ্রেস আপডেট
        db_put(f"user_progress/{user_id}", {"index": index, "server": server})
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("🔄 Next Number", callback_data=f"srv_{server}"),
                   types.InlineKeyboardButton("📩 Get SMS", callback_data=f"check_{phone}"))
        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="select_server"))
        
        bot.edit_message_text(f"🌍 *Server:* {server.upper()}\n🔢 *Serial:* {index + 1}\n☎️ *Number:* `{phone}`", 
                              call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "এই সার্ভারে আর নাম্বার নেই!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def check_sms(call):
    phone = call.data.split("_")[1]
    now = int(time.time())
    data = db_get(f"sms_logs/{phone}")
    
    if data and abs(now - data['timestamp']) <= 300: # ৫ মিনিট পর্যন্ত ভ্যালিড
        bot.send_message(call.message.chat.id, f"🔐 *OTP Received* ✅\n\n☎️ `{phone}`\n💬 `{data['message']}`", parse_mode="Markdown")
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👥 Join Group", url=GROUP_URL))
        bot.send_message(call.message.chat.id, "❌ মেসেজ এখনো আসেনি।", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def back_home(call):
    bot.edit_message_text("🔐 *Online OTP System Active* ✅", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=main_menu())

# --- ৫. কনসোল থেকে ডাটাবেজ আপডেট (ব্রাউজার স্ক্রিপ্ট) ---
@bot.message_handler(func=lambda m: m.text and m.text.startswith("DB_ADD:"))
def remote_db_add(message):
    try:
        raw = message.text.replace("DB_ADD:", "").split("|")
        phone, msg = raw[0].strip(), raw[1].strip()
        db_put(f"sms_logs/{phone}", {"message": msg, "timestamp": int(time.time())})
        bot.reply_to(message, f"✅ Firebase Updated: {phone}")
    except: pass

# ==========================================
#              ৬. এডমিন প্যানেল (Firebase)
# ==========================================

@bot.message_handler(commands=['admin'])
def admin_login(message):
    msg = bot.reply_to(message, "🔐 *Admin Login*\nদয়া করে পাসওয়ার্ড দিন:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, verify_password)

def verify_password(message):
    if message.text == ADMIN_PASSWORD:
        show_admin_panel(message.chat.id)
    else:
        bot.reply_to(message, "❌ ভুল পাসওয়ার্ড!")

def show_admin_panel(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ Add Numbers to Firebase", callback_data="adm_add_fb"))
    markup.add(types.InlineKeyboardButton("🗑️ DELETE ALL OTPs (Reset)", callback_data="adm_del_all_otp"))
    markup.add(types.InlineKeyboardButton("🗑️ Delete Specific Server", callback_data="adm_del_srv"))
    markup.add(types.InlineKeyboardButton("🚪 Logout", callback_data="back_home"))
    bot.send_message(chat_id, "⚙️ *Firebase Admin Dashboard*\nঅপশন সিলেক্ট করুন:", parse_mode="Markdown", reply_markup=markup)

# --- 1. Delete ALL OTPs ---
@bot.callback_query_handler(func=lambda call: call.data == "adm_del_all_otp")
def confirm_del_otp(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚠️ YES, DELETE ALL", callback_data="do_del_otp"))
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="back_admin"))
    bot.edit_message_text("⚠️ আপনি কি ডাটাবেজের **সব ওটিপি** ডিলিট করতে চান?", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "do_del_otp")
def delete_all_otps(call):
    db_delete("sms_logs") # পুরো sms_logs নোড ডিলিট করে দিবে
    bot.answer_callback_query(call.id, "All OTPs Deleted!", show_alert=True)
    bot.send_message(call.message.chat.id, "✅ ডাটাবেজের সব ওটিপি ক্লিয়ার করা হয়েছে।")
    show_admin_panel(call.message.chat.id)

# --- 2. Add Numbers to Firebase ---
@bot.callback_query_handler(func=lambda call: call.data == "adm_add_fb")
def adm_ask_srv(call):
    msg = bot.send_message(call.message.chat.id, "📝 সার্ভারের নাম লিখুন (উদা: facebook):")
    bot.register_next_step_handler(msg, adm_get_srv)

def adm_get_srv(message):
    server_name = message.text.lower().strip()
    msg = bot.send_message(message.chat.id, f"📦 *{server_name.upper()}* এর জন্য নাম্বার লিস্ট পেস্ট করুন:\n(প্রতি লাইনে একটি নাম্বার)", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: adm_push_numbers(m, server_name))

def adm_push_numbers(message, server_name):
    raw_text = message.text.strip()
    if not raw_text:
        bot.send_message(message.chat.id, "❌ কোনো নাম্বার পাওয়া যায়নি।")
        return

    new_numbers = [n.strip() for n in raw_text.split('\n') if n.strip()]
    
    # আগের নাম্বারগুলো চেক করা (Append Logic)
    current_numbers = db_get(f"servers/{server_name}")
    if not current_numbers:
        current_numbers = []
    
    # নতুন নাম্বার যোগ করা
    final_list = current_numbers + new_numbers
    
    # ফায়ারবেজে সেভ করা
    db_put(f"servers/{server_name}", final_list)
    
    bot.send_message(message.chat.id, f"✅ ফায়ারবেজে {len(new_numbers)} টি নাম্বার যোগ হয়েছে!\nসার্ভার: {server_name}")
    show_admin_panel(message.chat.id)

# --- 3. Delete Specific Server ---
@bot.callback_query_handler(func=lambda call: call.data == "adm_del_srv")
def adm_list_srv_del(call):
    markup = types.InlineKeyboardMarkup()
    servers = db_get("servers")
    
    if not servers:
        bot.answer_callback_query(call.id, "ডাটাবেজে কোনো সার্ভার নেই!", show_alert=True)
        return

    for s in servers.keys():
        markup.add(types.InlineKeyboardButton(f"🗑️ Delete {s.upper()}", callback_data=f"del_fb_{s}"))
    markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_admin"))
    bot.edit_message_text("কোন সার্ভারটি ফায়ারবেজ থেকে মুছতে চান?", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_fb_"))
def adm_del_process(call):
    server = call.data.split("_")[2]
    db_delete(f"servers/{server}")
    bot.answer_callback_query(call.id, "Deleted!", show_alert=True)
    bot.send_message(call.message.chat.id, f"✅ {server} সার্ভারটি ফায়ারবেজ থেকে মুছে ফেলা হয়েছে।")
    show_admin_panel(call.message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_admin")
def back_admin(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_admin_panel(call.message.chat.id)

if __name__ == "__main__":
    print("🤖 Firebase Bot is Running...")
    bot.polling(none_stop=True)

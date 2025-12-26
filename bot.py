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

# বট ইনিশিলাইজেশন
bot = telebot.TeleBot(API_TOKEN)

# ==========================================
# 1. RENDER KEEP-ALIVE (Flask Server)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🔥 Bot is Running Successfully!"

def run_flask():
    # রেন্ডার সাধারণত পোর্ট 10000 ব্যবহার করে
    app.run(host='0.0.0.0', port=10000)

# আলাদা থ্রেডে সার্ভার রান করা
threading.Thread(target=run_flask).start()

# ==========================================
# 2. FIREBASE HELPER FUNCTIONS
# ==========================================
def db_put(path, data):
    try:
        requests.put(f"{FIREBASE_URL}/{path}.json", json=data)
    except Exception as e:
        print(f"Firebase Put Error: {e}")

def db_get(path):
    try:
        res = requests.get(f"{FIREBASE_URL}/{path}.json")
        if res.status_code == 200:
            return res.json()
        return None
    except Exception as e:
        print(f"Firebase Get Error: {e}")
        return None

def db_delete(path):
    try:
        requests.delete(f"{FIREBASE_URL}/{path}.json")
    except Exception as e:
        print(f"Firebase Delete Error: {e}")

# ==========================================
# 3. MAIN MENU & USER INTERFACE
# ==========================================
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🚀 Get Number", callback_data="select_server"))
    markup.add(types.InlineKeyboardButton("👨‍💻 Admin", url=ADMIN_URL),
               types.InlineKeyboardButton("👥 Group", url=GROUP_URL))
    markup.add(types.InlineKeyboardButton("📢 Channel", url=CHANNEL_URL))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🔐 *Online OTP System Active* ✅\n\nনাম্বার নিতে নিচের বাটন চাপুন।", 
                     parse_mode="Markdown", reply_markup=main_menu())

# --- সার্ভার সিলেকশন ---
@bot.callback_query_handler(func=lambda call: call.data == "select_server")
def select_server(call):
    markup = types.InlineKeyboardMarkup()
    
    # ফায়ারবেজ থেকে সার্ভার লিস্ট আনা
    servers_data = db_get("servers")
    
    if not servers_data:
        markup.add(types.InlineKeyboardButton("⬅️ Back to Home", callback_data="back_home"))
        bot.edit_message_text("❌ ডাটাবেজে কোনো সার্ভার নেই!", call.message.chat.id, call.message.message_id, reply_markup=markup)
        return

    # সার্ভার বাটন জেনারেট
    for srv_name in servers_data.keys():
        markup.add(types.InlineKeyboardButton(f"🔹 {srv_name.upper()}", callback_data=f"srv_{srv_name}"))
    
    markup.add(types.InlineKeyboardButton("⬅️ Back to Home", callback_data="back_home"))
    bot.edit_message_text("একটি সার্ভার সিলেক্ট করুন:", call.message.chat.id, call.message.message_id, reply_markup=markup)

# --- নাম্বার হ্যান্ডলিং ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("srv_"))
def handle_number(call):
    server = call.data.split("_")[1]
    user_id = str(call.from_user.id)
    
    # ফায়ারবেজ থেকে নাম্বার আনা
    numbers = db_get(f"servers/{server}")
    
    if not numbers or not isinstance(numbers, list):
        bot.answer_callback_query(call.id, "এই সার্ভারে কোনো নাম্বার নেই!", show_alert=True)
        return

    # ইউজারের সিরিয়াল চেক
    progress = db_get(f"user_progress/{user_id}")
    index = (progress['index'] + 1) if (progress and progress.get('server') == server) else 0

    if index < len(numbers):
        phone = numbers[index]
        # নতুন প্রগ্রেস সেভ
        db_put(f"user_progress/{user_id}", {"index": index, "server": server})
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("🔄 Next Number", callback_data=f"srv_{server}"),
                   types.InlineKeyboardButton("📩 Get SMS", callback_data=f"check_{phone}"))
        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="select_server"))
        
        bot.edit_message_text(f"🌍 *Server:* {server.upper()}\n🔢 *Serial:* {index + 1}\n☎️ *Number:* `{phone}`", 
                              call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "এই সার্ভারে আর নাম্বার নেই!", show_alert=True)

# --- এসএমএস চেক ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def check_sms(call):
    phone = call.data.split("_")[1]
    now = int(time.time())
    data = db_get(f"sms_logs/{phone}")
    
    # ৫ মিনিটের (৩০০ সেকেন্ড) মধ্যে আসা মেসেজ ভ্যালিড ধরবে
    if data and abs(now - data['timestamp']) <= 300: 
        bot.send_message(call.message.chat.id, f"🔐 *OTP Received* ✅\n\n☎️ `{phone}`\n💬 `{data['message']}`", parse_mode="Markdown")
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👥 Join Group", url=GROUP_URL))
        bot.send_message(call.message.chat.id, "❌ মেসেজ এখনো আসেনি।", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def back_home(call):
    bot.edit_message_text("🔐 *Online OTP System Active* ✅", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=main_menu())

# --- কনসোল কমান্ড (DB_ADD) ---
@bot.message_handler(func=lambda m: m.text and m.text.startswith("DB_ADD:"))
def remote_db_add(message):
    try:
        raw = message.text.replace("DB_ADD:", "").split("|")
        phone, msg = raw[0].strip(), raw[1].strip()
        db_put(f"sms_logs/{phone}", {"message": msg, "timestamp": int(time.time())})
        bot.reply_to(message, f"✅ Firebase Updated: {phone}")
    except: pass

# ==========================================
# 4. ADMIN PANEL (FIREBASE CONTROL)
# ==========================================
@bot.message_handler(commands=['admin'])
def admin_login(message):
    msg = bot.reply_to(message, "🔐 *Admin Login*\nপাসওয়ার্ড দিন:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, verify_password)

def verify_password(message):
    if message.text == ADMIN_PASSWORD:
        show_admin_panel(message.chat.id)
    else:
        bot.reply_to(message, "❌ ভুল পাসওয়ার্ড!")

def show_admin_panel(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ Add Numbers (Firebase)", callback_data="adm_add_fb"))
    markup.add(types.InlineKeyboardButton("🧹 DELETE ALL OTPs (Reset)", callback_data="adm_del_all_otp"))
    markup.add(types.InlineKeyboardButton("🗑️ Delete Server", callback_data="adm_del_srv"))
    markup.add(types.InlineKeyboardButton("🚪 Logout", callback_data="back_home"))
    bot.send_message(chat_id, "⚙️ *Admin Dashboard*", parse_mode="Markdown", reply_markup=markup)

# --- সব ওটিপি ডিলিট ---
@bot.callback_query_handler(func=lambda call: call.data == "adm_del_all_otp")
def confirm_del_otp(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚠️ YES, DELETE ALL", callback_data="do_del_otp"))
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="back_admin"))
    bot.edit_message_text("⚠️ আপনি কি সব ওটিপি ডিলিট করতে চান?", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "do_del_otp")
def delete_all_otps(call):
    db_delete("sms_logs")
    bot.answer_callback_query(call.id, "All OTPs Deleted!", show_alert=True)
    bot.send_message(call.message.chat.id, "✅ ডাটাবেজ ক্লিয়ার করা হয়েছে।")
    show_admin_panel(call.message.chat.id)

# --- ফায়ারবেজে নাম্বার অ্যাড ---
@bot.callback_query_handler(func=lambda call: call.data == "adm_add_fb")
def adm_ask_srv(call):
    msg = bot.send_message(call.message.chat.id, "📝 সার্ভারের নাম লিখুন (উদা: imo):")
    bot.register_next_step_handler(msg, adm_get_srv)

def adm_get_srv(message):
    server_name = message.text.lower().strip()
    msg = bot.send_message(message.chat.id, f"📦 *{server_name.upper()}* এর জন্য নাম্বার লিস্ট দিন:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: adm_push_numbers(m, server_name))

def adm_push_numbers(message, server_name):
    raw_text = message.text.strip()
    if not raw_text:
        bot.send_message(message.chat.id, "❌ নাম্বার পাওয়া যায়নি।")
        return

    new_numbers = [n.strip() for n in raw_text.split('\n') if n.strip()]
    current_numbers = db_get(f"servers/{server_name}")
    if not current_numbers: current_numbers = []
    
    # নতুন এবং পুরানোগুলো মার্জ করা
    final_list = current_numbers + new_numbers
    db_put(f"servers/{server_name}", final_list)
    
    bot.send_message(message.chat.id, f"✅ {len(new_numbers)} টি নাম্বার অ্যাড হয়েছে!")
    show_admin_panel(message.chat.id)

# --- সার্ভার ডিলিট ---
@bot.callback_query_handler(func=lambda call: call.data == "adm_del_srv")
def adm_list_srv_del(call):
    markup = types.InlineKeyboardMarkup()
    servers = db_get("servers")
    if not servers:
        bot.answer_callback_query(call.id, "কোনো সার্ভার নেই!", show_alert=True)
        return
    for s in servers.keys():
        markup.add(types.InlineKeyboardButton(f"🗑️ Delete {s.upper()}", callback_data=f"del_fb_{s}"))
    markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_admin"))
    bot.edit_message_text("ডিলিট করতে সিলেক্ট করুন:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_fb_"))
def adm_del_process(call):
    server = call.data.split("_")[2]
    db_delete(f"servers/{server}")
    bot.answer_callback_query(call.id, "Deleted!", show_alert=True)
    adm_list_srv_del(call)

@bot.callback_query_handler(func=lambda call: call.data == "back_admin")
def back_admin(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_admin_panel(call.message.chat.id)

# ==========================================
# 5. AUTO RECONNECT & STARTUP
# ==========================================
if __name__ == "__main__":
    print("🤖 Bot is starting...")
    
    # এই লুপটি বটকে ক্র্যাশ হওয়া থেকে বাঁচাবে
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"⚠️ Connection Error: {e}")
            print("🔄 Reconnecting in 5 seconds...")
            time.sleep(5)

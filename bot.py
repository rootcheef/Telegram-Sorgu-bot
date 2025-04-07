import os
import logging
import mysql.connector
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# === Telegram Bot Token ===
TOKEN = "TOKENİNİZİ GİRİN"

# === Logging Ayarları ===
log_folder = r"C:\Users\Administrator\Desktop\BOTUM"
os.makedirs(log_folder, exist_ok=True)
log_file = os.path.join(log_folder, "log.txt")

logging.basicConfig(
    filename=log_file,
    filemode='a',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# === Veritabanı Bağlantısı ===
def get_db_connection(database):
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database=database
        )
    except mysql.connector.Error as err:
        logging.error(f"Veritabanı bağlantı hatası ({database}): {err}")
        return None

# === Kişi Bilgisi Çekme ===
def get_user_info(filters_dict=None):
    conn = get_db_connection("101m")
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        base_query = "SELECT * FROM 101m"
        conditions, values = [], []

        column_map = {
            "ad": "ADI", "soyad": "SOYADI",
            "il": "NUFUSIL", "ilce": "NUFUSILCE",
            "tc": "TC"
        }

        if filters_dict:
            for key, value in filters_dict.items():
                if key in column_map:
                    conditions.append(f"{column_map[key]} = %s")
                    values.append(value)

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        base_query += " LIMIT 1"

        cursor.execute(base_query, tuple(values))
        result = cursor.fetchone()
        cursor.close()
        return result
    except mysql.connector.Error as err:
        logging.error(f"Sorgu hatası: {err}")
        return None
    finally:
        conn.close()

# === GSM Sorguları ===
def get_gsm_from_tc(tc):
    conn = get_db_connection("145mgsm")
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM 145mgsm WHERE TC = %s LIMIT 1", (tc,))
        result = cursor.fetchone()
        cursor.close()
        return result
    finally:
        conn.close()

def get_tc_from_gsm(gsm):
    conn = get_db_connection("145mgsm")
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM 145mgsm WHERE GSM = %s LIMIT 1", (gsm,))
        result = cursor.fetchone()
        cursor.close()
        return result
    finally:
        conn.close()

# === Operatör Bilgisi ===
def get_operator_info(gsm):
    try:
        url = f"GSM APİNİZİ YAZIN{gsm}"
        response = requests.get(url)
        return response.json() if "Operatör" in response.json() else None
    except Exception as e:
        logging.error(f"Operatör API hatası: {e}")
        return None

# === GIF Gönderici ===
async def send_gif(update: Update):
    gif_path = "C4COMMİNTYFREE.gif"
    if os.path.exists(gif_path):
        with open(gif_path, "rb") as gif:
            await update.message.reply_animation(gif)

# === Komutlar ===
async def start_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type not in ['group', 'supergroup']:
        return  # Özel mesajda işlem yapma
    await send_gif(update)
    mesaj = (
        "🤖 Bot Aktif\n\n"
        "📋 Komutlar:\n"
        "🔍 /tc 12345678901\n"
        "🔎 /ara ad=Ad soyad=Soyad il=İl ilce=İlçe\n"
        "📞 /gsmtc 5xxxxxxxxx\n"
        "📱 /tcgsm 12345678901\n"
        "🏢 /operator 5xxxxxxxxx\n"
        "👪 /aile 12345678901\n"
        "🧹 /clear\n"
        "ℹ️ /start /yardim"
    )
    await update.message.reply_text(mesaj)

async def clear_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type not in ['group', 'supergroup']:
        return  # Özel mesajda işlem yapma
    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    for i in range(message_id - 20, message_id):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=i)
        except:
            continue

async def tc_sorgu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type not in ['group', 'supergroup']:
        return  # Özel mesajda işlem yapma
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("⚠️ Doğru kullanım: /tc 12345678901")
        return

    user = get_user_info({"tc": context.args[0]})
    if not user:
        await update.message.reply_text("❌ Kayıt bulunamadı.")
        return

    mesaj = (
        f"👤 {user['ADI']} {user['SOYADI']}\n"
        f"📌 İl: {user['NUFUSIL']} / {user['NUFUSILCE']}\n"
        f"🎂 Doğum Tarihi: {user['DOGUMTARIHI']}\n"
        f"👩‍👦 Anne: {user.get('ANNEADI', 'Bilinmiyor')}\n"
        f"👨‍👦 Baba: {user.get('BABAADI', 'Bilinmiyor')}\n"
        f"🆔 TC: {user['TC']}"
    )
    await update.message.reply_text(mesaj)
    await send_gif(update)

async def tcgsm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type not in ['group', 'supergroup']:
        return  # Özel mesajda işlem yapma
    if len(context.args) != 1:
        await update.message.reply_text("⚠️ Kullanım: /tcgsm 12345678901")
        return

    result = get_gsm_from_tc(context.args[0])
    if not result:
        await update.message.reply_text("❌ GSM bulunamadı.")
        return

    await update.message.reply_text(f"📱 GSM: {result['GSM']}\n🆔 TC: {result['TC']}")
    await send_gif(update)

async def gsmtc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type not in ['group', 'supergroup']:
        return  # Özel mesajda işlem yapma
    if len(context.args) != 1:
        await update.message.reply_text("⚠️ Kullanım: /gsmtc 5xxxxxxxxx")
        return

    result = get_tc_from_gsm(context.args[0])
    if not result:
        await update.message.reply_text("❌ TC bulunamadı.")
        return

    await update.message.reply_text(f"🆔 TC: {result['TC']}\n📱 GSM: {result['GSM']}")
    await send_gif(update)

async def operator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type not in ['group', 'supergroup']:
        return  # Özel mesajda işlem yapma
    if len(context.args) != 1:
        await update.message.reply_text("⚠️ Kullanım: /operator 5xxxxxxxxx")
        return

    data = get_operator_info(context.args[0])
    if not data:
        await update.message.reply_text("❌ Operatör bilgisi bulunamadı.")
    else:
        mesaj = f"📱 GSM: {data['GSM']}\n🏢 Operatör: {data['Operatör']}"
        await update.message.reply_text(mesaj)

async def handle_ara(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type not in ['group', 'supergroup']:
        return  # Özel mesajda işlem yapma
    args = update.message.text.replace("/ara", "").strip().split()
    filters_dict = {k.lower(): v for part in args if "=" in part for k, v in [part.split("=", 1)]}

    if not filters_dict:
        await update.message.reply_text("⚠️ Kullanım: /ara ad=Ad soyad=Soyad il=İl ilce=İlçe")
        return

    user = get_user_info(filters_dict)
    if not user:
        await update.message.reply_text("❌ Kayıt bulunamadı.")
        return

    mesaj = (
        f"👤 {user['ADI']} {user['SOYADI']}\n"
        f"🆔 TC: {user['TC']}\n"
        f"📌 Memleket: {user['NUFUSIL']}"
    )
    await update.message.reply_text(mesaj)
    await send_gif(update)

async def aile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type not in ['group', 'supergroup']:
        return  # Özel mesajda işlem yapma
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("⚠️ Kullanım: /aile 12345678901")
        return

    tc = context.args[0]
    conn = get_db_connection("101m")
    if not conn:
        await update.message.reply_text("❌ Veritabanı bağlantı hatası.")
        return

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM 101m WHERE TC = %s", (tc,))
        user = cursor.fetchone()
        if not user:
            await update.message.reply_text("❌ Kayıt bulunamadı.")
            return

        result = ""
        queries = {
            "Çocuklar": ("SELECT * FROM 101m WHERE (ANNETC = %s OR BABATC = %s) AND TC != %s", (tc, tc, tc)),
            "Kardeşler": ("SELECT * FROM 101m WHERE (ANNETC = %s OR BABATC = %s) AND TC != %s", (tc, tc, tc)),
            "Anne-Baba": ("SELECT * FROM 101m WHERE TC = %s", (user['ANNEADI'],)),
        }
        for relation, (query, params) in queries.items():
            cursor.execute(query, params)
            data = cursor.fetchall()
            result += f"\n{relation}:\n"
            for person in data:
                result += f"{person['ADI']} {person['SOYADI']} ({person['TC']})\n"
        
        await update.message.reply_text(result if result else "❌ Aile üyeleri bulunamadı.")
    except mysql.connector.Error as err:
        logging.error(f"Aile sorgusu hatası: {err}")
        await update.message.reply_text("❌ Hata oluştu.")
    finally:
        conn.close()

# === Bot Konfigürasyonu ===
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start_help))
    application.add_handler(CommandHandler("yardim", start_help))
    application.add_handler(CommandHandler("tc", tc_sorgu))
    application.add_handler(CommandHandler("tcgsm", tcgsm))
    application.add_handler(CommandHandler("gsmtc", gsmtc))
    application.add_handler(CommandHandler("operator", operator))
    application.add_handler(CommandHandler("ara", handle_ara))
    application.add_handler(CommandHandler("aile", aile))
    application.add_handler(CommandHandler("clear", clear_messages))

    application.run_polling()

if __name__ == "__main__":
    main()

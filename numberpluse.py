from collections import Counter
import os
import phonenumbers
from phonenumbers import geocoder
import telebot
from telebot import types

BOT_TOKEN = "8716955781:AAHT9loYpXquEINc-Yq0F5PWe7olN2jKuEo"
bot = telebot.TeleBot(BOT_TOKEN)

user_sessions = {}


def get_country_name(number_str):
    try:
        formatted = (
            number_str if number_str.startswith("+") else "+" + number_str
        )
        parsed = phonenumbers.parse(formatted, None)
        country = geocoder.description_for_number(parsed, "en")
        return country if country else "Unknown"
    except Exception:
        return "Unknown"


# Main Menu Buttons (/start)
@bot.message_handler(commands=["start"])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_help = types.InlineKeyboardButton("ℹ️ Help", callback_data="btn_help")
    btn_status = types.InlineKeyboardButton(
        "⚡ Status", callback_data="btn_status"
    )
    markup.add(btn_help, btn_status)

    bot.reply_to(
        message,
        "👋 **Welcome!**\n\nNumbers wali `.txt` file bhejo, main country detect karke sabke aage `+` add kar dunga.",
        parse_mode="Markdown",
        reply_markup=markup,
    )


# File handler
@bot.message_handler(content_types=["document"])
def handle_file(message):
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        text_data = downloaded_file.decode("utf-8", errors="ignore")
        lines = text_data.splitlines()

        processed_numbers = []
        country_list = []

        for line in lines:
            num = line.strip()
            if num:
                clean_num = "+" + num if not num.startswith("+") else num
                processed_numbers.append(clean_num)

                if len(country_list) < 50:
                    c_name = get_country_name(clean_num)
                    if c_name != "Unknown":
                        country_list.append(c_name)

        if not processed_numbers:
            bot.reply_to(message, "⚠️ File khali hai ya koi valid number nahi mila!")
            return

        top_country = (
            Counter(country_list).most_common(1)[0][0]
            if country_list
            else "Unknown"
        )

        user_sessions[message.chat.id] = {
            "numbers": processed_numbers,
            "country": top_country,
            "orig_name": message.document.file_name or "numbers.txt",
        }

        # Action Buttons
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_custom = types.InlineKeyboardButton(
            "✍️ Custom Name", callback_data="action_custom"
        )
        btn_default = types.InlineKeyboardButton(
            "⚡ Default Name", callback_data="action_default"
        )
        btn_cancel = types.InlineKeyboardButton(
            "❌ Cancel", callback_data="action_cancel"
        )
        markup.add(btn_custom, btn_default)
        markup.add(btn_cancel)

        caption = (
            f"🌍 **Detected Country:** `{top_country}`\n"
            f"📊 **Total Numbers:** `{len(processed_numbers)}`\n\n"
            "File ready hai. Ab niche diye gaye buttons se choose karo:"
        )

        bot.reply_to(message, caption, parse_mode="Markdown", reply_markup=markup)

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


# Button Clicks Handle Karna
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id

    if call.data == "btn_help":
        bot.answer_callback_query(call.id)
        bot.send_message(
            chat_id,
            "📖 **Guide:**\n1. Bas `.txt` file send karo\n2. Bot automatic Country check karega\n3. Button dabakar direct download kar lo!",
            parse_mode="Markdown",
        )

    elif call.data == "btn_status":
        bot.answer_callback_query(call.id, text="Bot Active & Running! 🚀", show_alert=True)

    elif call.data == "action_cancel":
        bot.answer_callback_query(call.id, text="Cancelled")
        if chat_id in user_sessions:
            del user_sessions[chat_id]
        bot.edit_message_text(
            "❌ Process cancel kar diya gaya.",
            chat_id,
            call.message.message_id,
        )

    elif call.data == "action_default":
        bot.answer_callback_query(call.id)
        if chat_id not in user_sessions:
            bot.send_message(chat_id, "Session expired, file dobara bhejo.")
            return

        session = user_sessions[chat_id]
        clean_country = session["country"].replace(" ", "_")
        filename = f"{clean_country}_numbers.txt"
        deliver_file(chat_id, filename)

    elif call.data == "action_custom":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(
            chat_id,
            "📝 File ka jo naam rakhna hai, abhi text message mein likh kar bhejo:",
        )
        bot.register_next_step_handler(msg, process_custom_name)


def process_custom_name(message):
    chat_id = message.chat.id
    if chat_id not in user_sessions:
        bot.reply_to(message, "Session expired! Dobara file upload karo.")
        return

    name = message.text.strip()
    if not name.endswith(".txt"):
        name += ".txt"

    deliver_file(chat_id, name)


def deliver_file(chat_id, filename):
    session = user_sessions.get(chat_id)
    if not session:
        return

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(session["numbers"]))

        caption = (
            f"✅ **File Converted!**\n"
            f"📁 **Name:** `{filename}`\n"
            f"🌍 **Country:** `{session['country']}`\n"
            f"🔢 **Count:** `{len(session['numbers'])}`"
        )

        with open(filename, "rb") as f:
            bot.send_document(chat_id, f, caption=caption, parse_mode="Markdown")

        if os.path.exists(filename):
            os.remove(filename)
        del user_sessions[chat_id]

    except Exception as e:
        bot.send_message(chat_id, f"File delivery error: {e}")


bot.infinity_polling()

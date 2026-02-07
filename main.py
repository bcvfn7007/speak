import os
import re
import time
import threading
from collections import defaultdict

import telebot
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://xxx.up.railway.app

if not TOKEN or not WEBHOOK_URL:
    raise RuntimeError("BOT_TOKEN or WEBHOOK_URL not set")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ====== НАСТРОЙКИ ======
MUTE_SECONDS = 5 * 60          # мут 5 минут
MAX_WARNINGS = 3               # сколько нарушений до жёсткого мута
WARNING_TTL_SECONDS = 5

# ====== СЧЁТЧИК НАРУШЕНИЙ ======
violations = defaultdict(int)

# ====== ЗАГРУЗКА ПЛОХИХ СЛОВ ======
with open("bad_words.txt", encoding="utf-8") as f:
    BAD_ROOTS = [line.strip() for line in f if line.strip()]

# анти-обход: пробелы, символы, латиница
OBFUSCATION = r"[^\w]*"

bad_pattern = re.compile(
    r"(?<!\w)(" + OBFUSCATION.join(BAD_ROOTS) + r")\w*",
    re.IGNORECASE
)


def delete_later(chat_id, message_id, delay):
    def _del():
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
    threading.Timer(delay, _del).start()


def mute_user(chat_id, user_id, seconds):
    until = int(time.time()) + seconds
    try:
        bot.restrict_chat_member(
            chat_id,
            user_id,
            until_date=until,
            permissions=telebot.types.ChatPermissions(can_send_messages=False)
        )
    except Exception:
        pass


@bot.message_handler(content_types=["text"])
def moderate(message):
    text = message.text or ""

    if bad_pattern.search(text):
        user_id = message.from_user.id
        chat_id = message.chat.id

        violations[user_id] += 1

        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception:
            return

        if violations[user_id] >= MAX_WARNINGS:
            mute_user(chat_id, user_id, MUTE_SECONDS)
            warn = bot.send_message(
                chat_id,
                f"🔇 Пользователь замьючен на {MUTE_SECONDS//60} мин за нарушения."
            )
        else:
            warn = bot.send_message(
                chat_id,
                f"⚠️ Нарушение {violations[user_id]}/{MAX_WARNINGS}"
            )

        delete_later(chat_id, warn.message_id, WARNING_TTL_SECONDS)


# ====== WEBHOOK ======
@app.route("/", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.json)
    bot.process_new_updates([update])
    return "OK", 200


@app.route("/", methods=["GET"])
def index():
    return "Bot is running", 200


if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

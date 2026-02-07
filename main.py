import os
import re
import threading
import telebot

TOKEN = os.getenv("8234772720:AAF7WdXm0bWhYpqyGFUiPLip8eMwzH_L-es", "8234772720:AAF7WdXm0bWhYpqyGFUiPLip8eMwzH_L-es")
bot = telebot.TeleBot(TOKEN)

# Список "плохих" слов (пример). Лучше хранить в файле/БД.
BAD_WORDS = {"нахуй","уёбок","уёбище","сука", "уебок", "хуй", "пидр", "пидор","пидорас","долбаеб","долбаёб","пох","похуй","хуесос","бля","блять","бл","блат","блят","уебан","ебан","ебать","еблан","хуела","ебаное","член","заебал","сосать","сосо"}
bad_pattern = re.compile(r"\b(" + "|".join(map(re.escape, BAD_WORDS)) + r")\b", re.IGNORECASE)
WARNING_TTL_SECONDS = 5  # через сколько секунд удалить предупреждение


def delete_later(chat_id: int, message_id: int, delay: int) -> None:
    def _do_delete():
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            # Уже удалено или нет прав — просто игнорируем
            pass

    threading.Timer(delay, _do_delete).start()


@bot.message_handler(content_types=["text"])
def moderate_text(message: telebot.types.Message):
    text = message.text or ""
    if not text:
        return

    if bad_pattern.search(text):
        # 1) Удаляем сообщение пользователя
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception:
            # Обычно причина: бот не админ/нет права удалять
            return

        # 2) Отправляем короткое предупреждение (без “простыней”)
        warn = bot.send_message(message.chat.id, "Сообщение удалено.")
        # 3) Удаляем предупреждение через N секунд
        delete_later(warn.chat.id, warn.message_id, WARNING_TTL_SECONDS)


bot.polling(skip_pending=True, none_stop=True)
from .. import loader, utils
import os

from pyrogram.types import Message


class Logs(loader.Module):
    strings = {"name": "Logs"}

    # translate

    async def logs_cmd(self, message: Message):
        """
        .logs [level] — Send log file filtered by level (default: INFO)
        Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
        """
        args = utils.get_args_raw(message).strip().upper()
        level = args if args in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] else "INFO"

        log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "teagram.log")
        if not os.path.exists(log_path):
            await message.reply("Log file not found.")
            return

        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        min_level = levels.index(level)
        filtered = [line for line in lines if any(lvl in line for lvl in levels[min_level:])]

        if not filtered:
            await message.reply(f"No log records with level {level} or higher.")
            return

        text = "<code>" + "".join(filtered[-50:]).replace("<", "&lt;").replace(">", "&gt;") + "</code>"
        if len(text) > 4000 or len(filtered) > 50:
            from io import BytesIO
            file = BytesIO("".join(filtered).encode("utf-8"))
            file.name = f"teagram-{level.lower()}-logs.txt"
            await message.reply_document(file, caption=f"Logs (level: {level})")
        else:
            await message.reply(text, parse_mode="HTML")

    async def clearlogs_cmd(self, message: Message):
        """
        .clearlogs — Clear the log file
        """
        log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "teagram.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("")
            await message.reply("Log file cleared.")
        except Exception as e:
            await message.reply(f"Failed to clear log file: {e}")
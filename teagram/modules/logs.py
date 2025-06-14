from .. import loader, utils
import os
import logging
from typing import Optional
from pyrogram.types import Message


class TelegramLogHandler(logging.Handler):
    def __init__(self, send_func):
        super().__init__()
        self.send_func = send_func  # async function to send logs

    def emit(self, record):
        log_entry = self.format(record)
        import asyncio
        asyncio.create_task(self.send_func(log_entry))


class Logs(loader.Module):
    strings = {"name": "Logs"}

    # translate
    # inline buttons

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_chat_id: Optional[int] = None
        self._log_handler: Optional[TelegramLogHandler] = None

    @loader.command()
    async def logschatcmd(self, message: Message):
        """
        — Set this chat as log receiver
        """
        self.log_chat_id = message.chat.id
        if self._log_handler:
            logging.getLogger().removeHandler(self._log_handler)
        self._log_handler = TelegramLogHandler(self._send_log_to_chat)
        self._log_handler.setLevel(logging.ERROR)  # Only errors by default
        self._log_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logging.getLogger().addHandler(self._log_handler)
        await message.reply("This chat is now set as log receiver. All ERROR logs will be sent here.")

    async def _send_log_to_chat(self, log_entry: str):
        if self.log_chat_id:
            try:
                await self.client.send_message(self.log_chat_id, f"<code>{log_entry}</code>", parse_mode="HTML")
            except Exception:
                pass

    @loader.command()
    async def logscmd(self, message: Message):
        """
        [level] — Send log file filtered by level (default: INFO)
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

    @loader.command()
    async def clearlogscmd(self, message: Message):
        """
        — Clear the log file
        """
        log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "teagram.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("")
            await message.reply("Log file cleared.")
        except Exception as e:
            await message.reply(f"Failed to clear log file: {e}")
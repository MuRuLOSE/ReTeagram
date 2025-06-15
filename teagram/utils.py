from __future__ import annotations
import os
import time
import logging
import random
import string
from typing import List, Optional, Union, Any
from io import BytesIO, IOBase
from enum import Enum
from urllib.parse import urlparse
from configparser import ConfigParser

from pyrogram.types import Message
from pyrogram.enums.parse_mode import ParseMode
from teagram.client import CustomClient
from aiogram import types
from . import init_time

FileLike = Optional[Union[BytesIO, IOBase, bytes, str]]
InlineLike = Union[types.ChosenInlineResult, types.InlineQuery, types.CallbackQuery]

BASE_PATH = os.path.normpath(
    os.path.join(os.path.abspath(os.path.dirname(os.path.abspath(__file__))), "..")
)
LETTERS = string.ascii_letters + string.digits


class Parser(Enum):
    HTML = ParseMode.HTML
    MARKDOWN = ParseMode.MARKDOWN


class CommandParseResult:
    """
    Represents the result of command parsing.
    Attributes:
        prefix (str): The command prefix (e.g., '.')
        command (str): The command name (lowercase)
        args (str): The raw arguments string (may be empty)
    """

    def __init__(self, prefix: str = "", command: str = "", args: str = ""):
        self.prefix = prefix
        self.command = command
        self.args = args

    def __bool__(self) -> bool:
        return bool(self.command)

    def __iter__(self):
        return iter((self.prefix, self.command, self.args))

    def __repr__(self) -> str:
        return f"<CommandParseResult prefix={self.prefix!r} command={self.command!r} args={self.args!r}>"


def get_uptime() -> str:
    """Returns uptime as HH:MM:SS string."""
    current_time = time.time()
    uptime_seconds = current_time - init_time
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"


def get_command(database: Any, message: Message) -> CommandParseResult:
    """
    Extracts the prefix, command, and arguments from a message.
    Returns CommandParseResult(prefix, command, args) or all empty if not a command.
    """
    message_text = getattr(
        getattr(message, "raw", message), "message", None
    ) or getattr(message, "text", None)
    if not message_text:
        return CommandParseResult()
    prefixes = (
        database.get("teagram", "prefix", ["."]) if database is not None else [""]
    )
    for prefix in prefixes:
        if message_text.startswith(prefix) and len(message_text) > len(prefix):
            parts = message_text[len(prefix) :].split(maxsplit=1)
            command = parts[0].lower() if parts else ""
            args = parts[1] if len(parts) > 1 else ""
            return CommandParseResult(prefix, command, args)
    return CommandParseResult()


def normalize_parser(parse_mode: str | Parser) -> str | None:
    if isinstance(parse_mode, str):
        parse_mode_enum = getattr(Parser, parse_mode.upper(), None)
        if parse_mode_enum:
            return parse_mode_enum.value
    elif isinstance(parse_mode, Parser):
        return parse_mode.value
    return parse_mode


def is_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


async def answer(
    message: Message,
    content: Union[str, FileLike],
    parse_mode: str = "HTML",
    **kwargs,
):
    """Send or edit a message, or send a photo with caption, with proper parse_mode."""
    result = None
    parse_mode = normalize_parser(parse_mode)
    caption = kwargs.pop("caption", None)
    if not content:
        logging.error(f"Expected content got {content}")
        return
    if content and not caption:
        if getattr(message, "outgoing", False):
            result = await message.edit(content, parse_mode=parse_mode, **kwargs)
        else:
            result = await message.reply(content, parse_mode=parse_mode, **kwargs)
    elif caption:
        if not isinstance(content, (IOBase, BytesIO, bytes)) and not is_url(content):
            logging.error(f"Expected `FileLike` got {type(content)}")
            return
        if isinstance(content, bytes):
            content = BytesIO(content)
        result = await message.reply_photo(
            content, caption=caption, parse_mode=parse_mode, **kwargs
        )
        if getattr(message, "outgoing", False):
            await message.delete()
    return result


def random_id(length: int = 10) -> str:
    """Generate a random string of given length from LETTERS."""
    return "".join(random.choice(LETTERS) for _ in range(length))


def clear_console() -> None:
    """Simulation of clear console, moves cursor to last line of command line. Compatible with all systems."""
    print("\033[H\033[J", end="")


rand = random_id

JAPANESE_MOCK = [
    "Kaze",
    "Yami",
    "Hikari",
    "Tenshi",
    "Yume",
    "Tsuki",
    "Hana",
    "Kumo",
    "Mizu",
    "Tora",
    "Kage",
    "Sora",
    "Hoshi",
    "Kokoro",
    "Kami",
    "Ryu",
    "Yoru",
    "Taiyo",
    "Sakura",
    "Akari",
    "Kitsune",
    "Yuki",
    "Raijin",
    "Inari",
    "Shiro",
    "Kuro",
    "Midori",
    "Aoi",
    "Akai",
    "Shinju",
    "Kumo",
    "Kawa",
    "Umi",
    "Mori",
    "Yama",
    "Hane",
    "Kumo",
    "Koi",
    "Hibiki",
    "Ren",
    "Haruka",
    "Kazumi",
    "Ayame",
    "Takara",
    "Hinata",
    "Suzu",
    "Rin",
    "Natsu",
    "Fuyu",
    "Ame",
    "Kirin",
    "Sango",
    "Hotaru",
    "Mochi",
    "Sora",
    "Kage",
    "Kumo",
    "Mizu",
    "Yoru",
    "Hana",
    "Tsuki",
    "Yume",
    "Kokoro",
    "Ryu",
    "Kami",
    "Hoshi",
    "Kaze",
    "Yami",
    "Taiyo",
    "Tenshi",
    "Sakura",
]


def generate_app_name() -> str:
    """Generate random Japanese-style app name."""
    return "-".join(random.choices(JAPANESE_MOCK, k=3))


def save_app_name() -> str:
    """Save the generated app name to a config file and return it."""
    config = ConfigParser()
    config_path = os.path.join(BASE_PATH, "config.ini")
    if os.path.exists(config_path):
        config.read(config_path)
    if not config.has_section("teagram"):
        config.add_section("teagram")
    if not config.has_option("teagram", "app_name"):
        config.set("teagram", "app_name", generate_app_name())
        with open(config_path, "w") as f:
            config.write(f)
    return config.get("teagram", "app_name", fallback=generate_app_name())


JAPANESE_FEMALE_NAMES = [
    "Sakura",
    "Yuki",
    "Haruka",
    "Hinata",
    "Ayame",
    "Takara",
    "Akari",
    "Kazumi",
    "Suzu",
    "Rin",
    "Natsu",
    "Fuyu",
    "Ame",
    "Hotaru",
    "Mochi",
    "Hana",
    "Kumiko",
    "Mizuho",
    "Miyu",
    "Aoi",
    "Midori",
    "Shinju",
    "Ayaka",
    "Nanami",
    "Emi",
    "Yume",
    "Kanon",
    "Sayuri",
    "Mio",
    "Rika",
    "Nozomi",
    "Kokoro",
    "Hibiki",
    "Kayo",
    "Miyuki",
    "Rina",
    "Yuna",
    "Kana",
    "Miyako",
    "Chihiro",
    "Yui",
]


def generate_bot_name() -> str:
    """Generate random Japanese-style bot name."""
    return random.choice(JAPANESE_FEMALE_NAMES) + "-chan"


def save_bot_name() -> str:
    """Save the generated bot name to a config file and return it."""
    config = ConfigParser()
    config_path = os.path.join(BASE_PATH, "config.ini")
    if os.path.exists(config_path):
        config.read(config_path)
    if not config.has_section("teagram"):
        config.add_section("teagram")
    if not config.has_option("teagram", "bot_name"):
        config.set("teagram", "bot_name", generate_bot_name())
        with open(config_path, "w") as f:
            config.write(f)
    return config.get("teagram", "bot_name", fallback=generate_bot_name())


def get_args(message: Message) -> list[str]:
    """
    Returns a list of command arguments (split by spaces), excluding the prefix and command name.
    Example: For the message `.test foo bar`, returns ["foo", "bar"].
    """
    result = get_command(None, message)
    return result.args.split() if result.args else []


def get_args_raw(message: Message) -> str:
    """
    Returns the raw string of command arguments (everything after the command name), excluding the prefix and command name.
    Example: For the message `.test foo bar`, returns "foo bar".
    """
    result = get_command(None, message)
    return result.args or ""


async def create_asset_group(
    client: CustomClient,
    group_name: str,
    group_type: str = "private",
    users: int | str | List[int | str] = None,
) -> types.Chat:
    """
    Create a new group for asset management.

    :param client: The client instance to use for creating the chat.
    :param chat_name: The name of the chat to create.
    :param chat_type: The type of chat to create (default is "private").
    :param users: Users to add to the group.
    :return: The created chat object.
    """
    if group_type not in ["private", "group", "supergroup"]:
        raise ValueError(
            "Invalid chat type. Must be 'private', 'group', or 'supergroup'."
        )

    async for dialog in client.get_dialogs():
        chat = dialog.chat
        if chat.type in ("supergroup", "group") and chat.title == group_name:
            return chat

    return await client.create_group(group_name, users=users)

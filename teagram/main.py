from .auth import Authorization
from .loader import Loader
from .database import Database
from pyrogram.methods.utilities.idle import idle
import asyncio
import logging
import sys
import traceback
from pyrogram.errors.exceptions import PeerIdInvalid

# Custom logging handler to suppress tracebacks for specific errors
class CustomHandler(logging.StreamHandler):
    def emit(self, record):
        if not getattr(record, "exc_info", None):
            return super().emit(record)
        
        # Suppress traceback for PeerIdInvalid unless in debug mode
        exc_type, exc_value, exc_tb = record.exc_info
        if isinstance(exc_value, PeerIdInvalid) and not logging.getLogger().isEnabledFor(logging.DEBUG):
            # Log only the message without traceback
            record.exc_info = None
            record.exc_text = None
            return super().emit(record)
        
        return super().emit(record)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[CustomHandler(sys.stdout)]
)

LOGGERS = ["pyrogram", "aiogram", "aiohttp.access", "watchfiles.main"]
for logger in LOGGERS:
    logging.getLogger(logger).setLevel(logging.ERROR)

class Main:
    def __init__(self, arguments):
        self.arguments = arguments

    def start(self):
        try:
            import uvloop
            if sys.version_info[:2] >= (3, 12):
                uvloop.run(self.main())
            else:
                uvloop.install()
                asyncio.run(self.main())
        except ImportError:
            logging.info("Uvloop not installed, it may cause performance leaks")
            asyncio.run(self.main())

    async def main(self):
        logger = logging.getLogger(__name__)
        
        if getattr(self.arguments, "debug", False):
            logging.getLogger().setLevel(logging.DEBUG)
            logging.getLogger("pyrogram").setLevel(logging.INFO)
            logging.getLogger("pyrogram.session").setLevel(logging.ERROR)
            logger.info("Debug mode enabled")

        database = Database()
        client = await Authorization(
            getattr(self.arguments, "test_mode", False),
            getattr(self.arguments, "no_qr", False),
            getattr(self.arguments, "no_web", False),
            getattr(self.arguments, "port", 0),
        ).authorize()

        await client.connect()
        await client.initialize()

        if not client.me:
            me = await client.get_me()
            client.me = me
            logger.info(f"Authorized as {me.first_name} (@{me.username})")

        loader = Loader(client, database, self.arguments)
        await loader.load()

        await idle()
        logger.info("Shutdown...")
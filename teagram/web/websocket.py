import json
import uuid
import asyncio
import logging
import hashlib

from pathlib import Path
from configparser import ConfigParser, NoSectionError, NoOptionError

from aiohttp import web, WSMsgType

from ..client import CustomClient

from pyrogram import errors
import pyrogram
from pyrogram.types import User

from pyrogram.qrlogin import QRLogin
from pyrogram.raw.functions.account.get_password import GetPassword

from .. import __version__

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
PAGE_DIR = BASE_DIR / "page"


class WebsocketServer:
    def __init__(
        self,
        login_success: asyncio.Event = None,
        test_mode: bool = False,
        *args,
        **kwargs,
    ):
        self.login_success = login_success or asyncio.Event()
        self.connection = None
        self.test_mode = test_mode

        self.need_2fa = False
        self.hint = None

        self.last_request = None
        self.session_token = None

        self.data = None
        self.client = None
        self.qr_login = None
        self.qr_wait = None

        self.app = web.Application()
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/ws", self.handler)
        self.app.router.add_static("/static", path=PAGE_DIR / "static", name="static")

        self._config_path = BASE_DIR.parent.parent / "config.ini"
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config = self.load_config()

        super().__init__(*args, **kwargs)

    def load_config(self) -> ConfigParser:
        config = ConfigParser()
        if self._config_path.is_file():
            config.read(str(self._config_path))
        return config

    # --- Password protection methods ---

    def get_password_hash(self):
        if self._config.has_option("auth", "password_hash"):
            return self._config.get("auth", "password_hash")
        return None

    def set_password_hash(self, password: str):
        if not self._config.has_section("auth"):
            self._config.add_section("auth")
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        print(f"[DEBUG] Set password hash: {password_hash}")  # Для отладки
        self._config.set("auth", "password_hash", password_hash)
        with open(self._config_path, "w") as file:
            self._config.write(file)
        return password_hash

    def check_password(self, password: str):
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        print(f"[DEBUG] Check password hash: {password_hash}, expected: {self.get_password_hash()}")  # Для отладки
        return password_hash == self.get_password_hash()

    async def index(self, _) -> web.Response:
        return web.FileResponse(path=PAGE_DIR / "index.html")

    async def send_request(self, data: dict):
        self.last_request = data
        if self.connection is None or self.connection.closed:
            return

        await self.connection.send_json(data)

    async def handler(self, request: web.Request) -> web.WebSocketResponse:
        session_token = request.cookies.get("session_token")
        if not session_token:
            session_token = str(uuid.uuid4())

        if self.session_token is None:
            self.session_token = session_token

        ws = web.WebSocketResponse()

        ws.set_cookie(
            "session_token", session_token, httponly=True, secure=False, expires=30 * 60
        )
        await ws.prepare(request)

        # --- Password protection handshake ---
        password_hash = self.get_password_hash()
        if password_hash:
            await ws.send_json({"type": "password_required"})
            try:
                msg = await ws.receive_json(timeout=60)
            except Exception:
                await ws.close(code=4001, message=b"Password required")
                return ws

            if msg.get("type") != "password" or not self.check_password(msg.get("content", "")):
                await ws.send_json({"type": "error", "content": "Wrong password"})
                await ws.close(code=4002, message=b"Wrong password")
                return ws
        else:
            # If no password set, ask to set it
            await ws.send_json({"type": "set_password"})
            try:
                msg = await ws.receive_json(timeout=60)
            except Exception:
                await ws.close(code=4003, message=b"Password not set")
                return ws

            if msg.get("type") != "set_password" or not msg.get("content"):
                await ws.send_json({"type": "error", "content": "Password not set"})
                await ws.close(code=4004, message=b"Password not set")
                return ws

            self.set_password_hash(msg.get("content"))
            await ws.send_json({"type": "message", "content": "Password set successfully"})
            await ws.send_json({"type": "password_set"})

        if self.session_token == session_token and self.last_request:
            await ws.send_json(self.last_request)

        if self.connection is not None:
            await ws.close(code=1008, message=b"Too many connections")
            return ws

        self.connection = ws

        try:
            api_id = self._config.get("api_tokens", "api_id")
            api_hash = self._config.get("api_tokens", "api_hash")
            if not api_id or not api_hash:
                await self.send_request({"type": "enter_tokens"})
            else:
                self.client = CustomClient(
                    "../teagram_v2",
                    api_id=api_id,
                    api_hash=api_hash,
                    device_model="Windows 10",
                    app_version=__version__,
                    test_mode=self.test_mode,
                )

                await self.client.connect()
                await self.handle_qr_authorization()
        except (NoSectionError, NoOptionError):
            await self.send_request({"type": "enter_tokens"})

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self.handle_message(msg.data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error("WebSocket error: %s", ws.exception())
        except Exception as exc:
            logger.exception("Error during message handling: %s", exc)
        finally:
            self.connection = None
            if self.qr_wait and not self.qr_wait.done():
                self.qr_wait.cancel()
                try:
                    await self.qr_wait
                except Exception:
                    pass
            self.qr_wait = None

        return ws

    async def handle_message(self, message: str):
        if self.connection is None:
            return

        message_data = json.loads(message)
        message_type = message_data.get("type")

        if message_type == "tokens":
            await self.handle_tokens(message_data)
        elif message_type == "phone_number":
            await self.handle_phone_number(message_data)
        elif message_type == "phone_code":
            await self.handle_phone_code(message_data)
        elif message_type == "cloud_auth":
            await self.handle_cloud_auth(message_data)
        elif message_type == "authorize_qr":
            await self.handle_qr_authorization()
        else:
            await self.send_request(
                {"type": "error", "content": "Unknown message type"}
            )

    async def handle_tokens(self, message_data: dict):
        api_id = message_data.get("API_ID")
        api_hash = message_data.get("API_HASH")

        if not self._config.has_section("api_tokens"):
            self._config.add_section("api_tokens")

        self._config.set("api_tokens", "api_id", api_id)
        self._config.set("api_tokens", "api_hash", api_hash)

        with open(self._config_path, "w") as file:
            self._config.write(file)

        self.client = CustomClient(
            "../teagram_v2",
            api_id=api_id,
            api_hash=api_hash,
            device_model="Windows 10",
            app_version=__version__,
            test_mode=self.test_mode,
        )
        await self.client.connect()
        await self.handle_qr_authorization()

    async def handle_password_needed(self):
        if not self.hint:
            password = await self.client.invoke(GetPassword())
            self.hint = password.hint

        await self.send_request(
            {
                "type": "session_password_needed",
                "content": "Password required for cloud authentication.",
                "hint": self.hint,
            }
        )

        self.need_2fa = True

    async def handle_phone_number(self, message_data: dict):
        phone_number = message_data.get("phone_number")
        try:
            result = await self.client.send_code(phone_number)
            self.data = (phone_number, result.phone_code_hash)

            await self.send_request(
                {"type": "message", "content": "Success! Sent code to Telegram..."}
            )
        except errors.PhoneNumberInvalid:
            await self.send_request(
                {"type": "error", "content": "Invalid phone number, please try again."}
            )
        except errors.PhoneNumberFlood as error:
            await self.send_request(
                {
                    "type": "error",
                    "content": f"Phone floodwait, retry after: {error.value}",
                }
            )
        except errors.PhoneNumberBanned:
            await self.send_request(
                {
                    "type": "error",
                    "content": "Phone number banned, please try another number.",
                }
            )
        except errors.PhoneNumberOccupied:
            await self.send_request(
                {"type": "error", "content": "Phone number is already in use."}
            )
        except errors.BadRequest:
            await self.send_request(
                {"type": "error", "content": "Bad request, please try again."}
            )

    async def handle_phone_code(self, message_data: dict):
        if not self.data:
            await self.send_request({"type": "error", "content": "Missing phone data."})
            return

        phone_number, phone_code_hash = self.data
        phone_code = message_data.get("phone_code")
        try:
            await self.client.sign_in(phone_number, phone_code_hash, phone_code)
            await self.stop()
        except errors.SessionPasswordNeeded:
            await self.handle_password_needed()

    async def handle_cloud_auth(self, message_data: dict):
        try:
            await self.client.check_password(message_data.get("password"))

            await self.send_request(
                {"type": "message", "content": "Cloud authentication successful."}
            )
            await self.stop()
        except Exception as e:
            logger.error("Cloud auth error: %s", e)
            await self.send_request(
                {"type": "error", "content": "Cloud authentication failed."}
            )

    async def handle_qr_authorization(self):
        if self.need_2fa:
            return

        # Cancel previous QR wait task if running
        if self.qr_wait and not self.qr_wait.done():
            self.qr_wait.cancel()
            try:
                await self.qr_wait
            except Exception:
                pass

        self.qr_login = QRLogin(self.client)
        await self.qr_login.recreate()
        self.qr_wait = asyncio.create_task(self.wait_qr_login())

        await self.send_request({"type": "qr_login", "content": self.qr_login.url})

    async def wait_qr_login(self):
        try:
            while True:
                try:
                    logger.info("Waiting for QR login...")
                    state = await self.qr_login.wait(10)
                    if isinstance(state, User):
                        await self.stop()
                        break
                except errors.SessionPasswordNeeded:
                    await self.handle_password_needed()
                    break
                except (asyncio.TimeoutError, pyrogram.errors.AuthTokenExpired):
                    logger.info("QR expired or timeout, recreating QR code...")
                    await self.qr_login.recreate()
                    await self.send_request(
                        {"type": "qr_login", "content": self.qr_login.url}
                    )
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("QR wait task cancelled")
            return

    async def stop(self):
        try:
            await self.connection.close(code=1000)
            await self.client.disconnect()

            self.qr_wait.cancel()

            await self.runner.shutdown()
            self.login_success.set()
        except Exception as e:
            logger.exception("Error during stop: %s", e)

    async def start_server(self, port: int):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        server = web.TCPSite(self.runner, None, port)
        await server.start()
import typing
from enum import Enum
from aiogram import types
from aiogram.types import (
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InlineQueryResultGif,
    InlineQueryResultVideo,
    InlineQueryResultDocument,
    InlineQueryResultAudio,
    InputTextMessageContent,
)
from pyrogram.types import Message as PyroMessage
from pyrogram.enums import ParseMode

from ..utils import FileLike, random_id
from ..types import ABCLoader


class FormType(Enum):
    FORM = "form"
    # TODO: more types


class Form:
    def __init__(self, loader: ABCLoader):
        self._loader = loader

    async def answer(
        self,
        text: str,
        message: types.Message,
        reply_markup: typing.List[typing.Dict[str, typing.Any]] = None,
        *,
        photo: typing.Optional[FileLike] = None,
        gif: typing.Optional[FileLike] = None,
        video: typing.Optional[FileLike] = None,
        file: typing.Optional[FileLike] = None,
        audio: typing.Optional[FileLike] = None,
        parse_mode: typing.Optional[ParseMode] = ParseMode.HTML,
    ) -> PyroMessage:
        form_id = random_id()

        if not hasattr(self, "_forms"):
            self._forms = {}
        if not hasattr(self, "_context"):
            self._context = {}

        self._context[form_id] = {"message": message}

        media = {
            k: v
            for k, v in {
                "photo": photo,
                "gif": gif,
                "video": video,
                "file": file,
                "audio": audio,
            }.items()
            if v is not None
        }

        self._forms[form_id] = {
            "type": FormType.FORM,
            "text": text,
            "reply_markup": reply_markup,
            "parse_mode": parse_mode,
            **media,
        }

        bot_username = getattr(self, "bot_username", None)
        if not bot_username:
            me = await self.bot.get_me()
            bot_username = me.username
            self.bot_username = bot_username

        bot_results = await self._loader.client.get_inline_bot_results(
            bot_username, form_id
        )

        reply_to_message_id = None
        if isinstance(message, PyroMessage):
            reply_to_message_id = message.reply_to_message_id
        elif isinstance(message, types.Message) and message.reply_to_message:
            reply_to_message_id = message.reply_to_message.message_id

        if bot_results and bot_results.results:
            return await self._loader.client.send_inline_bot_result(
                message.chat.id,
                bot_results.query_id,
                bot_results.results[0].id,
                reply_to_message_id=reply_to_message_id,
            )
        else:
            raise ValueError("No inline results returned by bot.")

    async def _form_inline_handler(self, inline_query: types.InlineQuery, form: typing.Dict):
        normalized_markup = self._normalize_reply_markup(form.get("reply_markup"))
        base_text = form.get("text", "")
        parse_mode = "html"
        input_message_content = InputTextMessageContent(message_text=base_text, parse_mode=parse_mode)

        if form.get("photo"):
            result = InlineQueryResultPhoto(
                id=random_id(),
                photo_url=form["photo"],
                thumb_url=form.get("thumb_url", form["photo"]),
                caption=base_text,
                parse_mode=parse_mode,
                reply_markup=normalized_markup,
                input_message_content=input_message_content
            )
        elif form.get("gif"):
            result = InlineQueryResultGif(
                id=random_id(),
                gif_url=form["gif"],
                thumb_url=form.get("thumb_url", form["gif"]),
                caption=base_text,
                parse_mode=parse_mode,
                reply_markup=normalized_markup,
                input_message_content=input_message_content
            )
        elif form.get("video"):
            result = InlineQueryResultVideo(
                id=random_id(),
                video_url=form["video"],
                mime_type="video/mp4",
                thumb_url=form.get("thumb_url", form["video"]),
                title="Video",
                caption=base_text,
                parse_mode=parse_mode,
                reply_markup=normalized_markup,
                input_message_content=input_message_content
            )
        elif form.get("file"):
            result = InlineQueryResultDocument(
                id=random_id(),
                title="Document",
                document_url=form["file"],
                mime_type="application/octet-stream",
                caption=base_text,
                parse_mode=parse_mode,
                reply_markup=normalized_markup,
                input_message_content=input_message_content
            )
        elif form.get("audio"):
            result = InlineQueryResultAudio(
                id=random_id(),
                audio_url=form["audio"],
                title=form.get("title", "Teagram"),
                performer=form.get("performer", ""),
                caption=base_text,
                parse_mode=parse_mode,
                reply_markup=normalized_markup,
                input_message_content=input_message_content
            )
        else:
            result = InlineQueryResultArticle(
                id=random_id(),
                title=form.get("title", "Teagram"),
                description=base_text,
                input_message_content=input_message_content,
                reply_markup=normalized_markup
            )

        await inline_query.answer([result], cache_time=30)

    async def _handle_inline_result(self, inline_query: types.InlineQuery, func_results: typing.List[typing.Dict]):
        results = []
        for r in func_results:
            msg_text = r.get("text") or r.get("message", "")
            content = InputTextMessageContent(
                message_text=msg_text,
                parse_mode="html"
            )
            results.append(
                InlineQueryResultArticle(
                    id=random_id(),
                    title=r.get("title", "Teagram"),
                    description=msg_text,
                    input_message_content=content,
                    reply_markup=self._normalize_reply_markup(r.get("reply_markup"))
                )
            )
        await inline_query.answer(results, cache_time=30)

    def _normalize_reply_markup(self, reply_markup):
        if (
            isinstance(reply_markup, dict) and "inline_keyboard" in reply_markup
        ) or not reply_markup:
            return reply_markup

        if isinstance(reply_markup, list):
            keyboard = []
            for row in reply_markup:
                normalized_row = []
                for button in row:
                    if "callback" in button and callable(button["callback"]):
                        callback_func = button.pop("callback")
                        args = button.pop("args", [])
                        kwargs = button.pop("kwargs", {})
                        button["callback_data"] = self._register_callback(callback_func, args, kwargs)
                    normalized_row.append(button)
                keyboard.append(normalized_row)
            return {"inline_keyboard": keyboard}
        return reply_markup

    def _register_callback(self, callback, args, kwargs):
        callback_id = str(hash((callback, tuple(args), frozenset(kwargs.items()))))
        self._forms[callback_id] = (callback, args, kwargs)
        return callback_id

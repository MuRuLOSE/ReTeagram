from .. import loader, utils
import ast

from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong
from pyrogram.types import Message

def insert_returns(body):
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])

    if isinstance(body[-1], ast.If):
        insert_returns(body[-1].body)
        insert_returns(body[-1].orelse)

    if isinstance(body[-1], ast.With):
        insert_returns(body[-1].body)


async def async_eval(code: str, env: dict):
    code = code or "return"

    cmd = "\n".join(f"    {i}" for i in code.splitlines())
    body = f"async def _eval_temp():\n{cmd}"

    parsed = ast.parse(body)
    body = parsed.body[0].body

    insert_returns(body)

    env = {"__import__": __import__, **env}

    exec(compile(parsed, filename="<ast>", mode="exec"), env)
    result = await eval("_eval_temp()", env)

    return result


class Evaluator(loader.Module):
    strings = {"name": "Eval"}

    @loader.command(alias="e")
    async def eval(self, message: Message, args):
        env = {
            "self": self,
            "client": self.client,
            "loader": self.inline._loader,
            "message": message,
            "msg": message,
            "m": message,
            "args": args,
            "r" : message.reply_to_message,
            "reply": message.reply_to_message,
        }

        result = None
        try:
            result = await async_eval(args.strip(), env)
            if callable(result) and getattr(result, "stringify", None):
                result = result.stringify()
        except Exception as error:
            result = str(error)

        try:
            await utils.answer(message, self.get("result").format(args, result))
        except MessageTooLong:
            result = str(result)
            if len(result) > 4096:
                result = result[:4000] + "\n..."
            await utils.answer(message, self.get("result").format(args, result))

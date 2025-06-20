from pyrogram.types import Message

from .. import loader, utils

from ..translator import SUPPORTED_LANGUAGES
from ..types import ModuleException, ModuleVersionException

from time import time

import subprocess
import logging

import atexit
import psutil

import aiohttp

import sys
import os

import git


def kill(force: bool = False):
    if "DOCKER" in os.environ:
        sys.exit(0)
        return

    try:
        process = psutil.Process(os.getpid())
        for proc in process.children(recursive=True):
            proc.kill()

        if force:
            process.kill()
        else:
            sys.exit(0)
    except psutil.NoSuchProcess:
        pass


def restart(*_):
    logging.info("Restarting...")

    os.execl(
        sys.executable,
        sys.executable,
        "-m",
        "teagram",
        *sys.argv[1:],
    )


class Manager(loader.Module):
    strings = {
        "name": "Manager",
        "setconfig_usage": "Usage: .setconfig <module> <key> <value>",
        "setconfig_success": "Value '{key}' for module '{module}' set to: {value}",
        "setconfig_key_not_found": "Key '{key}' not found in config of module '{module}.",
        "setconfig_module_not_found": "Module '{module}' not found or does not support config.",
        "setconfig_type_error": "Failed to convert value '{value}' to type {type}.",
        "getconfig_usage": "Usage: .getconfig <module> <key>",
        "getconfig_key_not_found": "Key '{key}' not found in config of module '{module}.",
        "getconfig_module_not_found": "Module '{module}' not found or does not support config.",
        "showconfig_usage": "Usage: .showconfig <module>",
        "showconfig_module_not_found": "Module '{module}' not found or does not support config.",
    }

    async def on_load(self):
        try:
            data = self.database.get("teagram", "restart_info", None)
            if data:
                restart_time = round(time() - data["time"])
                message = await self.client.get_messages(data["chat"], data["id"])

                await utils.answer(
                    message, self.get("restart_success").format(restart_time)
                )
        except Exception:
            logging.exception("Failed to change restart message")
        finally:
            self.database.pop("teagram", "restart_info")

    def check_requirements(self, repo, sha):
        commit = repo.commit(sha)
        diffs = commit.diff(commit.parents[0])
        for diff in diffs:
            if diff.a_path == "requirements.txt" or diff.b_path == "requirements.txt":
                return self.download_requirements()

    def download_requirements(self):
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    "requirements.txt",
                    "--user",
                ],
                check=True,
            )
        except subprocess.CalledProcessError:
            logging.error("Error during installing requirements.txt")

    async def load_module(
        self, code: str, save_file: bool = False, origin: str = "<string>"
    ):
        if utils.is_url(code):
            code = await self.fetch_code(code)

        module_class = await self.loader.load_module(
            f"teagram.custom_modules.{utils.random_id()}",
            module_source=code,
            origin=origin,
            save_file=save_file,
        )
        return module_class.__class__.__name__

    @loader.command()
    async def stop(self, message, args=None):
        """
        — stop the userbot process
        """
        await utils.answer(message, self.get("stopping"))
        kill(True)

    @loader.command()
    async def restart(self, message):
        """
        — restart the userbot process
        """
        message = await utils.answer(message, self.get("restarting"))
        atexit.register(restart)

        self.database.set(
            "teagram",
            "restart_info",
            {"chat": message.chat.id, "id": message.id, "time": time()},
        )

        kill()

    @loader.command()
    async def update(self, message):
        """
        — update userbot from git and restart
        """
        message = await utils.answer(message, self.get("checking_updates"))

        try:
            repo = git.Repo(os.path.abspath("."))
            branch = repo.active_branch.name

            repo.remotes.origin.fetch()

            local_commit = repo.head.commit.hexsha
            remote_commit = next(
                repo.iter_commits(f"origin/{branch}", max_count=1)
            ).hexsha

            if local_commit == remote_commit:
                return await utils.answer(message, self.get("uptodate"))

            repo.git.pull()
            self.check_requirements(repo, remote_commit)

            await self.restart(message)
        except git.exc.GitCommandError as e:
            return await utils.answer(message, self.get("update_fail").format(e))
        except Exception as e:
            return await utils.answer(message, self.get("unexpected_error").format(e))

    @loader.command(alias="ch_branch")
    async def change_branch(self, message):
        """
        — switch between main/dev git branches
        """
        branch_name = ""
        try:
            repo = git.Repo(os.path.abspath("."))
            repo.remotes.origin.fetch()

            branch_name = repo.active_branch.name

            if branch_name == "dev":
                branch_name = "main"
            else:
                branch_name = "dev"

            message = await utils.answer(
                message,
                (
                    self.get("changing_branch").format(branch_name)
                    + self.get("changing_warning")
                    if branch_name == "dev"
                    else ""
                ),
            )

            repo.git.checkout(branch_name)
            repo.git.pull()

            self.check_requirements(repo, repo.head.commit.hexsha)

            await self.restart(message)
        except git.exc.GitCommandError as e:
            return await utils.answer(
                message, self.get("changing_fail").format(branch_name, e)
            )
        except Exception as e:
            return await utils.answer(message, self.get("unexpected_error").format(e))

    @loader.command(alias="lm")
    async def loadmod(self, message: Message):
        """
        <file> — load a module from file
        """
        reply = message.reply_to_message
        module_not_found = self.get("module_not_found")

        if not reply:
            return await utils.answer(message, module_not_found)

        file = reply.media
        if not file:
            return await utils.answer(message, module_not_found)

        path = await reply.download(in_memory=True)
        code = None

        if isinstance(file, str):
            try:
                with open(path, "r") as f:
                    code = f.read()
            except Exception as error:
                return await utils.answer(
                    message, self.get("unexpected_error").format(error)
                )
        else:
            code = path.getvalue().decode()

        if not code:
            return await utils.answer(message, self.get("empty_file"))

        try:
            module_name = await self.load_module(code)
            await utils.answer(message, self.get("load_success").format(module_name))
        except (ModuleException, ModuleVersionException) as error:
            return await utils.answer(message, str(error))

    @loader.command(alias="ulm")
    async def unloadmod(self, message, args):
        """
        <module> — unload a module by name
        """
        module = args.strip()
        if not self.loader.lookup(module):
            return await utils.answer(message, self.get("module_not_found"))

        try:
            module_name = await self.loader.unload_module(module)
            if not module_name:
                return await utils.answer(message, self.get("unexpected_error"))
        except ModuleException as error:
            return await utils.answer(message, f"<b>{error}</b>")

        await utils.answer(message, self.get("unload_success").format(module_name))

    @loader.command(alias="dlm")
    async def downloadmod(self, message, args):
        url = args.strip()
        if not url:
            return await utils.answer(message, self.get("module_not_found"))

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    module_code = await response.text()
                    if not module_code:
                        raise Exception()
        except Exception:
            return await utils.answer(message, self.get("unexpected_error"))

        module_name = await self.load_module(module_code)
        await utils.answer(message, self.get("load_success").format(module_name))

    @loader.command()
    async def setlang(self, message, args: str):
        """
        <lang> — set the interface language
        """
        language = args.strip().lower()
        if language not in SUPPORTED_LANGUAGES:
            return await utils.answer(
                message,
                self.get("language_not_supported").format(
                    ", ".join(SUPPORTED_LANGUAGES)
                ),
            )

        self.loader.translator.language = language
        await utils.answer(message, self.get("set_lang_success").format(language))

    @loader.command()
    async def addprefix(self, message, args: str):
        """
        <prefix> — add a new command prefix
        """
        prefix = args.split(" ")[0]
        if not prefix:
            return await utils.answer(message, self.get("invalid_prefix"))

        prefixes = self.database.get("teagram", "prefix", ["."])
        prefixes.append(prefix)

        self.database.set("teagram", "prefix", prefixes)

        await utils.answer(message, self.get("set_prefix_success").format(prefix))

    @loader.command()
    async def delprefix(self, message, args: str):
        """
        <prefix> — remove a command prefix
        """
        prefix = args.split(" ")[0]
        if not prefix:
            return await utils.answer(message, self.get("invalid_prefix"))

        prefixes = self.database.get("teagram", "prefix", ["."])
        if prefix not in prefixes:
            prefixes = ", ".join(prefixes)

            return await utils.answer(
                message, self.get("prefix_not_found").format(prefixes)
            )

        prefixes.remove(prefix)
        self.database.set("teagram", "prefix", prefixes)

        await utils.answer(message, self.get("del_prefix_success").format(prefix))

    @loader.command()
    async def setconfig(self, message: Message, args: str):
        """
        <module> <key> <value> — change module config value
        """
        import typing

        def get_base_type(tp):
            # For Optional[...] and Union[...] extract the first non-None type
            origin = getattr(tp, "__origin__", None)
            if origin is typing.Union:
                args = [t for t in tp.__args__ if t is not type(None)]
                return args[0] if args else str
            return tp

        parts = args.strip().split(maxsplit=2)
        if len(parts) != 3:
            return await utils.answer(message, self.get("setconfig_usage", default="Usage: .setconfig <module> <key> <value>"))
        module_name, key, value = parts
        module = self.loader.lookup(module_name)
        if not module or not hasattr(module, "config"):
            return await utils.answer(message, self.get("setconfig_module_not_found", default=f"Module '{module_name}' not found or does not support config.").format(module_name=module_name))
        config = module.config
        if not hasattr(config, key):
            return await utils.answer(message, self.get("setconfig_key_not_found", default=f"Key '{key}' not found in config of module '{module_name}'.").format(key=key, module_name=module_name))
        # Get type from dataclass field
        field_type = None
        if hasattr(config, "__dataclass_fields__") and key in config.__dataclass_fields__:
            field_type = get_base_type(config.__dataclass_fields__[key].type)
        else:
            field_type = type(getattr(config, key))
        # Handle None/null
        if value.strip().lower() in ("none", "null", ""):  # empty string is also None
            value = None
        else:
            try:
                if field_type is bool:
                    value = value.lower() in ("1", "true", "yes", "on")
                else:
                    value = field_type(value)
            except Exception:
                return await utils.answer(message, self.get("setconfig_type_error", default="Failed to convert value '{value}' to type {type}.").format(value=value, type=field_type))
        setattr(config, key, value)
        if hasattr(module, "save_config"):
            module.save_config()
        await utils.answer(message, self.get("setconfig_success", default="Value '{key}' for module '{module_name}' set to: {value}").format(key=key, module_name=module_name, value=value))

    @loader.command()
    async def getconfig(self, message: Message, args: str):
        """
        <module> <key> — get module config value
        """
        parts = args.strip().split(maxsplit=1)
        if len(parts) != 2:
            return await utils.answer(message, self.get("getconfig_usage", default="Usage: .getconfig <module> <key>"))
        module_name, key = parts
        module = self.loader.lookup(module_name)
        if not module or not hasattr(module, "config"):
            return await utils.answer(message, self.get("getconfig_module_not_found", default=f"Module '{module_name}' not found or does not support config.").format(module_name=module_name))
        config = module.config
        if not hasattr(config, key):
            return await utils.answer(message, self.get("getconfig_key_not_found", default=f"Key '{key}' not found in config of module '{module_name}'.").format(key=key, module_name=module_name))
        value = getattr(config, key)
        desc = None
        if hasattr(config, "__dataclass_fields__"):
            desc = config.__dataclass_fields__[key].metadata.get("description")
        text = self.get("getconfig_value", default="<b>{module_name}.{key}</b> = <code>{value}</code>").format(module_name=module_name, key=key, value=value)
        if desc:
            text += f"\n<i>{desc}</i>"
        await utils.answer(message, text)

    @loader.command()
    async def showconfig(self, message: Message, args: str):
        """
        <module> — show all config values for module
        """
        module_name = args.strip()
        module = self.loader.lookup(module_name)
        if not module or not hasattr(module, "config"):
            return await utils.answer(message, self.get("showconfig_module_not_found", default=f"Module '{module_name}' not found or does not support config.").format(module_name=module_name))
        config = module.config
        if hasattr(config, "__dataclass_fields__"):
            lines = []
            for key, field in config.__dataclass_fields__.items():
                value = getattr(config, key)
                desc = field.metadata.get("description")
                line = self.get("showconfig_line", default="<b>{key}</b>: <code>{value}</code>").format(key=key, value=value)
                if desc:
                    line += f" — <i>{desc}</i>"
                lines.append(line)
            text = self.get("showconfig_title", default="<b>Config for module {module_name}:</b>\n").format(module_name=module_name) + "\n".join(lines)
        else:
            text = str(config)
        await utils.answer(message, text)

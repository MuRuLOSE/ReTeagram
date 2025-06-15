import difflib
from .. import loader, utils


class Help(loader.Module):
    strings = {"name": "Help"}

    @loader.command()
    async def helpcmd(self, message, args):
        modules = self.loader.modules
        all_text = self.get("modules")

        core = False
        if args and any([arg in args for arg in ("--core", "-c")]):
            core = True

        args = args.strip() if args else ""
        if args and not core:
            names = [m.__class__.__name__ for m in modules]
            module = next((m for m in modules if m.__class__.__name__.lower().startswith(args.lower())), None)
            if not module:
                module = next((m for m in modules if args.lower() in m.__class__.__name__.lower()), None)
            if not module:
                matches = difflib.get_close_matches(args, names, n=1, cutoff=0.3)
                if matches:
                    module = next((m for m in modules if m.__class__.__name__ == matches[0]), None)
            if not module:
                return await utils.answer(message, f"Module '{args}' not found.")
            module_name = module.__class__.__name__
            origin = module.__origin__
            smile = "📦" if origin != "<core>" else "🔧"
            text = f"<b>{smile} {module_name}:</b>\n"
            for cmd, func in module.commands.items():
                desc = getattr(func, "__doc__", None) or self.get(f"{cmd}cmd_doc") or ""
                desc = desc.strip().replace("\n", " ") if desc else ""
                text += f"• <code>{cmd}</code> {desc}\n"
            return await utils.answer(message, text)

        for module in modules:
            module_name = module.__class__.__name__
            origin = module.__origin__

            if module_name == "HelpMod":
                continue

            if core and origin != "<core>":
                continue

            smile = "📦" if origin != "<core>" else "🔧"

            commands = " | ".join(
                f"<code>{cmd}</code>" for cmd in module.commands.keys()
            )
            text = f"<b>{smile} {module_name}:</b> {commands}"

            all_text += text + "\n"

        await utils.answer(message, all_text)

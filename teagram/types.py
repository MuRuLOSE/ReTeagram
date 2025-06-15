from typing import List, Dict, Final, Any, Optional
import types
from .client import CustomClient
from .database import Database
from .translator import Translator, ModuleTranslator
from importlib.abc import SourceLoader
from abc import ABC, abstractmethod


class ABCLoader(ABC):
    """
    Abstract base loader for modules.
    """

    def __init__(self, client: CustomClient, database: Database):
        self.client: CustomClient = client
        self.database: Database = database

        self.modules: List[Module] = []
        self.core_modules: Final[List[str]] = []

        self.commands: Dict[str, types.FunctionType] = {}
        self.aliases: Dict[str, types.FunctionType] = {}

        self.raw_handlers: List[types.FunctionType] = []
        self.watchers: List[types.FunctionType] = []

        self.inline_handlers: Dict[str, types.FunctionType] = {}
        self.callback_handlers: Dict[str, types.FunctionType] = {}

        self.message_handlers: List[types.FunctionType] = []

        self.dispatcher: Any = None
        self.inline_dispatcher: Any = None

        self.translator: Translator = None

    @abstractmethod
    async def load_module(self, *args, **kwargs):
        pass

    @abstractmethod
    async def unload_module(self, *args, **kwargs):
        pass

    @abstractmethod
    def prepare_module(self, *args, **kwargs):
        pass


class ModuleException(Exception):
    """Base exception for module errors."""

    pass


class ModuleVersionException(Exception):
    """Exception for module version mismatch."""

    pass


class Module:
    """
    Base class for all modules.
    """

    MIN_VERSION: str = "BETA"
    MODULE_VERSION: str = "Not specified"

    translator: ModuleTranslator

    def get(self, key: str) -> Optional[str]:
        return self.translator.get(key)

    def load_init(self):
        self.commands = get_methods(self, "cmd", "is_command")
        self.watchers = get_methods(self, "watcher", "is_watcher")

        self.inline_handlers = get_methods(self, "_inline_handler", "is_inline_handler")
        self.callback_handlers = get_methods(
            self, "_callback_handler", "is_callback_handler"
        )

        self.raw_handlers = get_methods(self, "raw_handler", "is_raw_handler")
        self.message_handlers = list(
            get_methods(self, "_message_handler", "is_message_handler").values()
        )

    async def on_load(self):
        pass

    async def on_unload(self):
        pass


class StringLoader(SourceLoader):
    """
    Loads Python source code from a string.
    """

    def __init__(self, data: str, origin: str) -> None:
        self.data = data.encode("utf-8")
        self.origin = origin

    def get_code(self, full_name: str):
        source = self.get_source(full_name)
        if source:
            return compile(source, self.origin, "exec", dont_inherit=True)
        return None

    def get_filename(self, _: str) -> str:
        return self.origin

    def get_data(self, _: str) -> bytes:
        return self.data


def get_methods(cls, end: str, attribute: str = "") -> Dict[str, types.FunctionType]:
    """
    Collects methods from a class by suffix or attribute.
    """
    methods = {}
    for method_name in dir(cls):
        method = getattr(cls, method_name)
        if callable(method) and (
            method_name.endswith(end) or hasattr(method, attribute)
        ):
            key = method_name.replace(end, "")
            methods[key] = method
    return methods

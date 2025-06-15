from os import listdir
import yaml
from typing import Dict, Optional, Any

SUPPORTED_LANGUAGES = [
    lang[:-5] for lang in listdir("teagram/translations") if lang.endswith(".yaml")
]


class Translator:
    """
    Loads and manages translations for the userbot.
    """

    def __init__(self, database: Any):
        self.database = database
        self.translations: Dict[str, Dict[str, str]] = {}

        self.fetch_translations()

    @property
    def language(self) -> str:
        lang = self.database.get("teagram", "language")
        if not lang:
            lang = "en"
            self.database.set("teagram", "language", lang)
        return lang

    @language.setter
    def language(self, lang: str) -> None:
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Invalid language. Supported languages: {', '.join(SUPPORTED_LANGUAGES)}"
            )
        if self.language != lang:
            self.database.set("teagram", "language", lang)
            self.fetch_translations()

    def fetch_translations(self) -> None:
        try:
            with open(
                f"teagram/translations/{self.language}.yaml", encoding="utf-8"
            ) as stream:
                self.translations = yaml.safe_load(stream) or {}
        except FileNotFoundError:
            self.translations = {}

    def get(self, section: str, key: str) -> Optional[str]:
        """Get translation for section/key."""
        return self.translations.get(section, {}).get(key)


class ModuleTranslator:
    """
    Provides translation for a specific module.
    """

    def __init__(
        self,
        module_class: Any,
        translator: Translator,
        module_translations: Optional[Dict[str, str]] = None,
    ):
        self.module_name = (
            module_class.__class__.__name__.lower()
            .replace("mod", "")
            .replace("module", "")
        )

        self.module_translations = module_translations or {}
        if not translator.translations.get(self.module_name):
            self.module_name = self.module_translations.get(
                "name", self.module_name
            ).lower()

        self.translator = translator

    def get(self, key: str) -> Optional[str]:
        """Get translation for a key in this module."""
        translations = self.translator.translations.get(
            self.module_name, self.module_translations
        )
        return translations.get(key) if translations else None

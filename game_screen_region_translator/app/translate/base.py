from __future__ import annotations

from abc import ABC, abstractmethod


class TranslatorProvider(ABC):
    @abstractmethod
    def translate(self, text: str, source_lang: str = "EN", target_lang: str = "RU", **kwargs) -> str:
        raise NotImplementedError

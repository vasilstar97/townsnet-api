from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime


class Cacheable(ABC):
    @abstractmethod
    def to_file(self, path: Path, name: str, date: datetime, *args) -> None:
        pass

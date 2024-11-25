from io import BytesIO
from pathlib import Path
from datetime import datetime

from app.common.storage.interfaces import Cacheable


class CacheableBytes(Cacheable):
    """
    Cacheable implementation for BytesIO type
    """
    def __init__(self, bytesio: BytesIO):
        self.bytes: BytesIO = bytesio

    def to_file(self, path: Path, name: str, date: datetime, *args) -> None:
        with open(path / f'{date.strftime("%Y-%m-%d-%H-%M-%S")}_{name}', "wb") as fout:
            fout.write(self.bytes.getvalue())

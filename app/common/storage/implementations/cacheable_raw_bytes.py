from pathlib import Path
from datetime import datetime
from app.common.storage.interfaces import Cacheable

class CacheablePythonBytes(Cacheable):
    """
    Cacheable implementation for raw byte data.
    This class is responsible for saving byte data directly to a file.
    """
    def __init__(self, data: bytes):
        self.data = data

    def to_file(self, path: Path, name: str, date: datetime, *args) -> None:
        filepath = f"{date.strftime('%Y-%m-%d-%H-%M-%S')}_{name}"
        for arg in args:
            filepath += f"_{arg}"
        filepath += ".pkl"
        full_path = path / filepath
        with open(full_path, "wb") as fout:
            fout.write(self.data)
from pathlib import Path
from datetime import datetime

from app.common.config.config import config
from app.common.storage.interfaces import Cacheable
from app.common.exceptions.http_exception_wrapper import http_exception


class CachingService:
    def __init__(self, cache_path: Path):
        self.cache_actuality_hours = int(config.get("CACHE_ACTUALITY_HOURS"))
        self.cache_path = cache_path
        self.cache_path.mkdir(parents=True, exist_ok=True)

    def save(self, cacheable: Cacheable, name: str, date: datetime, *args) -> None:
        cacheable.to_file(self.cache_path, name, date, *args)

    def get_cached_file_name(self, name: str) -> str:
        # Get list of files with pattern *{name}
        files = [file.name for file in self.cache_path.glob(f"*{name}")]
        if len(files) == 0:
            return ""
        elif len(files) > 1:
            raise http_exception(
                500,
                "Several instances of file in cache directory, manual conflict resolution required",
                [name, len(files)]
            )

        # Only 1 instance of file can be in cache directory
        file = files[0]
        return file

    def get_file_meta(self, name: str) -> str:
        file = self.get_cached_file_name(name)

        # Save format is {date}_{name}
        # Split with "_" with always result in {date} in position 0
        file_creation_date = file.split("_")[0]
        return file_creation_date

    def retrieve_cached_file(self, pattern: str, ext: str, *args) -> str:
        """
        Get filename of the most recent file created of such type

        :param pattern: rather a name of a file
        :param ext: extension of a file
        :param args: specification for a file to distinguish between

        :return: filename of the most recent file created of such type if it's in the span of actuality
        """
        files = [file.name for file in self.cache_path.glob(f"*{pattern}{''.join([f'_{arg}' for arg in args])}{ext}")]
        files.sort(reverse=True)
        actual_filename: str = ""
        for file in files:
            broken_filename = file.split('_')
            date = datetime.strptime(broken_filename[0], "%Y-%m-%d-%H-%M-%S")
            hours_diff = (datetime.now() - date).total_seconds() // 3600
            if hours_diff < self.cache_actuality_hours:
                actual_filename = file
                print(f"Found cached file - {actual_filename}")
                break
        return actual_filename

caching_service = CachingService(Path().absolute() / config.get("CACHE_NAME"))

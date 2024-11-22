import io

from loguru import logger

from app.common.storage.fileserver import DataGetter
from app.common.storage.interfaces.disposable_interface import IDisposable


class DisposableJSON(IDisposable):
    json: dict | None = None

    def try_init(self, bucket_name: str, object_name: str):
        logger.info(f"Trying to initialize JSON with /{bucket_name}/{object_name}")
        received_bytes: io.BytesIO = DataGetter.get_bytes(bucket_name, object_name)
        if self.json is not None and received_bytes is None:
            logger.info(f"JSON is already initialized with actual data")
            return
        logger.info(f"Loading new JSON")
        self.json = DataGetter.get_json(object_name, received_bytes)
        logger.info(f"JSON is initialized with /{bucket_name}/{object_name}")

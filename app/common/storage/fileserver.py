"""
This module contains queries to the main database in order to get layers with base info.
"""

import io
import json
from pathlib import Path

from minio import Minio
import pandas as pd
from loguru import logger
from pandas import DataFrame

from app.common.storage.caching import caching_service
from app.common.storage.implementations.cacheable_bytes import CacheableBytes
from app.common.config.config import config
from datetime import datetime


class DataGetter:
    """
    This class contains functions for getting layers for local database.
    """
    
    GENERAL_REQ_TIMEOUT = 360

    @staticmethod
    def get_pickle(object_name: str, received_bytes: io.BytesIO | None) -> DataFrame:
        if received_bytes is None:
            received_df = pd.read_pickle(caching_service.cache_path / caching_service.get_cached_file_name(object_name))
            logger.info(f"Loaded pickle from cache - {caching_service.get_cached_file_name(object_name)}")
            return received_df

        caching_service.save(CacheableBytes(received_bytes), object_name, datetime.now())
        received_df = pd.read_pickle(received_bytes)
        logger.info(f"Cached file and loaded pickle from bytes - {object_name}")
        return received_df

    @staticmethod
    def get_json(object_name: str, received_bytes: io.BytesIO | None) -> dict:
        if received_bytes is None:
            with io.open(
                    caching_service.cache_path / caching_service.get_cached_file_name(object_name), encoding="utf-8"
            ) as fin:
                received_json = json.load(fin)
                logger.info(f"Loaded json from cache - {caching_service.get_cached_file_name(object_name)}")
                return received_json

        caching_service.save(CacheableBytes(received_bytes), object_name, datetime.now())
        received_json = json.load(received_bytes)
        logger.info(f"Cached file and loaded json from bytes - {object_name}")
        return received_json

    @staticmethod
    def get_bytes(bucket_name: str, object_name: str) -> io.BytesIO | None:
        client = Minio(
            endpoint=config.get("FILESERVER_ADDR"),
            access_key=config.get("FILESERVER_ACCESS_KEY"),
            secret_key=config.get("FILESERVER_SECRET_KEY"),
            secure=False
        )
        try:
            meta = client.stat_object(
                bucket_name=bucket_name,
                object_name=object_name
            )
        except Exception as e:
            logger.warning(e)
            raise e

        existing_file_date = caching_service.get_file_meta(object_name)

        # Convert server date from UTC to MSK and remove timezone info for type compatibility
        server_file_date = meta.last_modified.astimezone(tz=None).replace(tzinfo=None)

        # If file is not cached or server has newer type of file
        if existing_file_date == "" or (
                server_file_date - datetime.strptime(existing_file_date, "%Y-%m-%d-%H-%M-%S")
        ).total_seconds() > 0:
            logger.info(f"Downloading new file - /{bucket_name}/{object_name}")
            received_bytes = io.BytesIO(client.get_object(
                bucket_name=bucket_name,
                object_name=object_name
            ).data)

            # Delete existing cache to replace with a new one
            if existing_file_date != "":
                logger.info(f"Deleting existing cache - {caching_service.get_cached_file_name(object_name)}")
                Path.unlink(caching_service.cache_path / caching_service.get_cached_file_name(object_name))

            return received_bytes
        return None

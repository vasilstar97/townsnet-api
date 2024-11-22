import io

from geopandas import GeoDataFrame
from loguru import logger
from pyproj import CRS

from app.common.storage.fileserver import DataGetter
from app.common.storage.interfaces.disposable_interface import IDisposable


class DisposableTerritoryGDF(IDisposable):
    gdf: GeoDataFrame | None = None
    local_crs: CRS | None = None

    def try_init(self, bucket_name: str, object_name: str):
        logger.info(f"Trying to initialize Territory GDF with /{bucket_name}/{object_name}")
        received_bytes: io.BytesIO = DataGetter.get_bytes(bucket_name, object_name)
        if self.gdf is not None and received_bytes is None:
            logger.info(f"{object_name} GDF is already initialized with actual data")
            return
        logger.info(f"Loading new pickle into {object_name} GDF")
        gdf = DataGetter.get_pickle(object_name, received_bytes)
        self.gdf = gdf.to_crs(4326)
        self.local_crs = self.gdf.estimate_utm_crs()
        self.gdf.to_crs(self.local_crs, inplace=True)
        logger.info(f"CITY GDF initialized with /{bucket_name}/{object_name}")

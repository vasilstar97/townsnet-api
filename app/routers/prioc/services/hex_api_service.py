from enum import verify

import requests_async as ra
import geopandas as gpd
import pandas as pd

from app.common.exceptions.http_exception_wrapper import http_exception
from app.common.config.config import config
from .constants import LO_HEXES


bucket_name = config.get("FILESERVER_BUCKET_NAME")
lo_hexes_filename= config.get("FILESERVER_LO_NAME")
hexes_attributes_list = [
    "geometry",
    'Показатель: Население',
    'Показатель: Транспорт',
    'Показатель: Экология',
    'Показатель: Социальная обеспеченность',
    'Показатель: Инженерная инфраструктура'
]


class HexApiService:
    """Class for retrieving hexagons necessary data for priority objects calculations"""

    def __init__(
            self,
            base_url=config.get("URBAN_API") + "/api/v1/territory"
    ):
        """
        Initialization function

        Args:
            base_url (string): Base URL for requests

        Returns:
            None
        """
        self.base_url = base_url

    #ToDo Rewrite to urban api
    @staticmethod
    async  def get_hexes_with_indicators_by_territory(territory_id: int) -> gpd.GeoDataFrame:
        """
        Function retrieves hexagons layer with indicators

        Args:
            territory_id (integer): Territory ID

        Returns:
            gpd.GeoDataFrame: Hexagons with indicators values as layers attributes
        """

        if territory_id != 1:
            raise http_exception(
                501,
                "Other territories not supported for now",
                territory_id
            )

        LO_HEXES.try_init(bucket_name, lo_hexes_filename)
        response = LO_HEXES.gdf[hexes_attributes_list]
        return response

    async def get_negative_service_by_territory_id(
            self,
            territory_id: int,
            service_type_ids: list[int],
    ) -> gpd.GeoDataFrame:
        """
        Function retrieves negative services layer

        Args:
            territory_id (integer): Territory ID
            service_type_ids (list[int]): Service type ids for retrieving

        Returns:
            gpd.GeoDataFrame: Services centroids with indicators values as layers attributes
        """

        url = f"{self.base_url}/{territory_id}/services_geojson"
        result_gdf = gpd.GeoDataFrame()

        for service_type_id in service_type_ids:
            current_url = url
            response = await ra.get(
                current_url,
                params={
                    "service_type_id": service_type_id,
                    "cities_only": "false",
                    "centers_only": "true"
                },
                verify=False
            )

            if response.status_code in (200, 201):
                current_gdf = gpd.GeoDataFrame.from_features(response.json())
                result_gdf = pd.concat([result_gdf, current_gdf])
            else:
                raise http_exception(
                    response.status,
                    "Coudn't retrieve exclude objets",
                    response.json())

        result_gdf.set_crs(4326, inplace=True)
        return result_gdf

    async def get_positive_service_by_territory_id(
            self,
            territory_id: int,
            service_type_ids: list[int],
    ) -> gpd.GeoDataFrame:
        """
        Function retrieves positive services layer

        Args:
            territory_id (integer): Territory ID
            service_type_ids (list[str]): Service type ids for retrieving

        Returns:
            gpd.GeoDataFrame: Services centroids with indicators values as layers attributes
        """

        url = f"{self.base_url}/{territory_id}/services_geojson"
        result_gdf = gpd.GeoDataFrame()

        for service_type_id in service_type_ids:
            response = await ra.get(
                url,
                params={
                    "service_type_id": service_type_id,
                    "cities_only": "false",
                    "centers_only": "false"
                },
                verify=False
            )

            if response.status_code in (200, 201):
                current_gdf = gpd.GeoDataFrame.from_features(response.json())
                result_gdf = pd.concat([result_gdf, current_gdf])
            else:
                raise http_exception(
                    response.status,
                    "Coudn't retrieve exclude objets",
                    response.json())

        result_gdf.set_crs(4326, inplace=True)
        return result_gdf


hex_api_getter = HexApiService()

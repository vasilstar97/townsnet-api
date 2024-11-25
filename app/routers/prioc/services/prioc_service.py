import asyncio

import geopandas as gpd
from shapely.geometry import shape

from app.routers.prioc.dto.hexes_dto import HexesDTO
from app.routers.prioc.dto.territory_dto import TerritoryDTO
from .hex_api_service import  hex_api_getter
from .hex_cleaner import hex_cleaner
from .hex_estimator import hex_estimator
from .territory_estimator import territory_estimator
from .constants import POSITIVE_SERVICE_CLEANING, NEGATIVE_SERVICE_CLEANING


class PriocService:
    """Class for handling priority objects calculations"""

    @staticmethod
    async def get_hexes_for_object(
        hex_params: HexesDTO,
    ) -> gpd.GeoDataFrame:
        """
        Generate hexes with estimation for object use

        Args:
            hex_params (HexesDTO): Hexes query parameters

        Returns:
            gpd.GeoDataFrame: Layer with calculated hexes values
        """

        hexes = await hex_api_getter.get_hexes_with_indicators_by_territory(
            hex_params.territory_id
        )
        positive_services_list = POSITIVE_SERVICE_CLEANING.json.get(hex_params.object_type)
        cleaned_hexes = hexes
        if positive_services_list:
            positive_services = await hex_api_getter.get_positive_service_by_territory_id(
                hex_params.territory_id,
                positive_services_list,
            )
            cleaned_hexes = await hex_cleaner.positive_clean(
                cleaned_hexes,
                positive_services
            )
        negative_services_list = NEGATIVE_SERVICE_CLEANING.json.get(hex_params.object_type)
        if negative_services_list:
            negative_services = await hex_api_getter.get_negative_service_by_territory_id(
                hex_params.territory_id,
                negative_services_list
            )

            cleaned_hexes = await hex_cleaner.negative_clean(
                hexes,
                negative_services
            )
        cleaned_hexes = await asyncio.to_thread(
            hex_cleaner.clean_by_min_object_val,
            hexagons=cleaned_hexes,
            object_name=hex_params.object_type,
        )

        estimated_hexes = await hex_estimator.weight_hexes(
            cleaned_hexes,
            hex_params.object_type
        )

        return estimated_hexes

    async def get_hex_clusters_for_object(
            self,
            hex_params: HexesDTO,
    ) -> gpd.GeoDataFrame:
        """
        Generate hex clusters with estimation for object use

        Args:
            hex_params (HexesDTO): Hexes query parameters

        Returns:
            gpd.GeoDataFrame: Layer with calculated hex clusters
        """

        estimated_hexes = await self.get_hexes_for_object(
            hex_params
        )
        clustered_hexes = await hex_estimator.cluster_hexes(
            estimated_hexes
        )

        return clustered_hexes

    @staticmethod
    async def get_territory_estimation(
            territory_params: TerritoryDTO,
    ) -> dict[str, float]:
        """
        Generates territory evaluation with available objects

        Args:
            territory_params (TerritoryDTO): Territory query parameters

        Returns:
            dict: Dictionary with calculated territory values
        """
        territory = gpd.GeoDataFrame([1], geometry=[shape(territory_params.territory.model_dump())], crs=4326)
        territory.to_crs(32636, inplace=True)
        hexagons = await hex_api_getter.get_hexes_with_indicators_by_territory(
            territory_params.territory_id
        )
        hexagons = hexagons.clip(territory.geometry)
        territory_estimation = await territory_estimator.estimate_territory(
            hexagons
        )

        for key in list(territory_estimation.keys()):
            positive_services_ids = POSITIVE_SERVICE_CLEANING.json.get(key)
            negative_services_ids = NEGATIVE_SERVICE_CLEANING.json.get(key)
            if positive_services_ids:
                positive_services = await hex_api_getter.get_positive_service_by_territory_id(
                    territory_params.territory_id,
                    positive_services_ids
                )
            else:
                positive_services = None
            if negative_services_ids:
                negative_services = await hex_api_getter.get_negative_service_by_territory_id(
                    territory_params.territory_id,
                    negative_services_ids
                )
            else:
                negative_services = None

            check_result = await hex_cleaner.clean_estimation_dict_by_territory(
                territory,
                positive_services,
                negative_services
            )
            if check_result:
                del territory_estimation[key]

        return territory_estimation


prioc_service = PriocService()

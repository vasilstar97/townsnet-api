import geopandas as gpd
import pandas as pd

from .constants import OBJECT_INDICATORS_MIN_VAL


class HexCleaner:
    """
    Class for cleaning hex data from inappropriate hexagons.
    """

    @staticmethod
    async def negative_clean(
            hexagons: gpd.GeoDataFrame,
            negative_services: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        """
        Function cleans data from neighbour hexes containing services

        Args:
            hexagons (gpd.GeoDataFrame): hexes
            negative_services (gpd.GeoDataFrame): services to exclude

        Returns:
            gpd.GeoDataFrame: cleaned hexes
        """

        negative_services.to_crs(32636, inplace=True)
        if negative_services.empty:
            return hexagons

        negative_services["is_service"] = 1
        service_hexes = hexagons.sjoin(negative_services)
        service_hexes = service_hexes[service_hexes["is_service"] == 1].drop_duplicates("geometry")
        drop_list = service_hexes.index.to_list()

        for index, row in service_hexes.iterrows():
            current_hex_geom = row['geometry']
            neighbours = hexagons[current_hex_geom.touches(hexagons.geometry)]
            drop_list = drop_list + neighbours.index.to_list()

        drop_list = list(set(drop_list))
        cleaned = hexagons[~hexagons.index.isin(drop_list)]
        return cleaned

    @staticmethod
    async def positive_clean(
            hexagons: gpd.GeoDataFrame,
            positive_objects: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        """
        Function cleans data from neighbour hexes not containing objects

        Args:
            hexagons (gpd.GeoDataFrame): hexes
            positive_objects (gpd.GeoDataFrame): objects to include

        Returns:
            gpd.GeoDataFrame: cleaned hexes
        """

        cleaned_hexes = gpd.sjoin(positive_objects, hexagons, how='right')
        cleaned_hexes.dropna(subset="type_name", inplace=True)

        return cleaned_hexes

    @staticmethod
    async def clean_estimation_dict_by_territory(
            territory: gpd.GeoDataFrame,
            positive_services: gpd.GeoDataFrame | None,
            negative_services: gpd.GeoDataFrame | None,
    ) -> bool:
        """
        Function cleans estimations from inappropriate evaluations

        Args:
            territory (gpd.GeoDataFrame): territory hexes united in one polygon
            positive_services (gpd.GeoDataFrame): services which must be included
            negative_services (gpd.GeoDataFrame): services to exclude

        Returns:
            bool: Drop key or not
        """

        if isinstance(positive_services, gpd.GeoDataFrame):
            positive_services.to_crs(32636, inplace=True)
            positive_services["is_service"] = 1
            check = territory.sjoin(positive_services)
            if not check[check["is_service"] == 1].empty:
                return True
        if isinstance(negative_services, gpd.GeoDataFrame):
            negative_services.to_crs(32636, inplace=True)
            negative_services["is_service"] = 1
            check = territory.sjoin(negative_services)
            if not check[check["is_service"] == 1].empty:
                return True
        return False

    @staticmethod
    def clean_by_min_object_val(
            hexagons: gpd.GeoDataFrame,
            object_name: str
    ) -> gpd.GeoDataFrame:
        """
        Deletes hexagons with tiny indicators values

        Args:
            hexagons (gpd.GeoDataFrame): hexes
            object_name (str): object name

        Returns:
            gpd.GeoDataFrame: cleaned hexes
        """

        def clean_row(
                row: pd.Series,
                min_map: dict[str, int],
        ) -> bool:

            for key in list(min_map.keys()):
                if row[key] < min_map[key]:
                    return False
            return True

        values = OBJECT_INDICATORS_MIN_VAL.json[object_name]
        hexagons["mask"] = hexagons.apply(clean_row, min_map=values, axis=1)
        hexagons = hexagons[hexagons["mask"] > 0].drop("mask", axis=1)
        return hexagons


hex_cleaner = HexCleaner()

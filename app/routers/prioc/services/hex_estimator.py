import asyncio

import geopandas as gpd
import numpy as np
import hdbscan
import networkx as nx
import pandas as pd

from .constants import INDICATORS_WEIGHTS


class HexEstimator:
    """
    Class for calculating priority objects values in hexes
    """

    def __init__(self):
        """
        Initialisation function for HexEstimator
        """

        self.clusterer = hdbscan.HDBSCAN(
            min_cluster_size=3,
            min_samples=3,
            max_cluster_size=15
        )

    @staticmethod
    async def weight_hexes(
            hexagons: gpd.GeoDataFrame,
            service_name: str
    ) -> gpd.GeoDataFrame:
        """
        Function calculates hexagons weighted estimation for provided service

        Args:
            hexagons (gpd.GeoDataFrame): GeoDataFrame with acceptable hexagons
            service_name (str): Name of service

        Returns:
            gpd.GeoDataFrame: GeoDataFrame with weighted hexagons
        """

        hexagons["weighted_estimation"] = None
        indicators_names = list(INDICATORS_WEIGHTS.json[service_name].keys())
        ranks = INDICATORS_WEIGHTS.json[service_name]
        n = len(ranks)
        weights = {}
        for indicator, rank in ranks.items():
            denominator = sum([n - rank + 1 for rank in ranks.values()])
            weights[indicator] = (n - rank + 1) / denominator
        for index, row in hexagons.iterrows():
            total_score = 0
            for indicator_name in row.keys():
                if indicator_name in indicators_names:
                    weight = weights[indicator_name]
                    score = row[indicator_name]
                    total_score += score * weight
                    hexagons.at[index, 'weighted_sum'] = total_score

        return hexagons

    @staticmethod
    async def clarify_clusters(
            clustered_hexagons: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Function detects the biggest neighbour group in clusters and unites them in one geometry

        Args:
            clustered_hexagons (gpd.GeoDataFrame): GeoDataFrame with clustered hexagons

        Returns:
            gpd.GeoDataFrame: GeoDataFrame with clear and united clusters
        """

        grouped = gpd.GeoDataFrame()
        for cluster in clustered_hexagons.cluster:
            tmp_gdf = clustered_hexagons[clustered_hexagons.cluster == cluster]
            G = nx.Graph()
            for i, poly in enumerate(tmp_gdf["geometry"]):
                for j, poly2 in enumerate(tmp_gdf["geometry"]):
                    if i != j and poly.touches(poly2):
                        G.add_edge(i, j)

            components = list(nx.connected_components(G))
            largest_component = max(components, key=len)
            largest_geometries = tmp_gdf.iloc[list(largest_component)]
            grouped = pd.concat([grouped, largest_geometries])

        dissolved = grouped.dissolve(by=["cluster"], aggfunc="mean")
        dissolved.drop(columns=["X", "Y"], inplace=True)
        dissolved["cluster"] = dissolved.index.copy()
        dissolved.reset_index(inplace=True, drop=True)
        return dissolved

    async def cluster_hexes(
            self,
            weighted_hexagons: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        """
        Function creates hexagons clusters with provided weighted estimations

        Args:
            weighted_hexagons (gpd.GeoDataFrame): GeoDataFrame with acceptable hexagons
            with weighted estimations

        Returns:
            gpd.GeoDataFrame: GeoDataFrame with hexagons united in clusters
        """

        weighted_hexagons.to_crs(3857, inplace=True)
        weighted_hexagons["X"] = weighted_hexagons.centroid.x
        weighted_hexagons["Y"] = weighted_hexagons.centroid.y
        X = np.hstack([weighted_hexagons[["X", "Y", "weighted_sum"]].values])
        weighted_hexagons["cluster"] = await asyncio.to_thread(self.clusterer.fit_predict, X=X)
        united_clusters = await self.clarify_clusters(weighted_hexagons)
        return united_clusters


hex_estimator = HexEstimator()

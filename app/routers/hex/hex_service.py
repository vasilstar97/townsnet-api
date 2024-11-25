import geopandas as gpd
from townsnet.potential.grid_generator import GridGenerator
from ...utils import api_client

async def _fetch_region_gdf(region_id : int):
    regions = await api_client.get_regions(True)
    return regions[regions.index == region_id]

async def generate_hex_grid(region_id : int) -> gpd.GeoDataFrame:
    region_gdf = await _fetch_region_gdf(region_id)
    gg = GridGenerator()
    return gg.run(region_gdf)
import requests_async as ra
import pandas as pd
import geopandas as gpd

DEFAULT_CRS = 4326
URBAN_API = 'http://10.32.1.107:5300'

async def get_territories(parent_id : int | None = None, all_levels = False, geometry : bool = False) -> pd.DataFrame | gpd.GeoDataFrame:
  res = await ra.get(URBAN_API + f'/api/v1/all_territories{"" if geometry else "_without_geometry"}', {
    'parent_id': parent_id,
    'get_all_levels': all_levels
  })
  res_json = res.json()
  if geometry:
    gdf = gpd.GeoDataFrame.from_features(res_json, crs=DEFAULT_CRS)
    return gdf.set_index('territory_id', drop=True)
  df = pd.DataFrame(res_json)
  return df.set_index('territory_id', drop=True)

async def get_regions(geometry : bool = False) -> gpd.GeoDataFrame:
  countries = await get_territories()
  countries_ids = countries.index
  countries_regions = [await get_territories(country_id, geometry=geometry) for country_id in countries_ids]
  return pd.concat(countries_regions)

# async def get_region_territories(region_id : int) -> dict[int, gpd.GeoDataFrame]:
#   res = await ra.get(URBAN_API + '/api/v1/all_territories', {
#       'parent_id': region_id,
#       'get_all_levels': True
#   })
#   gdf = gpd.GeoDataFrame.from_features(res.json()['features'], crs=DEFAULT_CRS)
#   df = pd.json_normalize(gdf['territory_type']).rename(columns={
#       'name':'territory_type_name'
#   })
#   gdf = pd.DataFrame.join(gdf, df).set_index('territory_id', drop=True)
#   return {level:gdf[gdf['level'] == level] for level in set(gdf.level)}

async def get_service_types(territory_id : int) -> list[dict]:
  res = await ra.get(URBAN_API + f'/api/v1/territory/{territory_id}/service_types')
  return res.json()

async def get_normatives(territory_id : int) -> list[dict]:
  res = await ra.get(URBAN_API + f'/api/v1/territory/{territory_id}/normatives')
  return res.json()

async def get_normative_service_types(territory_id : int) -> list[dict]:
  service_types = await get_service_types(territory_id)
  normatives = await get_normatives(territory_id)
  return [{**st, 'normatives': filter(lambda n : n['service_type']['id'] == st['service_type_id'], normatives)} for st in service_types]
  # normatives = await _get_normatives(region_id)
  # return pd.merge(service_types, normatives, left_index=True, right_on='service_type_id')
import os
import shapely
import json
import requests_async as ra
import pandas as pd
import geopandas as gpd

DEFAULT_CRS = 4326
URBAN_API = os.environ['URBAN_API'] if 'URBAN_API' in os.environ else 'http://10.32.1.107:5300' 
TRANSPORT_FRAMES_API = os.environ['TRANSPORT_FRAMES_API'] if 'TRANSPORT_FRAMES_API' in os.environ else "http://10.32.1.65:5700" 
PAGE_SIZE = 10_000
POPULATION_COUNT_INDICATOR_ID = 1
GRAPH_TYPE = 'inter'

async def get_accessibility_matrix(region_id : int):
    res = await ra.get(f'{TRANSPORT_FRAMES_API}/api_v1/{region_id}/get_matrix', {
        'graph_type': GRAPH_TYPE
    })
    res_json = res.json()
    return pd.DataFrame(res_json['values'], index=res_json['index'], columns=res_json['columns'])

async def _get_physical_objects(region_id : int, pot_id : int, page : int, page_size : int = PAGE_SIZE):
    res = await ra.get(f'{URBAN_API}/api/v1/territory/{region_id}/physical_objects_with_geometry', {
        'physical_object_type_id': pot_id,
        'page': page,
        'page_size': page_size,
    })
    return res.json()

async def get_physical_objects(region_id : int, pot_id : int) -> gpd.GeoDataFrame | None:
    page = 1
    results = []
    while True:
        res_json = await _get_physical_objects(region_id, pot_id, page, page_size=PAGE_SIZE)
        results.extend(res_json['results'])
        if res_json['next'] is None:
            break
        page += 1
    #recovering geometries
    for result in results:
        g = result['geometry']
        result['geometry'] = shapely.from_geojson(json.dumps(g))
    if len(results) > 0:
        return gpd.GeoDataFrame(results, crs=DEFAULT_CRS).set_index('physical_object_id')
    return None

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

async def get_territories_population(territories_gdf : gpd.GeoDataFrame, regional_scenario_id : int | None = None):
    res = await ra.get(f'{URBAN_API}/api/v1/indicator/{POPULATION_COUNT_INDICATOR_ID}/values')
    res_df = pd.DataFrame(res.json())
    res_df = res_df[res_df['territory_id'].isin(territories_gdf.index)]
    res_df = res_df.groupby('territory_id').agg({'value': 'last'}).rename(columns={'value':'population'})
    return territories_gdf[['geometry']].merge(res_df, how='left', left_index=True, right_index=True)

async def get_service_type_capacities(territory_id : int, level : int, service_type_id : int) -> list[dict[str, int]]:
    res = await ra.get(URBAN_API + f'/api/v1/territory/{territory_id}/services_capacity', {
        'level': level,
        'service_type_id': service_type_id
    })
    return res.json()

async def get_regions(geometry : bool = False) -> gpd.GeoDataFrame:
    countries = await get_territories()
    countries_ids = countries.index
    countries_regions = [await get_territories(country_id, geometry=geometry) for country_id in countries_ids]
    return pd.concat(countries_regions)

async def get_service_types(territory_id : int) -> list[dict]:
    res = await ra.get(URBAN_API + f'/api/v1/territory/{territory_id}/service_types')
    return res.json()

async def get_normatives(territory_id : int) -> list[dict]:
    res = await ra.get(URBAN_API + f'/api/v1/territory/{territory_id}/normatives')
    return res.json()

async def get_physical_objects_types() -> list[dict]:
    res = await ra.get(URBAN_API + '/api/v1/physical_object_types')
    return res.json()

async def get_indicators():
    res = await ra.get(URBAN_API + '/api/v1/indicators_by_parent', {'get_all_subtree':True})
    return res.json()
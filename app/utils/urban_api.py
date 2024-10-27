import shapely
import json
import requests_async as ra
import pandas as pd
import geopandas as gpd
from townsnet.provision.service_type import ServiceType

DEFAULT_CRS = 4326
URBAN_API = 'http://10.32.1.107:5300'
PAGE_SIZE = 10_000

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

async def get_normative_service_types(territory_id : int) -> dict[int, ServiceType]:
    #prepare service types
    service_types = pd.DataFrame(await get_service_types(territory_id)).set_index('service_type_id')
    service_types['weight'] = service_types['properties'].apply(lambda p : p['weight_value'] if 'weight_value' in p else 0)
    service_types['category'] = service_types['infrastructure_type'].apply(str.upper)
    #prepare normatives
    normatives = pd.DataFrame(await get_normatives(territory_id))
    normatives['service_type_id'] = normatives['service_type'].apply(lambda st : st['id'])
    #merge one another
    service_types_instances = ServiceType.initialize_service_types(service_types, normatives)
    return {sti.id : sti for sti in service_types_instances}

async def get_service_type_capacities(territory_id : int, level : int, service_type_id : int) -> list[dict[str, int]]:
    res = await ra.get(URBAN_API + f'/api/v1/territory/{territory_id}/services_capacity', {
        'level': level,
        'service_type_id': service_type_id
    })
    return res.json()

async def get_physical_objects_types() -> list[dict]:
    res = await ra.get(URBAN_API + '/api/v1/physical_object_types')
    return res.json()

async def get_indicators():
    res = await ra.get(URBAN_API + '/api/v1/indicators_by_parent', {'get_all_subtree':True})
    return res.json()
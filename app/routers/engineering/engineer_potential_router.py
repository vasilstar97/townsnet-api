from fastapi import APIRouter, HTTPException, Depends, Query
import json
from townsnet.engineering.engineer_potential import InfrastructureAnalyzer
import requests
import geopandas as gpd
import shapely
import json
import pandas as pd
from typing import Any, Dict

engineer_potential_router = APIRouter(prefix="/engineer_potential", tags=["engineer"])

from enum import Enum
class EngineeringObject(Enum):
    POWER_SUPPLY = 'Энергоснабжение'
    HEAT_SUPPLY = 'Теплоснабжение'
    GAS_SUPPLY = 'Газоснабжение'
    WATER_SUPPLY = 'Водоснабжение'
    WATER_DRAINAGE = 'Водоотведение'

ENG_OBJ = {
    EngineeringObject.POWER_SUPPLY: [14, 20, 21, 33, 34, 35],  # Электрические подстанции, ЛЭП, электростанции и генераторы
    EngineeringObject.HEAT_SUPPLY: [41],                       # Котельная
    EngineeringObject.GAS_SUPPLY: [13, 18],                    # Магистральный газопровод
    EngineeringObject.WATER_SUPPLY: [27, 38, 40, 42],          # Сети водоснабжения, водонапорные башни, водозаборные и насосные станции
    EngineeringObject.WATER_DRAINAGE: [24, 37, 39]             # Сети водоотведения, сооружения для очистки воды, водоочистные сооружения
}

URBAN_API = 'http://10.32.1.107:5300'
PAGE_SIZE = 10_000

def _get_physical_objects(region_id : int, pot_id : int, page : int, page_size : int = PAGE_SIZE):
    res = requests.get(f'{URBAN_API}/api/v1/territory/{region_id}/physical_objects_with_geometry', {
    'physical_object_type_id': pot_id,
    'page': page,
    'page_size': page_size,
    })
    return res.json()

def get_physical_objects(region_id: int, pot_id: int):
    page = 1
    results = []
    results_with_geometry = [] 

    while True:
        res_json = _get_physical_objects(region_id, pot_id, page, page_size=PAGE_SIZE)
        results.extend(res_json['results'])
        if res_json['next'] is None:
            break
        page += 1

    results_with_geometry = [result for result in results if 'geometry' in result and result['geometry'] is not None]

    if not results_with_geometry:
        return gpd.GeoDataFrame(columns=['geometry'])

    for result in results_with_geometry:
        g = result['geometry']
        result['geometry'] = shapely.from_geojson(json.dumps(g))

    return gpd.GeoDataFrame(results_with_geometry).set_geometry('geometry')

def fetch_required_objects(region_id : int, pot_ids : list[int]):
    gdfs = [get_physical_objects(region_id, pot_id) for pot_id in pot_ids]
    return pd.concat(gdfs).set_geometry('geometry').set_crs(4326)

def get_engineering_gdf(data_dict: dict) -> gpd.GeoDataFrame:
    combined_gdf = gpd.GeoDataFrame(columns=['type', 'geometry'], crs="EPSG:4326")

    for eng_obj, gdf in data_dict.items():
        gdf = gdf.copy()  
        gdf['type'] = eng_obj.value 
        combined_gdf = pd.concat([combined_gdf, gdf], ignore_index=True)

    combined_gdf = gpd.GeoDataFrame(combined_gdf, geometry='geometry', crs="EPSG:4326")
    return combined_gdf


@engineer_potential_router.post("/test_engineer_potential", response_model=Dict[str, Any])
async def test_population_criterion_endpoint(region_id : int):
    try:
        gdfs = {}
        for eng_obj, ind_id in ENG_OBJ.items():
            if len(ind_id) > 0:
                gdf = fetch_required_objects(region_id, ind_id)
                gdfs[eng_obj] = gdf
        combined_gdf = get_engineering_gdf(gdfs)
        spb_hex = gpd.read_file('/Users/mvin/Code/townsnet-api/spb_hex.geojson')
        analyzer = InfrastructureAnalyzer(combined_gdf, spb_hex)
        results = analyzer.get_results()
        return json.loads(results.to_json())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
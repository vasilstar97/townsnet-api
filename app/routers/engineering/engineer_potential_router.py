from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Header,  Request
import json
from townsnet.engineering.engineer_potential import InfrastructureAnalyzer
import requests
import geopandas as gpd
import shapely
import json
import pandas as pd
from typing import Any, Dict
from loguru import logger
from datetime import datetime

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


@engineer_potential_router.post("/engineer_potential_hex", response_model=list[float])
async def engineer_potential_hex_endpoint(region_id : int, geojson_data: dict,):
    try:
        gdfs = {}
        for eng_obj, ind_id in ENG_OBJ.items():
            if len(ind_id) > 0:
                gdf = fetch_required_objects(region_id, ind_id)
                gdfs[eng_obj] = gdf
        combined_gdf = get_engineering_gdf(gdfs)

        if geojson_data.get("type") != "FeatureCollection":
            raise HTTPException(status_code=400, detail="Неверный формат GeoJSON, ожидался FeatureCollection")
        
        polygon_gdf = gpd.GeoDataFrame.from_features(geojson_data["features"], crs=4326)
        polygon_gdf = polygon_gdf.to_crs(combined_gdf.crs)
        analyzer = InfrastructureAnalyzer(combined_gdf, polygon_gdf)

        results = analyzer.get_results()
        if results.empty:
            raise HTTPException(status_code=404, detail="Результаты не найдены")
            
        scores = [float(res['score']) for res in results.to_dict('records')]
        return scores

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def process_engineer(
    region_id: int,
    project_scenario_id: int,
    token: str
):
    try:
        # Getting project_id and additional information based on scenario_id
        scenario_response = requests.get(
            f"{URBAN_API}/api/v1/scenarios/{project_scenario_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        if scenario_response.status_code != 200:
            raise Exception("Error retrieving scenario information")
        
        scenario_data = scenario_response.json()
        project_id = int(scenario_data.get("project_id"))  # Convert to standard int
        
        # Retrieving territory geometry
        territory_response = requests.get(
            f"{URBAN_API}/api/v1/projects/{project_id}/territory",
            headers={"Authorization": f"Bearer {token}"}
        )
        if territory_response.status_code != 200:
            raise Exception("Error retrieving territory geometry")
        
        # Extracting only the polygon geometry
        territory_data = territory_response.json()
        territory_geometry = territory_data["geometry"]

        # Converting the territory geometry to GeoDataFrame
        territory_feature = {
            'type': 'Feature',
            'geometry': territory_geometry,
            'properties': {}
        }
 
        gdfs = {}
        for eng_obj, ind_id in ENG_OBJ.items():
            if len(ind_id) > 0:
                gdf = fetch_required_objects(region_id, ind_id)
                gdfs[eng_obj] = gdf
        combined_gdf = get_engineering_gdf(gdfs)
        
        polygon_gdf = gpd.GeoDataFrame.from_features([territory_feature], crs=4326)
        polygon_gdf = polygon_gdf.to_crs(combined_gdf.crs)
        analyzer = InfrastructureAnalyzer(combined_gdf, polygon_gdf)

        results = analyzer.get_results()

        # Saving the evaluation to the database
        for res in results:
            indicator_data = {
                "scenario_id": project_scenario_id,  # Add scenario_id
                "indicator_id": 204,
                "date_type": "year",
                "date_value": datetime.now().strftime("%Y-%m-%d"),
                "value": float(res['score']),
                "value_type": "real",
                "information_source": "modeled"
            }

            indicators_response = requests.post(
                f"{URBAN_API}/api/v1/scenarios/{project_scenario_id}/indicators_values",
                headers={"Authorization": f"Bearer {token}"},
                json=indicator_data
            )
            if indicators_response.status_code not in (200, 201):  # Successful codes: 200 and 201
                logger.error(f"Error saving indicators: {indicators_response.status_code}, "
                             f"Response body: {indicators_response.text}")
                raise Exception("Error saving indicators")
    except Exception as e:
        logger.error(f"Error in the evaluation process: {e}")

@engineer_potential_router.post("/save_engineer_potential")
async def save_engineer_potential_endpoint(
    region_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    project_scenario_id: int | None = Query(None, description="Project scenario ID, if available"),
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization token is missing or invalid")
    
    token = auth_header.split(" ")[1]
    # Add a background task that will be executed after the response is returned
    background_tasks.add_task(process_engineer, region_id, project_scenario_id, token)
    
    # Instantly return a message indicating that processing has started
    return {"message": "Population criterion processing started", "status": "processing"}
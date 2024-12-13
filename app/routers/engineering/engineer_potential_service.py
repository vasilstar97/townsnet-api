import requests
import geopandas as gpd
import shapely
import pandas as pd
from typing import Any, Dict
from loguru import logger
import json
from enum import Enum
from townsnet.engineering.engineer_potential import InfrastructureAnalyzer
from ...utils.const import URBAN_API

# Enums for engineering object types
class EngineeringObject(Enum):
    POWER_SUPPLY = 'Энергоснабжение'
    HEAT_SUPPLY = 'Теплоснабжение'
    GAS_SUPPLY = 'Газоснабжение'
    WATER_SUPPLY = 'Водоснабжение'
    WATER_DRAINAGE = 'Водоотведение'

PAGE_SIZE = 10_000

ENG_OBJ = {
    EngineeringObject.POWER_SUPPLY: [
        14, 20, 21, 33, 34, 35, 12, 53 # Электрические подстанции, ЛЭП, электростанции, генераторы, и объекты электроснабжения
    ],
    EngineeringObject.HEAT_SUPPLY: [
        41, 11, 56, 58  # Котельная и объекты теплоснабжения
    ],
    EngineeringObject.GAS_SUPPLY: [
        13, 18, 59  # Магистральные газопроводы, объекты добычи и транспортировки газа
    ],
    EngineeringObject.WATER_SUPPLY: [
        27, 38, 40, 42, 13  # Сети водоснабжения, водонапорные башни, водозаборные и насосные станции
    ],
    EngineeringObject.WATER_DRAINAGE: [
        24, 37, 39, 14  # Сети водоотведения, сооружения для очистки воды, водоочистные сооружения
    ]
}
# Utility Functions
def fetch_physical_objects(region_id: int, pot_id: int, page: int, page_size: int = PAGE_SIZE):
    response = requests.get(
        f'{URBAN_API}/api/v1/territory/{region_id}/physical_objects_with_geometry',
        params={'physical_object_type_id': pot_id, 'page': page, 'page_size': page_size}
    )
    response.raise_for_status()
    return response.json()

def get_physical_objects(region_id: int, pot_id: int):
    results = []
    page = 1
    while True:
        data = fetch_physical_objects(region_id, pot_id, page)
        results.extend(data['results'])
        if data['next'] is None:
            break
        page += 1

    results_with_geometry = [
        {**result, 'geometry': shapely.from_geojson(json.dumps(result['geometry']))}
        for result in results if result.get('geometry')
    ]

    if not results_with_geometry:
        return gpd.GeoDataFrame(columns=['geometry'])

    return gpd.GeoDataFrame(results_with_geometry).set_geometry('geometry').set_crs(4326)

def fetch_required_objects(region_id: int, pot_ids: list[int]):
    gdfs = [get_physical_objects(region_id, pot_id) for pot_id in pot_ids]
    return pd.concat(gdfs).set_geometry('geometry').set_crs(4326)

def combine_engineering_gdfs(data_dict: Dict[EngineeringObject, gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
    combined_gdf = gpd.GeoDataFrame(columns=['type', 'geometry'], crs="EPSG:4326")
    for eng_obj, gdf in data_dict.items():
        gdf['type'] = eng_obj.value
        combined_gdf = pd.concat([combined_gdf, gdf], ignore_index=True)
    return combined_gdf

def retrieve_project_and_territory(project_scenario_id: int, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    
    scenario_response = requests.get(f"{URBAN_API}/api/v1/scenarios/{project_scenario_id}", headers=headers)
    scenario_response.raise_for_status()
    scenario_data = scenario_response.json()
    project_id = scenario_data.get("project", {}).get("project_id")
    if project_id is None:
        raise Exception("Project ID is missing in scenario data.")
    
    territory_response = requests.get(f"{URBAN_API}/api/v1/projects/{project_id}/territory", headers=headers)
    territory_response.raise_for_status()
    territory_geometry = territory_response.json()["geometry"]
    
    return territory_geometry

def analyze_and_save_results(analyzer: InfrastructureAnalyzer, project_scenario_id: int, token: str):
    results = analyzer.get_results()
    for res in results.to_dict("records"):
        indicator_data = {
            "indicator_id": 204,
            "scenario_id": project_scenario_id,
            "territory_id": None,
            "hexagon_id": None,
            "value": float(res['score']),
            "comment": '_',
            "information_source": "modeled",
             "properties": {
                "attribute_name": "Обеспечение инженерной инфраструктурой"
            }
        }

        response = requests.put(
            f"{URBAN_API}/api/v1/scenarios/indicators_values",
            headers={"Authorization": f"Bearer {token}"},
            json=indicator_data
        )
        if response.status_code not in (200, 201):
            logger.error(f"Error saving indicators: {response.status_code}, Response body: {response.text}")
            raise Exception("Error saving indicators")

async def process_engineer(region_id: int, project_scenario_id: int, token: str):
    try:
        territory_geometry = retrieve_project_and_territory(project_scenario_id, token)
        gdfs = {eng_obj: fetch_required_objects(region_id, pot_ids) for eng_obj, pot_ids in ENG_OBJ.items()}
        combined_gdf = combine_engineering_gdfs(gdfs)
        territory_feature = {
            'type': 'Feature',
            'geometry': territory_geometry,
            'properties': {}
        }
        polygon_gdf = gpd.GeoDataFrame.from_features([territory_feature], crs=4326)
        polygon_gdf = polygon_gdf.to_crs(combined_gdf.crs)
        analyzer = InfrastructureAnalyzer(combined_gdf, polygon_gdf)
        analyze_and_save_results(analyzer, project_scenario_id, token)
    except Exception as e:
        logger.error(f"Error during engineer processing: {e}")

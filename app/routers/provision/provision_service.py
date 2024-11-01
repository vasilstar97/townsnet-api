import os
import numpy as np
import geopandas as gpd
import pandas as pd
from statistics import mean
from loguru import logger
from townsnet.provision.service_type import ServiceType, SupplyType, Category
from townsnet.provision.provision_model import ProvisionModel
from townsnet.provision.social_model import SocialModel
from shapely import Polygon, MultiPolygon
from ...utils import api_client
from ...utils.const import DATA_PATH

CATEGORIES_WEIGHTS = {
    Category.BASIC: 3,
    Category.ADDITIONAL : 1,
    Category.COMFORT : 1
}

async def fetch_service_types(region_id : int) -> dict[int, ServiceType]:
    """
    Fetch region specific service types with normatives
    """
    #prepare service types
    service_types = pd.DataFrame(await api_client.get_service_types(region_id)).set_index('service_type_id')
    service_types['weight'] = service_types['properties'].apply(lambda p : p['weight_value'] if 'weight_value' in p else 0)
    service_types['category'] = service_types['infrastructure_type']
    #prepare normatives
    normatives = pd.DataFrame(await api_client.get_normatives(region_id))
    normatives['service_type_id'] = normatives['service_type'].apply(lambda st : st['id'])
    #merge one another
    service_types_instances = ServiceType.initialize_service_types(service_types, normatives)
    return {sti.id : sti for sti in service_types_instances}

async def fetch_territories(region_id : int, regional_scenario_id : int | None = None, population : bool = True, geometry = True) -> tuple[dict[int, gpd.GeoDataFrame], gpd.GeoDataFrame]:
    """
    Fetch region territories for specific regional_scenario with population (optional) and geometry (optional)
    """
    # fetch region
    regions_gdf = await api_client.get_regions(geometry)
    region_gdf = regions_gdf[regions_gdf.index == region_id]
    units_gdfs = {2 : region_gdf}
    # fetch towns
    territories_gdf = await api_client.get_territories(region_id, all_levels = True, geometry=geometry)
    territories_gdf['was_point'] = territories_gdf['properties'].apply(lambda p : p['was_point'] if 'was_point' in p else False)
    #filter towns gdf
    towns_gdf = territories_gdf[territories_gdf['was_point']]
    if population:
        towns_gdf = await api_client.get_territories_population(towns_gdf)
        towns_gdf['population'] = towns_gdf['population'].fillna(0)
    #filter units gdf
    units_gdf = territories_gdf[~territories_gdf['was_point']]
    levels = units_gdf['level'].unique()
    # fetch population
    for level in levels:
        units_gdfs[level] = units_gdf[units_gdf.level == level]
    return units_gdfs, towns_gdf

async def fetch_levels(region_id : int) -> dict[int, str]:
    """
    Fetch region levels
    """
    units_gdfs, _ = await fetch_territories(region_id, population=False, geometry=False)
    levels = {}
    for level, gdf in units_gdfs.items():
        gdf['territory_type_name'] = gdf['territory_type'].apply(lambda tt : tt['name'])
        ttn = max(gdf['territory_type_name'].unique(), key=lambda ttn : len(gdf[gdf['territory_type_name'] == ttn]))
        levels[level] = ttn
    return levels

async def fetch_acc_mx(region_id : int, regional_scenario_id : int | None = None) -> pd.DataFrame:
    """
    Fetch region accessibility matrix from Transport Frames
    """
    acc_mx = await api_client.get_accessibility_matrix(region_id)
    return acc_mx

async def fetch_supplies(region_id : int, service_type : ServiceType):
    level = 5
    while level>0:
        supplies = await api_client.get_service_type_capacities(region_id, level, service_type.id)
        if len(supplies) == 0:
            level -= 1
        else:
            break
    supplies_df = pd.DataFrame(supplies).set_index('territory_id')
    if service_type.supply_type == SupplyType.CAPACITY_PER_1000:
        supplies_df['supply'] = supplies_df['capacity']
    else:
        supplies_df['supply'] = supplies_df['count']
    return supplies_df

def merge_provisions(provisions : dict[int, gpd.GeoDataFrame], service_types : list[ServiceType]):
    provision = list(provisions.values())[0][['geometry']].copy()
    for st in service_types:
        prov_gdf = provisions[st.id]
        provision[st.name] = prov_gdf['provision']
    provision['provision'] = provision.apply(lambda s : mean([s[st.name] for st in service_types if not np.isnan(s[st.name])]), axis=1)
    return provision

def _get_file_path(region_id : int, service_type_id : int, regional_scenario_id : int | None = None):
    file_path = f'{region_id}_{service_type_id}'
    if regional_scenario_id is not None:
        file_path = f'{file_path}_{regional_scenario_id}'
    return os.path.join(DATA_PATH, f'{file_path}.parquet')

async def _exists(region_id : int, service_type_id : int, regional_scenario_id : int | None = None):
    return os.path.exists(_get_file_path(region_id, service_type_id, regional_scenario_id))

async def load(region_id : int, service_type_id : int, regional_scenario_id : int | None = None):
    file_path = _get_file_path(region_id, service_type_id, regional_scenario_id)
    return gpd.read_parquet(file_path)

async def _save(provision_gdf : gpd.GeoDataFrame, region_id : int, service_type_id : int, regional_scenario_id : int | None = None):
    file_path = _get_file_path(region_id, service_type_id, regional_scenario_id)
    provision_gdf.to_parquet(file_path)

async def evaluate_and_save_region(region_id : int, regional_scenario_id : int | None = None):
    logger.info(f'Fetching {region_id} region service types')
    region_service_types = await fetch_service_types(region_id)
    candidate_service_types = []
    for service_type_id, service_type in region_service_types.items():
        # если сервиса не существует, добавляем его в кандидаты на вычисление
        if not await _exists(region_id, service_type_id, regional_scenario_id):
            candidate_service_types.append(service_type)
    if len(candidate_service_types) == 0:
        logger.success('All service types are evaluated')
        return
    # инициализируем модельку
    logger.info(f'Initializing {region_id} region provision model')
    try:
        acc_mx = await fetch_acc_mx(region_id, regional_scenario_id)
    except:
        raise Exception(f'Problem with accessibility matrix for {region_id}')
    _, towns_gdf = await fetch_territories(region_id, regional_scenario_id) # TODO добавить агрегацию по юнитам
    if len(towns_gdf) == 0:
        raise Exception(f'No towns found for {region_id}')
    provision_model = ProvisionModel(towns_gdf, acc_mx, verbose = False)
    # для каждого ненайденного типа сервисов цепляем емкости и считаем обеспеченность
    for service_type in candidate_service_types:
        logger.info(f'Evaluating {service_type.id} service_type provision')
        supplies_df = await fetch_supplies(region_id, service_type)
        provision = provision_model.calculate(supplies_df, service_type)
        # и сохраняем их на будущее
        await _save(provision, region_id, service_type.id, regional_scenario_id)

def evaluate_social_indicator(social_model : SocialModel, project_geometry : Polygon | MultiPolygon):
    
    # calculating max possible scores
    service_types = social_model.provisions.keys()
    max_possible_scores = {}
    for category in list(Category):
        category_service_types = filter(lambda st : st.category == category, service_types)
        max_possible_score = sum(st.weight for st in  category_service_types)
        max_possible_scores[category] = max_possible_score

    # evaluate context provisions
    evaluations = social_model.evaluate_provisions(project_geometry)
    evaluations_df = pd.DataFrame([{
        'id' : st.id,
        'weight': st.weight,
        'category': st.category.name,
        'provision': prov
    } for st, prov in evaluations.items()]).set_index('id', drop=True)
    evaluations_df['score'] = evaluations_df['provision']*evaluations_df['weight']
    
    # aggregate by category
    categories_dfs = {category : evaluations_df[evaluations_df['category'] == category.name] for category in list(Category)}
    categories_scores = {category : CATEGORIES_WEIGHTS[category]*(category_df['score'].sum())/max_possible_scores[category] for category, category_df in categories_dfs.items()}

    return round(sum(categories_scores.values()))

async def evaluate_project(region_id : int, project_geometry : Polygon | MultiPolygon):
    ...

async def evaluate_and_save_project(region_id : int, project_scenario_id : int):
    ...

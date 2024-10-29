import geopandas as gpd
import pandas as pd
import os
from loguru import logger
from fastapi import APIRouter, HTTPException, Depends
from townsnet.provision.service_type import ServiceType, Category, SupplyType
from townsnet.provision.provision_model import ProvisionModel
from ...utils import urban_api, decorators
from ...utils.const import DATA_PATH

async def on_startup():
    ...

async def on_shutdown():
    ...

router = APIRouter(prefix='/provision', tags=['Provision assessment'])

async def _fetch_towns(region_id : int, regional_scenario_id : int | None = None) -> gpd.GeoDataFrame:
    # fetch towns
    logger.info('Fetching towns...')
    territories_gdf = await urban_api.get_territories(region_id, all_levels = True, geometry=True)
    levels = territories_gdf['level'].unique()
    max_level = max(levels)
    territories_gdf = territories_gdf[territories_gdf['level'] == max_level]
    # fetch population
    logger.info('Fetching population...')
    territories_gdf = await urban_api.get_territories_population(territories_gdf)
    return territories_gdf

async def _fetch_acc_mx(region_id : int, regional_scenario_id : int | None = None) -> gpd.GeoDataFrame:
    if region_id == 1:
        return pd.read_pickle(os.path.join(DATA_PATH, 'acc_mx.pickle'))
    raise HTTPException(404, 'Sorry the matrix is not ready yet')

async def _prepare_model(region_id : int, regional_scenario_id : int | None = None) -> ProvisionModel:
    # towns_gdf = pd.read_parquet(os.path.join(DATA_PATH, f'towns_{region_id}.parquet'))
    towns_gdf = await _fetch_towns(region_id, regional_scenario_id)
    acc_mx = await _fetch_acc_mx(region_id, regional_scenario_id)
    return ProvisionModel(towns_gdf, acc_mx)

@router.get('/categories')
async def get_categories() -> dict[str, str]:
    return {cat.name:cat.value for cat in Category}


@router.get('/{region_id}/levels')
async def get_levels(region_id : int) -> dict[int, str]:
    regions = await urban_api.get_regions()
    territories_gdf = await urban_api.get_territories(region_id, all_levels = True)
    levels = {
        2 : regions.loc[region_id, 'territory_type']['name']
    }
    for level, gdf in territories_gdf.groupby('level'):
        gdf['territory_type_name'] = gdf['territory_type'].apply(lambda tt : tt['name'])
        ttn = max(gdf['territory_type_name'].unique(), key=lambda ttn : len(gdf[gdf['territory_type_name'] == ttn]))
        levels[level] = ttn
    return levels

@router.get('/{region_id}/service_types')
async def get_service_types(region_id : int) -> list[ServiceType]:
    service_types = await urban_api.get_normative_service_types(region_id)
    return list(service_types.values())

@router.get('/{region_id}/calculate')
@decorators.gdf_to_geojson
async def get_calculate(region_id : int, service_type_id : int, regional_scenario_id : int | None = None):
    #fetch normative service types
    logger.info('Fetching service types...')
    service_types = await urban_api.get_normative_service_types(region_id)
    if service_type_id not in service_types:
        raise HTTPException(404, 'There is no normatives for service type with such an id')
    service_type = service_types[service_type_id]
    #prepare a model
    provision_model = await _prepare_model(region_id, regional_scenario_id)
    #hoho
    logger.info('Fetching capacities...')
    supplies_df = await urban_api.get_service_type_capacities(region_id, 5, service_type_id)
    if service_type.supply_type == SupplyType.CAPACITY_PER_1000:
        supplies_df['supply'] = supplies_df['capacity']
    else:
        supplies_df['supply'] = supplies_df['count']
    return provision_model.calculate(supplies_df, service_type)
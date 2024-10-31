import geopandas as gpd
import pandas as pd
import os
from loguru import logger
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from townsnet.provision.service_type import ServiceType, Category, SupplyType
from townsnet.provision.provision_model import ProvisionModel
from pydantic_geojson import PolygonModel, MultiPolygonModel
from ...utils import decorators, api_client
from ...utils.const import DATA_PATH, EVALUATION_RESPONSE_MESSAGE
from . import provision_service, provision_models

async def on_startup():
    logger.info('Fetching regions')
    regions_df = await api_client.get_regions()
    for region_id in regions_df.index:
        if region_id != 1 : continue # TODO убрать когда появятся другие регионы
        try:
            await provision_service.evaluate_and_save(region_id)
        except Exception as e:
            logger.error(e)

async def on_shutdown():
    ...

router = APIRouter(prefix='/provision', tags=['Provision assessment'])

@router.get('/categories')
async def get_categories() -> dict[str, str]:
    return {cat.name:cat.value for cat in Category}

@router.get('/{region_id}/levels')
async def get_levels(region_id : int) -> dict[int, str]:
    return await provision_service.fetch_levels(region_id)

@router.get('/{region_id}/service_types')
async def get_service_types(region_id : int) -> list[ServiceType]:
    service_types = await provision_service.fetch_service_types(region_id)
    return list(service_types.values())

@router.get('/{region_id}/get_evaluation')
@decorators.gdf_to_geojson
async def get_evaluation(region_id : int, level : int | None = None, category : Category | None = None, service_type_id : int | None = None, regional_scenario_id : int | None = None) -> provision_models.ProvisionModel :
    # fetch service types
    logger.info(f'Fetching service types for {region_id}')
    service_types = list((await provision_service.fetch_service_types(region_id)).values())
    if service_type_id is not None:
        service_types = [st for st in service_types if st.id == service_type_id]
    elif category is not None:
        service_types = [st for st in service_types if st.category == category]
    
    #load provisions
    logger.info(f'Loading indicators for {region_id}')
    provisions = {st.id : await provision_service._load(region_id, st.id, regional_scenario_id) for st in service_types}

    #aggregate if needed
    if level is not None:
        #fetch territories
        logger.info('Loading territories to aggregate')
        units_gdfs, towns_gdf = await provision_service.fetch_territories(region_id)
        units_gdf = units_gdfs[level][['geometry']]
        logger.info('Aggregating')
        provisions = {st.id : ProvisionModel.agregate(towns_gdf, units_gdf) for st in service_types}

    # merge service types provisions if required
    if len(service_types) > 1:
        provision = provision_service.merge_provisions(provisions, service_types)
    else:
        provision = list(provisions.values())[0]

    return provision

@router.post('/{region_id}/evaluate_geojson')
async def evaluate_geojson(region_id : int, regional_scenario_id : int | None = None):
    return 'not ready yet'

@router.post('/{region_id}/evaluate_region')
async def evaluate_region(background_tasks : BackgroundTasks, region_id : int, regional_scenario_id : int | None = None) -> str:
    background_tasks.add_task(provision_service.evaluate_and_save, region_id, regional_scenario_id)
    return EVALUATION_RESPONSE_MESSAGE

@router.post('/{region_id}/evaluate_project')
async def evaluate_project(background_tasks : BackgroundTasks, region_id : int, project_scenario_id : int):
    return EVALUATION_RESPONSE_MESSAGE
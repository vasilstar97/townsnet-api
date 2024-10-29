import geopandas as gpd
import pandas as pd
import os
from loguru import logger
from fastapi import APIRouter, HTTPException, Depends
from townsnet.provision.service_type import ServiceType, Category, SupplyType
from townsnet.provision.provision_model import ProvisionModel
from pydantic_geojson import PolygonModel, MultiPolygonModel
from ...utils import decorators
from ...utils.const import DATA_PATH, EVALUATION_RESPONSE_MESSAGE
from . import provision_service, provision_models

async def on_startup():
    ...

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
    #fetch territories
    units_gdfs, towns_gdf = await provision_service.fetch_territories(region_id)
    units_gdf = units_gdfs[level][['geometry']] if level is not None else None
    # fetch acc_mx
    acc_mx = await provision_service.fetch_acc_mx(region_id)
    # fetch service types
    service_types = list((await provision_service.fetch_service_types(region_id)).values())
    if service_type_id is not None:
        service_types = [st for st in service_types if st.id == service_type_id]
    elif category is not None:
        service_types = [st for st in service_types if st.category == category]
    # init model and evaluate provision
    provision_model = ProvisionModel(towns_gdf, acc_mx, verbose = False)
    provisions = {st.id : await provision_service.evaluate(provision_model, region_id, st, units_gdf) for st in service_types}

    # aggregate service types provisions if needed
    if len(service_types) > 1:
        provision = provision_service.merge_provisions(provisions)
    else:
        provision = list(provisions.values())[0]

    return provision

@router.post('/{region_id}/evaluate_geojson')
async def evaluate_geojson(region_id : int, regional_scenario_id : int | None = None):
    return EVALUATION_RESPONSE_MESSAGE

@router.post('/{region_id}/evaluate_region')
async def evaluate_region(region_id : int, regional_scenario_id : int | None = None):
    return EVALUATION_RESPONSE_MESSAGE

@router.post('/{region_id}/evaluate_project')
async def evaluate_project(region_id : int, project_polygon : PolygonModel | MultiPolygonModel, project_scenario_id : int, regional_scenario_id : int | None, ):
    return EVALUATION_RESPONSE_MESSAGE
import geopandas as gpd
from loguru import logger
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from townsnet.provision.service_type import ServiceType, Category
from townsnet.provision.provision_model import ProvisionModel
from app.common.utils import decorators, api_client
from app.common.config.config import config
from . import provision_service, provision_models


EVALUATION_RESPONSE_MESSAGE = config.get("EVALUATION_RESPONSE_MESSAGE")



async def on_startup():
    logger.info('Fetching regions')
    regions_df = await api_client.get_regions()
    for region_id in regions_df.index:
        if region_id != 1 : continue # TODO убрать когда появятся другие регионы
        try:
            await provision_service.evaluate_and_save_region(region_id)
        except Exception as e:
            logger.error(e)

async def on_shutdown():
    ...

router = APIRouter(prefix='/provision', tags=['Provision assessment'])

@router.get('/categories')
async def get_categories() -> list[Category]:
    return Category

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
    provisions = {st.id : await provision_service.load(region_id, st.id, regional_scenario_id) for st in service_types}

    #aggregate if needed
    if level is not None:
        #fetch territories
        logger.info('Fetching territories to aggregate')
        units_gdfs, _ = await provision_service.fetch_territories(region_id)
        units_gdf = units_gdfs[level][['geometry']]
        logger.info('Aggregating')
        for st in service_types:
            provision =  provisions[st.id]
            provision.index.name = '' # FIXME doesnt work without that
            provisions[st.id] = ProvisionModel.agregate(provision, units_gdf)

    # merge service types provisions if required
    if len(service_types) > 1:
        provision = provision_service.merge_provisions(provisions, service_types)
    else:
        provision = list(provisions.values())[0]

    return provision

@router.post('/{region_id}/get_evaluation')
async def get_geojson_evaluation(region_id : int, geojson : provision_models.GridInputModel, regional_scenario_id : int | None = None) -> list[int]:
    
    grid_gdf = gpd.GeoDataFrame.from_features([f.model_dump() for f in geojson.features], crs=4326)

    social_model = provision_service.fetch_social_model(region_id, regional_scenario_id)

    logger.info('Evaluating social score for each cell')
    return grid_gdf.geometry.apply(lambda g : provision_service.evaluate_social(social_model, g)[0])

def _get_token_from_request(request : Request) -> str:
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing",
        )
    # Проверяем формат: заголовок должен начинаться с 'Bearer '
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=400,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )
    
    token = auth_header[len("Bearer "):]

    if not token:
        raise HTTPException(
            status_code=400,
            detail="Token is missing in the authorization header"
        )
    
    return token

@router.post('/{region_id}/evaluate_region')
async def evaluate_region(request : Request, background_tasks : BackgroundTasks, region_id : int, regional_scenario_id : int | None = None) -> str:
    background_tasks.add_task(provision_service.evaluate_and_save_region, region_id, regional_scenario_id, _get_token_from_request(request))
    return EVALUATION_RESPONSE_MESSAGE

@router.post('/{region_id}/evaluate_project')
async def evaluate_project(request : Request, background_tasks : BackgroundTasks, region_id : int, project_scenario_id : int):
    background_tasks.add_task(provision_service.evaluate_and_save_project, region_id, project_scenario_id, _get_token_from_request(request))
    return EVALUATION_RESPONSE_MESSAGE
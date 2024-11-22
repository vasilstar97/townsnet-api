from fastapi import APIRouter
from pydantic_geojson import PolygonModel, MultiPolygonModel
from app.common.utils import decorators
from app.common.config.config import config
from . import engineering_service, engineering_models


EVALUATION_RESPONSE_MESSAGE = config.get("EVALUATION_RESPONSE_MESSAGE")


async def on_startup():
    ...

async def on_shutdown():
    ...

router = APIRouter(prefix='/engineering', tags=['Engineering assessment'])

@router.get('/indicators')
async def get_indicators() -> list[engineering_models.Indicator]:
    indicators = await engineering_service.get_indicators()
    return indicators

@router.get('/{region_id}/levels')
async def get_levels(region_id : int) -> dict[int, str]:
    levels = await engineering_service.fetch_levels(region_id)
    return levels

@router.get('/{region_id}/get_evaluation')
@decorators.gdf_to_geojson
async def get_evaluation(region_id : int, level : int) -> engineering_models.EngineeringModel :
    engineering_model = await engineering_service.fetch_engineering_model(region_id)
    units = await engineering_service.fetch_units(region_id, level)
    return engineering_service.aggregate(engineering_model, units)

@router.post('/{region_id}/evaluate_geojson')
async def evaluate_geojson(region_id : int, regional_scenario_id : int | None = None):
    return EVALUATION_RESPONSE_MESSAGE

@router.post('/{region_id}/evaluate_region')
async def evaluate_region(region_id : int, regional_scenario_id : int | None = None):
    return EVALUATION_RESPONSE_MESSAGE

@router.post('/{region_id}/evaluate_project')
async def evaluate_project(region_id : int, project_polygon : PolygonModel | MultiPolygonModel, project_scenario_id : int, regional_scenario_id : int | None, ):
    return EVALUATION_RESPONSE_MESSAGE

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from townsnet.engineering.engineer_potential import InfrastructureAnalyzer
from pydantic_geojson import FeatureCollectionModel, PolygonModel, MultiPolygonModel
from ...utils import decorators
from . import engineering_service, engineering_models, engineer_potential_service
from ...utils.const import EVALUATION_RESPONSE_MESSAGE
from app.utils.auth import verify_token 
import geopandas as gpd
from loguru import logger

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

@router.post("/{region_id}/evaluate_region")
async def evaluate_region_endpoint(
    region_id: int,
    regional_scenario_id: int | None = None,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    background_tasks.add_task(engineering_service.process_region_evaluation, region_id, regional_scenario_id, token)
    return EVALUATION_RESPONSE_MESSAGE


@router.post('/{region_id}/evaluate_geojson')
async def engineer_potential_hex_endpoint(region_id: int, geojson_data: dict):
    try:
        gdfs = {eng_obj: engineer_potential_service.fetch_required_objects(region_id, pot_ids) for eng_obj, pot_ids in engineer_potential_service.ENG_OBJ.items()}
        combined_gdf = engineer_potential_service.combine_engineering_gdfs(gdfs)

        if geojson_data.get("type") != "FeatureCollection":
            raise HTTPException(status_code=400, detail="Invalid GeoJSON format. Expected FeatureCollection.")

        polygon_gdf = gpd.GeoDataFrame.from_features(geojson_data["features"], crs=4326).to_crs(combined_gdf.crs)
        analyzer = InfrastructureAnalyzer(combined_gdf, polygon_gdf)
        results = analyzer.get_results()
        if results.empty:
            raise HTTPException(status_code=404, detail="No results found.")
        
        return [float(res['score']) for res in results.to_dict('records')]
    except Exception as e:
        logger.error(f"Error in engineer potential calculation: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post('/{region_id}/evaluate_project')
async def save_engineer_potential_endpoint(region_id: int, background_tasks: BackgroundTasks, project_scenario_id: int, token: str = Depends(verify_token)):
    
    background_tasks.add_task(engineer_potential_service.process_engineer, region_id, project_scenario_id, token)
    return EVALUATION_RESPONSE_MESSAGE
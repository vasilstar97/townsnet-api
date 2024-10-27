from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from townsnet.provision.service_type import ServiceType, Category
from ..utils import urban_api, decorators

router = APIRouter(prefix='/provision', tags=['Provision assessment'])

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
    return [st for st in service_types.values()]
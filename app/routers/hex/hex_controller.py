from fastapi import APIRouter, HTTPException, Depends
from ...utils import decorators
from . import hex_service, hex_models

async def on_startup():
    ...

async def on_shutdown():
    ...

router = APIRouter(prefix='/hex', tags=['Hex grid generator'])

@router.get('/generate')
@decorators.gdf_to_geojson
async def generate_hex_grid(region_id : int) -> hex_models.HexGridModel:
    hex_grid = await hex_service.generate_hex_grid(region_id)
    return hex_grid

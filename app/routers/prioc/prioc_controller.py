from typing import Annotated

from fastapi import APIRouter, Depends
from typing import Annotated

from .dto import HexesDTO, TerritoryDTO
from app.utils import decorators

router = APIRouter(prefix="/prioc", tags=["Priority object calculation"])


@router.get("/object")
@decorators.gdf_to_geojson
async def get_object_hexes(
        hex_params: HexesDTO = Annotated[HexesDTO, Depends(HexesDTO)]
) -> dict:
    """
    Calculate hexes to place priority objects with estimation value
    """

    return hex_params.__dict__

@router.get("/cluster")
@decorators.gdf_to_geojson
async def get_hexes_clusters(
        hex_params: HexesDTO = Annotated[HexesDTO, Depends(HexesDTO)]
) -> dict:
    """
    Calculate hexes clusters to place priority objects with estimation value
    """

    return get_object_hexes.__dict__

@router.post("/territory")
@decorators.gdf_to_geojson
async def get_territory_value(
        territory_params: TerritoryDTO = Annotated[TerritoryDTO, Depends(TerritoryDTO)]
) -> dict:
    """
    Calculate possible priority objects allocation
    """

    return territory_params.__dict__

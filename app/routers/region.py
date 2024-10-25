from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from townsnet.potential.grid_generator import GridGenerator
from pydantic_geojson import FeatureCollectionModel, FeatureModel, PolygonModel
from ..utils import urban_api, decorators
import json

router = APIRouter(prefix='/region')

class PotentialFeatureProperties(BaseModel):
  ...
class PotentialFeatureModel(FeatureModel):
  geometry : PolygonModel
  properties : PotentialFeatureProperties

class PotentialModel(FeatureCollectionModel):
  features : list[PotentialFeatureModel]

@router.get('/{region_id}/levels')
async def get_levels(region_id : int) -> dict:
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
async def get_service_types(region_id : int) -> list:
  service_types = await urban_api.get_normative_service_types(region_id)
  return service_types

@router.get('/{region_id}/potential')
@decorators.gdf_to_geojson
async def get_potential(region_id : int) -> PotentialModel:
  regions = await urban_api.get_regions(True)
  region = regions[regions.index == region_id]
  gg = GridGenerator()
  grid = gg.run(region)
  return grid




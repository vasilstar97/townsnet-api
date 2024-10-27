import pandas as pd
import geopandas as gpd
import functools
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from townsnet.engineering.engineering_model import EngineeringModel, EngineeringObject
from pydantic_geojson import FeatureCollectionModel
from ..utils import urban_api, decorators

router = APIRouter(prefix='/engineering', tags=['Engineering assessment'])

class PhysicalObjectType(BaseModel):
    physical_object_type_id : int
    name : str

class Indicator(BaseModel):
    indicator_id : int
    name_full : str
    name_short : str
    physical_objects_types : list[PhysicalObjectType]

ENG_OBJ_POTS = {
    EngineeringObject.ENGINEERING_OBJECT: [],
    EngineeringObject.POWER_PLANTS: [21, 33, 34, 35],
    EngineeringObject.WATER_INTAKE: [38, 40],
    EngineeringObject.WATER_TREATMENT: [37, 39],
    EngineeringObject.WATER_RESERVOIR: [],
    EngineeringObject.GAS_DISTRIBUTION: [],
}

ENG_OBJ_INDICATOR = {
  EngineeringObject.ENGINEERING_OBJECT : 88,
  EngineeringObject.POWER_PLANTS : 89,
  EngineeringObject.WATER_INTAKE : 90,
  EngineeringObject.WATER_TREATMENT : 91,
  EngineeringObject.WATER_RESERVOIR : 92,
  EngineeringObject.GAS_DISTRIBUTION : 93
}

async def _prepare_model(region_id : int) -> EngineeringModel:
    eng_objs_queries = {}
    #sending queries
    for eng_obj, pots_ids in ENG_OBJ_POTS.items():
        eng_obj_queries = []
        for pot_id in pots_ids:
            pot_query = urban_api.get_physical_objects(region_id, pot_id)
            eng_obj_queries.append(pot_query)
        if len(eng_obj_queries) > 0:
            eng_objs_queries[eng_obj] = eng_obj_queries
    #awaiting queries'
    gdfs = {}
    for eng_obj, queries in eng_objs_queries.items():
        if len(queries)>0:
            queries_gdfs = [await query for query in queries]
            gdf = pd.concat(queries_gdfs)
            gdfs[eng_obj] = gdf

    return EngineeringModel(gdfs)

async def _prepare_units(region_id : int, level : int) -> gpd.GeoDataFrame:
    if level == 2: #return region gdf
        territories_gdf = await urban_api.get_regions(True)
        territories_gdf = territories_gdf[territories_gdf.index == region_id]
    else: #return certain gdf
        territories_gdf = await urban_api.get_territories(region_id, all_levels = True, geometry=True)
        territories_gdf = territories_gdf[territories_gdf['level'] == level]
    return territories_gdf

@router.get('/indicators')
async def get_indicators() -> list[Indicator]:
    indicators_pots = {ENG_OBJ_INDICATOR[eng_obj]: ENG_OBJ_POTS[eng_obj] for eng_obj in list(EngineeringObject)}
    indicators_df = pd.DataFrame(await urban_api.get_indicators()).set_index('indicator_id')
    physical_objects_types_df = pd.DataFrame(await urban_api.get_physical_objects_types()).set_index('physical_object_type_id')
    indicators = []
    for ind_id, pots_array in indicators_pots.items():
        physical_objects_types = [PhysicalObjectType(
            physical_object_type_id=pot_id,
            **(physical_objects_types_df.loc[pot_id].to_dict())
        ) for pot_id in pots_array]
        indicator = Indicator(
            indicator_id=ind_id,
            physical_objects_types=physical_objects_types,
            **(indicators_df.loc[ind_id].to_dict())
        )
        indicators.append(indicator)
    return indicators

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

@router.get('/{region_id}/aggregate')
# @decorators.gdf_to_geojson
async def aggregate(region_id : int, level : int, regional_scenario_id : int | None = None) -> dict[int, dict[int, int]]:
    engineering_model = _prepare_model(region_id)
    units = _prepare_units(region_id, level)
    agg = (await engineering_model).aggregate(await units)
    return {i : {ENG_OBJ_INDICATOR[eng_obj] : agg.loc[i, eng_obj.value] for eng_obj in list(EngineeringObject)} for i in agg.index}
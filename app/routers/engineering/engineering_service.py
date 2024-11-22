import pandas as pd
import geopandas as gpd
from townsnet.engineering.engineering_model import EngineeringModel, EngineeringObject
from ...utils import api_client
from .engineering_models import Indicator, PhysicalObjectType
from ...utils.const import EVALUATION_RESPONSE_MESSAGE, URBAN_API
from datetime import datetime
import requests
from app.utils.auth import verify_token 
from loguru import logger

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

async def fetch_engineering_model(region_id : int) -> EngineeringModel:
    eng_objs_queries = {}
    #sending queries
    for eng_obj, pots_ids in ENG_OBJ_POTS.items():
        eng_obj_queries = []
        for pot_id in pots_ids:
            pot_query = api_client.get_physical_objects(region_id, pot_id)
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

async def fetch_units(region_id : int, level : int) -> gpd.GeoDataFrame:
    if level == 2: #return region gdf
        territories_gdf = await api_client.get_regions(True)
        territories_gdf = territories_gdf[territories_gdf.index == region_id]
    else: #return certain gdf
        territories_gdf = await api_client.get_territories(region_id, all_levels = True, geometry=True)
        territories_gdf = territories_gdf[territories_gdf['level'] == level]
    return territories_gdf

async def fetch_levels(region_id : int) -> dict[int, str]:
    regions = await api_client.get_regions()
    territories_gdf = await api_client.get_territories(region_id, all_levels = True)
    levels = {
        2 : regions.loc[region_id, 'territory_type']['name']
    }
    for level, gdf in territories_gdf.groupby('level'):
        gdf['territory_type_name'] = gdf['territory_type'].apply(lambda tt : tt['name'])
        ttn = max(gdf['territory_type_name'].unique(), key=lambda ttn : len(gdf[gdf['territory_type_name'] == ttn]))
        levels[level] = ttn
    return levels

async def get_indicators() -> list[Indicator]:
    indicators_pots = {ENG_OBJ_INDICATOR[eng_obj]: ENG_OBJ_POTS[eng_obj] for eng_obj in list(EngineeringObject)}
    indicators_df = pd.DataFrame(await api_client.get_indicators()).set_index('indicator_id')
    physical_objects_types_df = pd.DataFrame(await api_client.get_physical_objects_types()).set_index('physical_object_type_id')
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

def aggregate(engineering_model : EngineeringModel, units : gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    agg = engineering_model.aggregate(units)
    return agg
    # return {i : {ENG_OBJ_INDICATOR[eng_obj] : agg.loc[i, eng_obj.value] for eng_obj in list(EngineeringObject)} for i in agg.index}

async def process_region_evaluation(
    region_id: int, 
    regional_scenario_id: int | None, 
    token: str
):
    try:
        levels = [2]
        indicators = [
            {"indicator_id": 88, "column": None},
            {"indicator_id": 89, "column": "Электростанция"},
            {"indicator_id": 90, "column": "Водозабор"},
            {"indicator_id": 91, "column": "Водоочистительное сооружение"},
            {"indicator_id": 92, "column": "Водохранилище"},
            {"indicator_id": 93, "column": "Газораспределительная станция"}
        ]

        engineering_model = await fetch_engineering_model(region_id)

        for level in levels:
            units = await fetch_units(region_id, level)
            engineer = aggregate(engineering_model, units)
            engineer = engineer.reset_index()  

            for indicator in indicators:
                indicator_id = indicator["indicator_id"]
                column = indicator["column"]

                for _, row in engineer.iterrows():
                    if column:
                        value = float(row.get(column, 0))
                    else:
                        value = sum(
                            float(row.get(col, 0)) for col in [
                                "Электростанция",
                                "Водозабор",
                                "Водоочистительное сооружение",
                                "Водохранилище",
                                "Газораспределительная станция"
                            ]
                        )

                    indicator_data = {
                        "indicator_id": indicator_id,
                        "territory_id": row["territory_id"],
                        "date_type": "year",
                        "date_value": datetime.now().strftime("%Y-%m-%d"),
                        "value": value,
                        "value_type": "real",
                        "information_source": "modeled TownsNet"
                    }
                    print(indicator_data)

                    response = requests.post(
                        f"{URBAN_API}/api/v1/indicator_value",
                        json=indicator_data
                    )

                    if response.status_code not in (200, 201, 500):
                        logger.error(
                            f"Error saving indicators: {response.status_code}, Response body: {response.text}"
                        )
                        raise Exception("Error saving indicators")

    except Exception as e:
        logger.error(f"Error during region evaluation: {e}")
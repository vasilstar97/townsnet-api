import os
import geopandas as gpd
import pandas as pd
from statistics import mean
from townsnet.provision.service_type import ServiceType, SupplyType
from townsnet.provision.provision_model import ProvisionModel
from ...utils import urban_api
from ...utils.const import DATA_PATH

async def fetch_service_types(region_id : int) -> dict[int, ServiceType]:
    #prepare service types
    service_types = pd.DataFrame(await urban_api.get_service_types(region_id)).set_index('service_type_id')
    service_types['weight'] = service_types['properties'].apply(lambda p : p['weight_value'] if 'weight_value' in p else 0)
    service_types['category'] = service_types['infrastructure_type']
    #prepare normatives
    normatives = pd.DataFrame(await urban_api.get_normatives(region_id))
    normatives['service_type_id'] = normatives['service_type'].apply(lambda st : st['id'])
    #merge one another
    service_types_instances = ServiceType.initialize_service_types(service_types, normatives)
    return {sti.id : sti for sti in service_types_instances}

async def fetch_territories(region_id : int, population : bool = True, geometry = True) -> tuple[dict[int, gpd.GeoDataFrame], gpd.GeoDataFrame]:
    # fetch region
    # regions = await urban_api.get_regions(True)
    # region_gdf = regions[regions.index == region_id]
    # units_gdfs = {2 : region_gdf}
    # fetch towns
    territories_gdf = await urban_api.get_territories(region_id, all_levels = True, geometry=geometry)
    territories_gdf['was_point'] = territories_gdf['properties'].apply(lambda p : p['was_point'] if 'was_point' in p else False)
    #filter towns gdf
    towns_gdf = territories_gdf[territories_gdf['was_point']]
    if population:
        towns_gdf = await urban_api.get_territories_population(towns_gdf)
        towns_gdf['population'] = towns_gdf['population'].fillna(0)
    #filter units gdf
    units_gdf = territories_gdf[~territories_gdf['was_point']]
    levels = units_gdf['level'].unique()
    # fetch population
    for level in levels:
        units_gdfs[level] = units_gdf[units_gdf.level == level]
    return units_gdfs, towns_gdf

async def fetch_levels(region_id : int) -> dict[int, str]:
    units_gdfs, _ = await fetch_territories(region_id, False, False)
    levels = {}
    for level, gdf in units_gdfs.items():
        gdf['territory_type_name'] = gdf['territory_type'].apply(lambda tt : tt['name'])
        ttn = max(gdf['territory_type_name'].unique(), key=lambda ttn : len(gdf[gdf['territory_type_name'] == ttn]))
        levels[level] = ttn
    return levels

async def fetch_acc_mx(region_id : int) -> pd.DataFrame:
    if region_id == 1:
        return pd.read_pickle(os.path.join(DATA_PATH, 'acc_mx.pickle'))
    return None

async def fetch_supplies(region_id : int, service_type : ServiceType):
    level = 5
    while level>0:
        supplies = await urban_api.get_service_type_capacities(region_id, level, service_type.id)
        if len(supplies) == 0:
            level -= 1
        else:
            break
    supplies_df = pd.DataFrame(supplies).set_index('territory_id')
    if service_type.supply_type == SupplyType.CAPACITY_PER_1000:
        supplies_df['supply'] = supplies_df['capacity']
    else:
        supplies_df['supply'] = supplies_df['count']
    return supplies_df

async def evaluate(provision_model : ProvisionModel, region_id : int, service_type : ServiceType, units_gdf : gpd.GeoDataFrame | None):
    supplies_df = await fetch_supplies(region_id, service_type)
    provision = provision_model.calculate(supplies_df, service_type)
    if units_gdf is not None:
        return provision_model.agregate(provision, units_gdf)
    return provision

def merge_provisions(provisions : dict[int, gpd.GeoDataFrame]):
    provision = list(provisions.values())[0][['geometry']].copy()
    for st_id, prov_gdf in provisions.items():
        provision[st_id] = prov_gdf['provision']
    provision['provision'] = provision.apply(lambda s : mean([s[st_id] for st_id in provisions.keys()]), axis=1)
    return provision
import os
import pandas as pd
import geopandas as gpd
from statistics import mean
from townsnet import Region, Provision, Territory, SERVICE_TYPES

REGIONS_DICT = {
  1: 'Ленинградская область',
  3138: 'Санкт-Петербург',
  3268: 'Москва',
  3427: 'Волгоградская область',
  3902: 'Тульская область',
  4013: 'Омская область',
  4437: 'Краснодарский край',
  4882: 'Тюменская область',
  5188: 'Московская область',
}

ADMIN_LEVELS = ['districts', 'settlements', 'towns']

DATA_PATH = os.path.abspath('app/data')

def _get_region_data_path(region_id : int):
    return os.path.join(DATA_PATH, str(region_id))

def get_region(region_id : int):
    return Region.from_pickle(os.path.join(_get_region_data_path(region_id), f'{region_id}.pickle'))

def _get_region_provision(region_id : int, admin_level : str):
    data_path = _get_region_data_path(region_id)
    selected_columns = ['geometry', 'town_name' if admin_level == 'towns' else 'name', 'provision']
    gdfs = []
    for service_type in SERVICE_TYPES:
        service_type_name = service_type['name']
        file_path = os.path.join(data_path, f'{service_type_name}_{admin_level}.parquet')
        prov_col = f'provision_{service_type_name}'
        gdf = gpd.read_parquet(file_path)[selected_columns].rename(columns={
            'provision': prov_col,
        })
        if admin_level == 'towns':
            gdf = gdf.rename(columns={'town_name': 'name'})
        gdfs.append(gdf)
    region_gdf = gdfs[0][['geometry', 'name']]
    region_gdf = pd.concat([region_gdf, *[gdf[filter(lambda c : 'provision' in c, gdf.columns)] for gdf in gdfs]], axis=1)
    region_gdf['provision'] = region_gdf[filter(lambda c : 'provision' in c, gdf.columns)].apply(mean, axis=1)
    for service_type in SERVICE_TYPES:
        service_type_name = service_type['name']
        gdf[prov_col] = gdf[prov_col]
    return region_gdf

def provision_exists(region_id : int, service_type_name : str):
    data_path = _get_region_data_path(region_id)
    exists = []
    for admin_level in ADMIN_LEVELS:
        file_path = os.path.join(data_path, f'{service_type_name}_{admin_level}.parquet')
        os.path.exists(file_path)
    return all(exists)

def get_provision(region_id : int, service_type_name : str = None):
    data_path = _get_region_data_path(region_id)

    def read_file(admin_level):
        if service_type_name is None:
            return _get_region_provision(region_id, admin_level)
        return gpd.read_parquet(os.path.join(data_path, f'{service_type_name}_{admin_level}.parquet'))

    return {
        level : read_file(level) for level in ADMIN_LEVELS
    }

def set_provision(region_id : int, service_type_name : str, prov_res : tuple):
    data_path = _get_region_data_path(region_id)
    for level, gdf in zip([*ADMIN_LEVELS], prov_res):
        for column in ['settlement_name', 'district_name']:
            if column in gdf.columns:
                gdf[column] = gdf[column].apply(lambda v : None if v==0 else v)
        gdf.to_parquet(os.path.join(data_path, f'{service_type_name}_{level}.parquet'))
    

print('looking for required precalculated files...')

for region_id in REGIONS_DICT.keys():
    print(f'Region {region_id}...')
    region = get_region(region_id)
    provision = Provision(region=region)

    for service_type in SERVICE_TYPES:
        service_type_name = service_type['name']
        if not provision_exists(region_id, service_type_name):
            print(f'    Calculating {service_type_name}...')
            prov_res = provision.calculate(service_type_name)
            set_provision(region_id, service_type_name, prov_res)
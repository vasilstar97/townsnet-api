import json
import geopandas as gpd
from typing import Annotated, Literal
import numpy as np
from pydantic import BaseModel
from pydantic_geojson import PolygonModel, PointModel, FeatureCollectionModel, FeatureModel
from townsnet import Region, Territory, Provision, ServiceType, Town
from fastapi import FastAPI, Query
from enum import Enum
import os
from shapely import set_precision

app = FastAPI()

#data initialization
data_path = os.path.join(os.getcwd(), 'data')

regions_dict = {
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

# regions = {}
# provisions = {}

# for region_id in regions_dict.keys():
#     region_data_path = f"{data_path}/{region_id}"
#     region = Region.from_pickle(f"{region_data_path}/{region_id}.pickle")

#     regions[region_id] = region
#     provisions[region_id] = {}

#     for service_type in region.service_types:
#         provisions[region_id][service_type.name] = {
#             t : gpd.read_parquet(f"{region_data_path}/provisions/{service_type.name}_{t}.parquet") for t in ['districts', 'settlements', 'towns', 'links']
#         }

#tags
tags_metadata = [
    {"name": "Provision methods", "description": "Region provision assessment methods"},
    {"name": "Territory methods", "description": "Custom territory assessment"},
]

class ProvisionPropertiesModel(BaseModel):
    demand : float
    demand_left : float
    demand_within : float
    demand_without : float
    capacity : float
    capacity_left : float
    capacity_left : float
    provision : float

class ProvisionFeatureModel(FeatureModel):
    geometry : PointModel
    properties : ProvisionPropertiesModel

class ProvisionModel(FeatureCollectionModel):
    features : list[ProvisionFeatureModel]

class AssessmentModel(BaseModel):
    assessment : int
    provisions : dict[str, ProvisionPropertiesModel]

def get_region(region_id):
    region_data_path = os.path.join(data_path, str(region_id))
    return Region.from_pickle(os.path.join(region_data_path, f'{region_id}.pickle'))

def get_provision(region_id, service_type_name):
    region_data_path = os.path.join(data_path, str(region_id))
    provisions_data_path = os.path.join(region_data_path, 'provisions')
    return {
        t : gpd.read_parquet(os.path.join(provisions_data_path, f'{service_type_name}_{t}.parquet')) for t in ['districts', 'settlements', 'towns', 'links']
    }

@app.get("/")
def read_root():
    return {
        'hello': os.getcwd()
    }

# @app.post('/service_types')
# def service_types() -> list[ServiceType]:
#     return region.service_types


@app.get("/provision/region", tags=['Provision assessment'])
def region_provision(
    region_id : int = 1, 
    service_type_name : str = 'school'
): # -> ProvisionModel:
    gdf = get_provision(region_id, service_type_name)['districts']
    gdf = gdf.to_crs(4326)
    gdf.geometry = set_precision(gdf.geometry, grid_size=0.0001)
    gdf['district_id'] = gdf.index
    return {
        'provision': round(gdf.demand_within.sum() / gdf.demand.sum(),2),
        'districts': json.loads(gdf.to_json())
    }

@app.get("/provision/district", tags=['Provision assessment'])
def district_provision(
    region_id : int = 1,
    district_name : str = 'Бокситогорский муниципальный район',
    service_type_name : str = 'school'
): # -> ProvisionModel:
    gdf = get_provision(region_id, service_type_name)['settlements']
    gdf = gdf[gdf.settlement_name == district_name]
    gdf = gdf.to_crs(4326)
    gdf.geometry = set_precision(gdf.geometry, grid_size=0.0001)
    gdf['settlement_id'] = gdf.index
    return {
        'provision': round(gdf.demand_within.sum() / gdf.demand.sum(),2),
        'districts': json.loads(gdf.to_json())
    }

@app.get("/provision/settlement", tags=['Provision assessment'])
def settlement_provision(
    region_id : int = 1,
    settlement_name : str = 'Самойловское сельское поселение',
    service_type_name : str = 'school'
): # -> ProvisionModel:
    gdfs = get_provision(region_id, service_type_name)

    towns_gdf = gdfs['towns']
    towns_gdf = towns_gdf[towns_gdf.settlement_name == settlement_name]
    towns_gdf = towns_gdf.to_crs(4326)
    towns_gdf.geometry = set_precision(towns_gdf.geometry, grid_size=0.0001)
    towns_gdf['town_id'] = towns_gdf.index
    
    links_gdf = gdfs['links']
    links_gdf = links_gdf[links_gdf['from'].isin(towns_gdf.index)]
    links_gdf = links_gdf[links_gdf['to'].isin(towns_gdf.index)]
    links_gdf = links_gdf.to_crs(4326)
    links_gdf.geometry = set_precision(links_gdf.geometry, grid_size=0.0001)

    return {
        'provision': round(towns_gdf.demand_within.sum() / towns_gdf.demand.sum(),2),
        'towns': json.loads(towns_gdf.to_json()),
        'links': json.loads(links_gdf.to_json())
    }

@app.post("/polygon_assessment", tags=['Territory methods'])
def polygon_assessment(polygon : PolygonModel, region_id : int = 1):
    feature = {
        'type': 'Feature',
        'geometry' : polygon.model_dump(),
        'properties': {}
    }
    region = get_region(region_id)
    provisions = {
        st : tuple(get_provision(region_id, st.name).values()) for st in region.service_types 
    }
    gdf = gpd.GeoDataFrame.from_features([feature], crs=4326).to_crs(region.crs)
    series = gdf.iloc[0]
    territory = Territory(id=0, name='0', geometry=series.geometry)
    indicators, assessment = territory.get_indicators(provisions)
    return {
        'assessment': round(assessment),
        'provisions': json.loads(indicators.to_json(orient='index'))
    }

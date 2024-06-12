import json
import geopandas as gpd
from typing import Annotated, Literal
import numpy as np
from pydantic import BaseModel
from pydantic_geojson import PolygonModel, PointModel, FeatureCollectionModel, FeatureModel
from townsnet import Region, Territory, SERVICE_TYPES
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
    {"name": "Layer methods", "description": "Region layers"},
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

def get_provision(region_id, service_type_name = None):
    region_data_path = os.path.join(data_path, str(region_id))
    provisions_data_path = os.path.join(region_data_path, 'provisions')

    def read_file(level):
        if service_type_name is None:
            return gpd.read_file(os.path.join(provisions_data_path, f'{level}.geojson'))
        else:
            return gpd.read_parquet(os.path.join(provisions_data_path, f'{service_type_name}_districts.parquet'))

    return {
        level : read_file for level in ['districts', 'settlements', 'towns']
    }

@app.get("/")
def read_root():
    return {
        'hello': 'hiii'
    }

@app.get('/service_types')
def service_types() -> list[dict]:
    return SERVICE_TYPES


@app.get("/layer/districts", tags=['Layer methods'])
def districts_layer(
    region_id : int = 1,
): # -> ProvisionModel:
    gdf = get_provision(region_id)['districts']
    gdf = gdf.to_crs(4326)
    gdf.geometry = set_precision(gdf.geometry, grid_size=0.0001)
    gdf['district_id'] = gdf.index
    return json.loads(gdf.to_json())

@app.get("/layer/settlements", tags=['Layer methods'])
def settlements_layer(
    region_id : int = 1,
): # -> ProvisionModel:
    gdf = get_provision(region_id)['settlements']
    gdf = gdf.to_crs(4326)
    gdf.geometry = set_precision(gdf.geometry, grid_size=0.0001)
    gdf['settlement_id'] = gdf.index
    return json.loads(gdf.to_json())

@app.get("/layer/towns", tags=['Layer methods'])
def towns_layer(
    region_id : int = 1,
): # -> ProvisionModel:
    gdf = get_provision(region_id)['towns']
    gdf = gdf.to_crs(4326)
    gdf.geometry = set_precision(gdf.geometry, grid_size=0.0001)
    gdf['settlement_id'] = gdf.index
    return json.loads(gdf.to_json())

@app.get('/provision/region', tags=['Provision methods'])
def region_provision(region_id : int = 1, service_type_name : str = 'school'):
    # service_type = list(filter(lambda st : st['name'] == service_type_name, SERVICE_TYPES))[0]
    gdf = gpd.read_parquet(f'data/{region_id}/provisions/{service_type_name}_districts.parquet')
    return {
        'provision': round(gdf.demand_within.sum() / gdf.demand.sum(),2)
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

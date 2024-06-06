import json
import geopandas as gpd
from typing import Literal
import numpy as np
from pydantic import BaseModel
from pydantic_geojson import PolygonModel, PointModel, FeatureCollectionModel, FeatureModel
from townsnet import Region, Territory, Provision, ServiceType, Town
from fastapi import FastAPI

app = FastAPI()
region = Region.from_pickle('region.pickle')
provision = Provision(region=region)
provisions = {}
for st in region.service_types:
    name = st.name.replace('/', '-')
    try:
        d_gdf = gpd.read_parquet(f'data/{name}_districts.parquet')
        s_gdf = gpd.read_parquet(f'data/{name}_settlements.parquet')
        t_gdf = gpd.read_parquet(f'data/{name}_towns.parquet')
        l_gdf = gpd.read_parquet(f'data/{name}_links.parquet')
        provisions[st] = (d_gdf, s_gdf, t_gdf, l_gdf)
    except:
        provisions[st] = provision.calculate(st)
        d_gdf, s_gdf, t_gdf, l_gdf = provisions[st]
        d_gdf.to_parquet(f'data/{name}_districts.parquet')
        s_gdf.to_parquet(f'data/{name}_settlements.parquet')
        t_gdf.to_parquet(f'data/{name}_towns.parquet')
        l_gdf.to_parquet(f'data/{name}_links.parquet')

# provisions = {st:provision.calculate(st) for st in region.service_types}

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

@app.get("/")
def read_root():
    return {
        'hello': 'hiii'
    }

@app.post('/service_types')
def service_types() -> list[ServiceType]:
    return region.service_types


@app.post("/provision/districts")
def districts_provision(service_type : str) -> ProvisionModel:
    st = region[service_type]
    d_gdf, s_gdf, t_gdf, l_gdf = provisions[st]
    for gdf in [d_gdf, s_gdf, t_gdf, l_gdf]:
        gdf.to_crs(4326, inplace=True)
    return json.loads(d_gdf.to_json())

@app.post("/provision/settlements")
def settlements_provision(service_type : str) -> ProvisionModel:
    st = region[service_type]
    d_gdf, s_gdf, t_gdf, l_gdf = provisions[st]
    for gdf in [d_gdf, s_gdf, t_gdf, l_gdf]:
        gdf.to_crs(4326, inplace=True)
    return json.loads(s_gdf.to_json())

@app.post("/provision/towns")
def towns_provision(service_type : str) -> ProvisionModel:
    st = region[service_type]
    d_gdf, s_gdf, t_gdf, l_gdf = provisions[st]
    for gdf in [d_gdf, s_gdf, t_gdf, l_gdf]:
        gdf.to_crs(4326, inplace=True)
    return {
        'towns': json.loads(t_gdf.to_json()),
        'links': json.loads(l_gdf.to_json()),
    }

@app.post("/polygon_assessment")
def polygon_assessment(polygon : PolygonModel):
    feature = {
        'type': 'Feature',
        'geometry' : polygon.model_dump(),
        'properties': {}
    }
    gdf = gpd.GeoDataFrame.from_features([feature], crs=4326).to_crs(region.crs)
    series = gdf.iloc[0]
    territory = Territory(id=0, name='0', geometry=series.geometry)
    indicators, assessment = territory.get_indicators(provisions)
    return {
        'assessment': round(assessment,2),
        # 'provisions': indicators.to_dict(orient='index')
    }

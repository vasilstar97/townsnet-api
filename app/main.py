import json
import math
from fastapi import FastAPI
import numpy as np
import pandas as pd
from pydantic_geojson import PolygonModel
from townsnet import SERVICE_TYPES, Territory
from .utils import REGIONS_DICT, get_provision, get_region, process_output, process_territory
from .models import *

app = FastAPI()

#data initialization

@app.get("/")
def read_root():
    return {
        'hello': 'hiii'
    }

@app.get('/regions')
def regions() -> dict[int, str]:
    return REGIONS_DICT

@app.get('/service_types')
def service_types() -> list[dict]:
    return SERVICE_TYPES

@app.get('/provision/region', tags=['Provision methods'])
def region_provision(region_id : int = 1, service_type_name : str = 'school'):
    gdf = get_provision(region_id, service_type_name)['districts']
    return {
        'provision': round(gdf.demand_within.sum() / gdf.demand.sum(),2)
    }

@app.post("/provision/territory", tags=['Provision methods', 'Territory methods'])
@process_territory
def territory_provision(polygon : PolygonModel, region_id : int = 1):
    region = get_region(region_id)
    polygon_gdf = polygon.to_crs(region.crs)
    territory = Territory(id=0, name='', geometry=polygon_gdf.iloc[0].geometry)
    provisions = {
        st : tuple([*get_provision(region_id, st.name).values(), None]) for st in region.service_types
    }
    indicators, assessment = territory.get_indicators(provisions)
    indicators = indicators[~indicators.provision.isna()]
    return {
        'assessment': round(assessment),
        'provisions': indicators.provision.apply(lambda p : round(p,2)) #json.loads(indicators.to_json(orient='index'))
    }

@app.get("/layer/districts", tags=['Layer methods'])
@process_output
def districts_layer(
    region_id : int = 1,
): # -> ProvisionModel:
    return get_provision(region_id)['districts']

@app.get("/layer/settlements", tags=['Layer methods'])
@process_output
def settlements_layer(
    region_id : int = 1,
): # -> ProvisionModel:
    return get_provision(region_id)['settlements']

@app.get("/layer/towns", tags=['Layer methods'])
@process_output
def towns_layer(
    region_id : int = 1,
): # -> ProvisionModel:
    return get_provision(region_id)['towns']

@app.post("/layer/territory", tags=['Layer methods', 'Territory methods'])
@process_output
@process_territory
def territory_layer(
    polygon : PolygonModel,
    region_id : int = 1,
): # -> ProvisionModel:
    region = get_region(region_id)
    polygon_gdf = polygon.to_crs(region.crs)
    territory = Territory(id=0, name='', geometry=polygon_gdf.iloc[0].geometry)
    
    gdfs = []
    for service_type in region.service_types:
        t_gdf = get_provision(region_id, service_type.name)['towns']
        gdf, _ = territory.get_context_provision(service_type, t_gdf)
        gdf = gdf[['geometry', 'provision']].rename(columns={'provision': f'provision_{service_type.name}'})
        gdfs.append(gdf)

    return pd.concat(gdfs)
from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic_geojson import PolygonModel
# from townsnet import SERVICE_TYPES, Territory
# from .utils import REGIONS_DICT, get_provision, get_region, process_output, process_territory
from .utils import urban_api
from .models import *
from .routers import provision, engineering

app = FastAPI(
    title='TownsNet API',
    description='API providing methods for regions provisions assessment and other stuff.'
)

# app.on_event('start_up')

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex='http://.*',
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=100)

@app.get("/", include_in_schema=False)
async def read_root():
    return RedirectResponse('/docs')

@app.get('/regions', tags=['Utils'])
async def regions() -> dict[int, str]:
    regions = await urban_api.get_regions()
    return {i : regions.loc[i,'name'] for i in regions.index}

app.include_router(provision.router)
app.include_router(engineering.router)


# @app.get('/service_types')
# def service_types() -> list[dict]:
#     return SERVICE_TYPES

# @app.get('/provision/region', tags=['Provision methods'])
# def region_provision(region_id : int = Query(example=1), service_type_name : str = Query(example='school')):
#     gdf = get_provision(region_id, service_type_name)['districts']
#     return {
#         'provision': round(gdf.demand_within.sum() / gdf.demand.sum(),2)
#     }

# INFRASTRUCTURES = {
#     'education': 'образование',
#     'healthcare': 'здравоохранение',
#     'commerce': 'торговля',
#     'catering': 'общепит',
#     'leisure': 'досуг',
#     'recreation': 'рекреация',
#     'sport': 'спорт',
#     'service': 'услуги',
#     'transport': 'транспорт',
#     'safeness': 'безопасность',
# }

# CATEGORIES = {
#     'basic': 'Базовые',
#     'basic_plus': "Базовые+",
#     "comfort": 'Комфорт'
# }

# def interpretation(provisions, indicators):
#     service_types = []
#     for st in SERVICE_TYPES:
#         if st['name'] not in provisions or provisions[st['name']]<0.8:
#             service_types.append(st)
#     texts = []
#     for category in {st['category'] for st in service_types}:
#         cat_text = f"Для сервисов из категории '{CATEGORIES[category]}' не хватает: "
#         inf_texts = []
#         for infrastructure in {st['infrastructure'] for st in service_types if st['category'] == category}:
#             st_text = str.join(', ', [st['name_ru'] for st in service_types if st['category'] == category and st['infrastructure'] == infrastructure])
#             inf_texts.append(f'{st_text} ({INFRASTRUCTURES[infrastructure]})')
#         cat_text += str.join('; ', inf_texts)
#         texts.append(cat_text)
#     return texts

# @app.post("/provision/territory", tags=['Provision methods', 'Territory methods'])
# @process_territory
# def territory_provision(polygon : PolygonModel, region_id : int = Query(example=1)):
#     region = get_region(region_id)
#     polygon_gdf = polygon.to_crs(region.crs)
#     territory = Territory(id=0, name='', geometry=polygon_gdf.iloc[0].geometry)
#     provisions = {
#         st : tuple([*get_provision(region_id, st.name).values(), None]) for st in region.service_types
#     }
#     indicators, assessment = territory.get_indicators(provisions)
#     indicators = indicators[~indicators.provision.isna()]
#     basic, basic_plus, comfort = indicators.groupby("category").agg({"assessment": "sum"})["assessment"]
#     return {
#         'assessment': round(assessment),
#         'interpretation': interpretation(indicators.provision, indicators),
#         'indicators': {
#             'basic': basic,
#             'basic_plus': basic_plus,
#             'comfort': comfort
#         },
#         'provisions': indicators.provision.apply(lambda p : round(p,2)) #json.loads(indicators.to_json(orient='index')),
#     }

# @app.get("/layer/districts", tags=['Layer methods'])
# @process_output
# def districts_layer(
#     region_id : int = Query(example=1)
# ): # -> ProvisionModel:
#     return get_provision(region_id)['districts']

# @app.get("/layer/settlements", tags=['Layer methods'])
# @process_output
# def settlements_layer(
#     region_id : int = Query(example=1)
# ): # -> ProvisionModel:
#     return get_provision(region_id)['settlements']

# @app.get("/layer/towns", tags=['Layer methods'])
# @process_output
# def towns_layer(
#     region_id : int = Query(example=1)
# ): # -> ProvisionModel:
#     return get_provision(region_id)['towns']

# @app.post("/layer/territory", tags=['Layer methods', 'Territory methods'])
# @process_output
# @process_territory
# def territory_layer(
#     polygon : PolygonModel,
#     region_id : int = Query(example=1)
# ): # -> ProvisionModel:
#     region = get_region(region_id)
#     polygon_gdf = polygon.to_crs(region.crs)
#     territory = Territory(id=0, name='', geometry=polygon_gdf.iloc[0].geometry)
#     res_gdf = region.get_towns_gdf()[['geometry', 'town_name']]
#     for service_type in region.service_types:
#         t_gdf = get_provision(region_id, service_type.name)['towns']
#         gdf, _ = territory.get_context_provision(service_type, t_gdf)
#         res_gdf[f'provision_{service_type.name}'] = gdf['provision']

#     res_gdf['keep'] = res_gdf[filter(lambda c : 'provision' in c, res_gdf.columns)].isna().apply(lambda s : not s.all(), axis=1)
#     res_gdf = res_gdf[res_gdf['keep']]
#     res_gdf = res_gdf[['geometry', *filter(lambda c : 'provision' in c,res_gdf.columns)]]
#     return res_gdf
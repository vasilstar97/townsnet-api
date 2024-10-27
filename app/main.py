from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
# from townsnet import SERVICE_TYPES, Territory
# from .utils import REGIONS_DICT, get_provision, get_region, process_output, process_territory
from .utils import urban_api
from .routers import provision, engineering

app = FastAPI(
    title='TownsNet API',
    description='API providing methods for regions provisions assessment and other stuff.'
)

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
    regions_df = await urban_api.get_regions()
    return {i : regions_df.loc[i,'name'] for i in regions_df.index}

app.include_router(provision.router)
app.include_router(engineering.router)

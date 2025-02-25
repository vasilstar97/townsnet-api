from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
# from townsnet import SERVICE_TYPES, Territory
# from .utils import REGIONS_DICT, get_provision, get_region, process_output, process_territory
from .utils import api_client
from .routers.engineering import engineering_controller
from .routers.provision import provision_controller
from .routers.hex import hex_controller
from contextlib import asynccontextmanager

controllers = [provision_controller, engineering_controller, hex_controller]

async def on_startup():
    for controller in controllers:
        await controller.on_startup()

async def on_shutdown():
    for controller in controllers:
        await controller.on_shutdown()

@asynccontextmanager
async def lifespan(app : FastAPI):
    await on_startup()
    yield
    await on_shutdown()

app = FastAPI(
    title='TownsNet API',
    description='API providing methods for regions provisions assessment and other stuff.',
    lifespan=lifespan
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
    regions_df = await api_client.get_regions()
    return {i : regions_df.loc[i,'name'] for i in regions_df.index}

for controller in controllers:
    app.include_router(controller.router)
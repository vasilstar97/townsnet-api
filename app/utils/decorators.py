import json
import geopandas as gpd
from functools import wraps
from shapely import set_precision

def process_territory(func):
    @wraps(func)
    def process(polygon, *args, **kwargs):
        polygon_feature = {
        'type': 'Feature',
        'geometry' : polygon.model_dump(),
        'properties': {}
        }
        polygon_gdf = gpd.GeoDataFrame.from_features([polygon_feature], crs=4326)
        return func(polygon_gdf, *args, **kwargs)
    return process

def process_output(func):
    @wraps(func)
    def process(*args, **kwargs):
        gdf = func(*args, **kwargs).to_crs(4326)
        gdf.geometry = set_precision(gdf.geometry, grid_size=0.0001)
        gdf['id'] = gdf.index
        for column in filter(lambda c : 'provision' in c, gdf):
            gdf[column] = gdf[column].apply(lambda p : round(p,2))
        return json.loads(gdf.to_json())
    return process
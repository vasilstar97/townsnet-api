from pydantic import BaseModel
from pydantic_geojson import PolygonModel


class TerritoryDTO(BaseModel):

    territory_id: int
    territory: PolygonModel

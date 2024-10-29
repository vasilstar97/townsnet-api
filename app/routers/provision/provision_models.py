from pydantic import BaseModel, Field, field_validator
from pydantic_geojson import FeatureCollectionModel, FeatureModel, PolygonModel, MultiPolygonModel, PointModel

ROUND_PRECISION = 2

class ProvisionModel(FeatureCollectionModel):

    class ProvisionProperties(BaseModel):
        provision : str
    
    class ProvisionFeature(FeatureModel):
        geometry : PolygonModel | MultiPolygonModel | PointModel
        properties : dict[str, float | int | None]

        @field_validator('properties', mode='after')
        @classmethod
        def validate_properties(cls, properties : dict[str, float | int]):
            properties = properties.copy()
            for key, value in properties.items():
                if isinstance(value, float):
                    properties[key] = round(value, ROUND_PRECISION)
            return properties
    
    features : list[ProvisionFeature]
from pydantic import BaseModel
from pydantic_geojson import (FeatureCollectionModel, FeatureModel, PointModel,
                              PolygonModel)

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
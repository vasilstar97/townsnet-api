from pydantic import BaseModel, Field
from pydantic_geojson import FeatureCollectionModel, FeatureModel, PolygonModel, MultiPolygonModel

class PhysicalObjectType(BaseModel):
    physical_object_type_id : int
    name : str

class Indicator(BaseModel):
    indicator_id : int
    name_full : str
    name_short : str
    physical_objects_types : list[PhysicalObjectType]

class EngineeringModel(FeatureCollectionModel):
    
    class EngineeringFeature(FeatureModel):
        geometry : PolygonModel | MultiPolygonModel
        properties : dict[str, int]
    
    features : list[EngineeringFeature]
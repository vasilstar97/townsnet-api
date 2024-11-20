from pydantic_geojson import FeatureCollectionModel, FeatureModel, PolygonModel

class HexGridModel(FeatureCollectionModel):
    
    class HexGridFeature(FeatureModel):
        geometry : PolygonModel
    
    features : list[HexGridFeature]
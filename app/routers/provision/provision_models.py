from pydantic import BaseModel, Field, field_validator
from pydantic_geojson import FeatureCollectionModel, FeatureModel, PolygonModel, MultiPolygonModel, PointModel
from townsnet.provision.provision_model import DEMAND_COLUMN, SUPPLY_COLUMN, CAPACITY_COLUMN, PROVISION_COLUMN, POPULATION_COLUMN, DEMAND_LEFT_COLUMN, CAPACITY_LEFT_COLUMN, DEMAND_WITHIN_COLUMN, DEMAND_WITHOUT_COLUMN

ROUND_PRECISION = 2
RU_NAMES_MAPPING = {
    POPULATION_COLUMN: 'Численность населения',
    PROVISION_COLUMN: 'Обеспеченность',
    CAPACITY_COLUMN: 'Вместимость',
    CAPACITY_LEFT_COLUMN: 'Оставшаяся вместимость',
    DEMAND_COLUMN: 'Спрос',
    DEMAND_LEFT_COLUMN: 'Неудовлетворенный спрос',
    DEMAND_WITHIN_COLUMN: 'Удовлетворенный спрос в зоне доступности',
    DEMAND_WITHOUT_COLUMN: 'Удовлетворенный спрос вне зоны доступности'
}

class ProvisionModel(FeatureCollectionModel):

    class ProvisionProperties(BaseModel):
        provision : str
    
    class ProvisionFeature(FeatureModel):
        geometry : PolygonModel | MultiPolygonModel | PointModel
        properties : dict[str, float | int | None]

        @field_validator('properties', mode='after')
        @classmethod
        def validate_properties(cls, properties : dict[str, float | int]):
            p = {}
            for key, value in properties.items():
                if key in RU_NAMES_MAPPING:
                    key = RU_NAMES_MAPPING[key]
                if isinstance(value, float):
                    value = round(value, ROUND_PRECISION)
                p[key] = value
            return p
    
    features : list[ProvisionFeature]
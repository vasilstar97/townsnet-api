from pydantic import BaseModel, Field
from typing import Literal


class HexesDTO(BaseModel):

    territory_id: int = Field(
        ...,
        examples=[1],
        description="Territory id to calculate hexes priority"
    )

    object_type: Literal[
        "Медицинский комплекс",
        "Бизнес-кластер",
        "Пром объект",
        "Логистическо-складской комплекс",
        "Порт",
        "Кампус университетский",
        "Тур база",
    ] = Field(
        ...,
        examples=["Тур база"],
        description="Possible object to place in territory"
    )

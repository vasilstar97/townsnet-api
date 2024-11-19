from pydantic import BaseModel, Field
from typing import LiteralString


class HexesDTO(BaseModel):

    territory: int = Field(
        ...,
        examples=[""],
        description="Territory id to calculate hexes priority"
    )

    object_type: LiteralString[
        "Медицинский комплекс",
        "Бизнес-кластер",
        "Пром объект",
        "Логистическо-складской комплекс",
        "Порт",
        "Кампус университетский",
        "Тур база",
    ] = Field(
        ...,
        description="Possible object to place in territory"
    )

import requests_async as ra
from fastapi import HTTPException


class HexApiService:

    def __init(self, base_url):
        self.base_url = base_url

    @staticmethod
    async  def get_hexes_with_indicators_by_territory(territory_id: int) -> dict | list:


        response = await ra.get()

        if response.status_code in (200, 201):
            return response.json()
        raise HTTPException(status_code=404, detail=response.json())

    @staticmethod
    async def get_service_by_territory_id(
            territory_id: int,
            service_type_name: str,
    ) -> dict | list:


        response = await ra.get()

        if response.status_code in (200, 201):
            return response.json()
        raise HTTPException(status_code=response.status, detail=response.json())

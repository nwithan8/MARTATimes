from typing import Union, Optional

import objectrest
from pydantic import BaseModel


class Address(BaseModel):
    house_number: Optional[str] = ''
    road: Optional[str] = ''


def get_nearest_address(api_key: str, latitude: float, longitude: float) -> Union[Address, None]:
    """
    Use locationiq.com API to get address of lat/long combo
    """
    params: dict = {
        'key': api_key,
        'lat': latitude,
        'lon': longitude,
        'format': 'json'
    }
    url: str = 'https://us1.locationiq.com/v1/reverse.php'

    try:
        # noinspection PyTypeChecker
        address: Address = objectrest.get_object(url=url, model=Address, sub_keys=['address'], params=params)
        return address
    except Exception as e:
        return None



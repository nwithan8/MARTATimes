from typing import List

import objectrest

from marta.models import LegacyBus

from modules.http import download_file


class MapBoxLocation:
    def __init__(self, longitude: float, latitude: float):
        self.longitude: float = longitude
        self.latitude: float = latitude

    def generate_query_string(self, marker: int) -> str:
        return f'pin-s-bus+{marker}({self.longitude},{self.latitude})'


def generate_mapbox_map(locations: List[MapBoxLocation], file_name: str) -> bool:
    """
    Generates a map image of the given locations and saves it to the given file_name
    Returns True if successful, False otherwise
    """
    pins_queries: List[str] = []
    count: int = 1

    for location in locations:
        pins_queries.append(location.generate_query_string(count))
        count += 1

    pins_query: str = ','.join(pins_queries)
    mapbox_url: str = f'https://api.mapbox.com/styles/v1/mapbox/traffic-day-v2/static/{pins_query}/auto/400x300@2x?access_token={MAPBOX_KEY}'

    response: objectrest.Response = objectrest.get(mapbox_url, stream=True)
    if response.status_code == 200:
        download_file(response=response, filename=file_name)
        return True
    else:
        return False

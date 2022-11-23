#!/usr/bin/python3

import os
from typing import List, Union, Tuple

import marta
import tweepy
from dotenv import load_dotenv
from marta import RailClient, BusClient, TrainStations
from marta.enums.vehicle_type import VehicleType
from marta.models.bus import LegacyBus
from marta.models.arrival import Arrival, Arrivals
from marta.models.vehicle import VehiclePosition

from modules.mapbox import generate_mapbox_map, MapBoxLocation
from modules.locationiq import get_nearest_address, Address
from modules.twitter import add_as_many_as_possible_to_tweet

import logs as logging

load_dotenv()

# Twitter API Credentials
TWITTER_HANDLE = "MARTAtimes"
TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# MARTA API Credentials
MARTA_API_KEY = os.getenv("MARTA_API_KEY")

# LocationIQ Credentials
LOCATION_IQ_KEY = os.environ.get('LOCATION_IQ_KEY')

# Mapbox Credentials
MAPBOX_KEY = os.environ.get('MAPBOX_KEY')

BUS_MAP_IMAGE_FILENAME = 'tmp/bus_map.png'


def get_nearest_address_to_bus(bus: LegacyBus) -> Union[str, None]:
    """
    Use locationiq.com API to get address of lat/long combo
    """
    bus_position = bus.position
    address: Union[Address, None] = get_nearest_address(api_key=LOCATION_IQ_KEY,
                                                        latitude=bus_position.latitude,
                                                        longitude=bus_position.longitude)
    if address:
        address_string = f'{address.house_number} {address.road}'.strip()
        return address_string

    return None


def generate_bus_location_map_image(buses: List[LegacyBus], file_name: str) -> bool:
    """
    Generates a map image of the given buses and saves it to the given file_name
    Returns True if successful, False otherwise
    """
    map_box_locations: List[MapBoxLocation] = []

    for bus in buses:
        bus_position: VehiclePosition = bus.position
        map_box_location: MapBoxLocation = MapBoxLocation(longitude=bus_position.longitude,
                                                          latitude=bus_position.latitude)
        map_box_locations.append(map_box_location)

    return generate_mapbox_map(locations=map_box_locations, file_name=file_name)


class TweetProcessor:
    def __init__(self, tweet: tweepy.Tweet, marta_api_key: str):
        self.tweet = tweet
        self._marta_api_key = marta_api_key

    @property
    def _tweet_text(self) -> str:
        return self.tweet.text.lower().strip()

    @property
    def _tweet_about_trains(self):
        return 'train' in self._tweet_text

    @property
    def _tweet_about_buses(self):
        return 'bus' in self._tweet_text

    def _get_bus_routes_from_tweet(self) -> List[int]:
        routes: List[int] = []
        for word in self._tweet_text.split():
            word = word.strip().upper()
            if word.isdigit():
                routes.append(int(word))
        return routes

    def _get_train_line_from_tweet(self) -> Union[marta.TrainLine, None]:
        possible_lines = marta.TrainLine.__members__.keys()
        for word in self._tweet_text.split():
            word: str = word.strip().upper()
            if word in possible_lines:
                return marta.TrainLine[word]
        return None

    def _get_direction_from_tweet(self) -> Union[marta.Direction, None]:
        possible_directions = marta.Direction.__members__.keys()
        for word in self._tweet_text.split():
            word: str = word.strip().upper().replace("BOUND", "")
            if word in possible_directions:
                return marta.Direction[word]
        return None

    def _get_train_stations_from_tweet(self) -> List[marta.TrainStations]:
        """
        Get all train stations mentioned in tweet
        """
        stations: List[TrainStations] = []
        for word in self._tweet_text.split():
            matching_station: Union[TrainStations, None] = TrainStations.from_keyword(keyword=word)
            if matching_station:
                stations.append(matching_station)

        return stations

    def _get_bus_locations_message(self, route_id: int) -> Tuple[str, Union[str, None]]:
        bus_client: BusClient = BusClient(api_key=self._marta_api_key)

        buses: List[LegacyBus] = bus_client.get_buses(route=route_id)
        if not buses:
            return "No buses on that route right now.", None

        link: str = f"itsmarta.com/{route_id}.aspx\n\n"

        bus_entries: List[str] = []
        for bus in buses:
            bus_entry: str = f"Bus {bus.vehicle_id} ({bus.direction})"

            address = get_nearest_address_to_bus(bus=bus)
            if address:
                bus_entry += f" - near {address}"

            bus_entry += "\n"
            bus_entries.append(bus_entry)

        # We always have buses at this point
        map_file_name: Union[str, None] = None
        if generate_bus_location_map_image(buses=buses, file_name=BUS_MAP_IMAGE_FILENAME):
            map_file_name: str = BUS_MAP_IMAGE_FILENAME

        message, _ = add_as_many_as_possible_to_tweet(link, bus_entries)

        return message, map_file_name

    def _get_train_travel_time_message(self,
                                       start_station: marta.TrainStations,
                                       end_station: marta.TrainStations) -> str:
        minutes = start_station.details.time_to(end_station.details)
        return f"It takes approximately {minutes} minute{'s' if minutes > 1 else ''} to go from {start_station.details.station_name} to {end_station.details.station_name}"

    def _get_train_arrival_times_message(self,
                                         station: marta.TrainStations,
                                         direction: marta.Direction = None,
                                         line: marta.TrainLine = None) -> str:
        rail_client: RailClient = RailClient(api_key=self._marta_api_key)

        arrivals: Arrivals = rail_client.get_arrivals()
        if direction:
            arrivals: Arrivals = arrivals.heading(direction=direction)
        if line:
            arrivals: Arrivals = arrivals.on_line(line=line)

        if not arrivals:
            return f"No trains near {station.details.station_name} right now."

        arrival_entries: List[str] = []
        for arrival in arrivals:
            waiting_minutes = arrival.waiting_time.seconds // 60
            direction_string = arrival.direction.to_string(vehicle_type=VehicleType.TRAIN)
            arrival_entry: str = f"{arrival.line} - {arrival.destination} ({direction_string}): {waiting_minutes} minute{'s' if waiting_minutes > 1 else ''}"
            arrival_entries.append(arrival_entry)

        message, _ = add_as_many_as_possible_to_tweet("", arrival_entries)

        return message

    def _process_train_tweet(self) -> str:
        """
        Process a tweet about trains, returning a response
        """
        stations: List[TrainStations] = self._get_train_stations_from_tweet()
        direction: Union[marta.Direction, None] = self._get_direction_from_tweet()
        line: Union[marta.TrainLine, None] = self._get_train_line_from_tweet()

        if len(stations) == 0:
            return "I couldn't detect a station in your tweet. Please include at least one station name."
        elif len(stations) == 1:
            # get arrival times for that station
            station = stations[0]
            return self._get_train_arrival_times_message(station=station, direction=direction, line=line)
        else:
            # get travel time between the two stations (use first two stations detected)
            start_station: TrainStations = stations[0]
            end_station: TrainStations = stations[1]
            if start_station == end_station:
                # Might have been an accident, or they might be asking about a station's arrival times
                return self._get_train_arrival_times_message(station=start_station, direction=direction, line=line)
            return self._get_train_travel_time_message(start_station=start_station, end_station=end_station)

    def _process_bus_tweet(self) -> Tuple[str, Union[str, None]]:
        """
        Process a tweet about buses, returning a response and an image
        """
        routes: List[int] = self._get_bus_routes_from_tweet()

        if len(routes) == 0:
            return "I couldn't detect a bus route in your tweet. Please include at least one bus route number.", None
        else:
            # get locations for that route (use first route detected)
            route: int = routes[0]
            return self._get_bus_locations_message(route_id=route)

    def process(self) -> Tuple[str, Union[str, None]]:
        """
        Process the tweet and return a response and an optional image link
        """
        if self._tweet_about_trains:
            return self._process_train_tweet(), None
        elif self._tweet_about_buses:
            return self._process_bus_tweet()
        else:
            return """I don't know what you're asking. 
            If you'd like train times, please include the word 'train' and which station(s).
            If you'd like bus times, please include the word 'bus' and which route number.""", None


class MartaTimesStream(tweepy.StreamingClient):
    def __init__(self, client: tweepy.Client, bearer_token: str):
        super().__init__(bearer_token=bearer_token)
        self.tweeting_client: tweepy.Client = client

    def respond_to_tweet(self, tweet: tweepy.Tweet, response: str, image_path: str = None):
        logging.info(f"Responding to tweet {tweet.id}: {tweet.text}")
        if image_path:
            # TODO: upload image to twitter
            pass
        else:
            self.tweeting_client.create_tweet(in_reply_to_tweet_id=tweet.id, text=response)
        logging.info(f"Responded to tweet {tweet.id} with: {response}")

    def on_connect(self):
        logging.debug("Connected to Twitter API")

    def on_disconnect(self):
        logging.debug("Disconnected from Twitter API")

    def on_tweet(self, tweet: tweepy.Tweet):
        processor = TweetProcessor(tweet=tweet, marta_api_key=MARTA_API_KEY)
        response_text, image_path = processor.process()
        self.respond_to_tweet(tweet=tweet, response=response_text, image_path=image_path)

    def on_errors(self, errors):
        logging.error(f"Errors {errors}")

    def on_exception(self, exception):
        logging.error(f"Exception {exception}")


if __name__ == '__main__':
    # Set up logging
    logging.init(app_name="MartaTimes", console_log_level="DEBUG", log_to_file=True)

    # Set up Twitter client
    client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN,
                           consumer_key=TWITTER_CONSUMER_KEY,
                           consumer_secret=TWITTER_CONSUMER_SECRET,
                           access_token=TWITTER_ACCESS_TOKEN,
                           access_token_secret=TWITTER_ACCESS_TOKEN_SECRET)

    stream = MartaTimesStream(client=client,
                              bearer_token=TWITTER_BEARER_TOKEN)

    mention_filter = f"keyword (@{TWITTER_HANDLE} OR to:{TWITTER_HANDLE}) -from:{TWITTER_HANDLE} -is:retweet"
    stream.add_rules(tweepy.StreamRule(mention_filter))

    logging.debug("Listening for mentions...")

    stream.filter(tweet_fields=["id", "text"])

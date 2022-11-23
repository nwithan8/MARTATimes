#!/usr/bin/python3

import os
from typing import List, Union, Any

import marta
import tweepy
from dotenv import load_dotenv
from marta import RailClient, BusClient, TrainStations
from marta.enums.vehicle_type import VehicleType

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


def can_add_to_tweet(existing_text: str, text_to_add: str) -> bool:
    """
    Checks if adding text_to_add to existing_text will exceed Twitter's 280-character limit
    """
    if len(existing_text) + len(text_to_add) > 280:
        return False
    return True


def get_nearest_address(latitude: str, longitude: str):
    """
    Use locationiq.com API to get address of lat/long combo
    """
    res = requests.get('https://us1.locationiq.com/v1/reverse.php', params={
        'key': location_iq_key,
        'lat': latitude,
        'lon': longitude,
        'format': 'json'
    }).json()
    if 'error' in res.keys():
        return False
    address = res.get('address')
    house_number = address.get('house_number')
    road = address.get('road')
    return '{}{}'.format((house_number + " " if house_number else ""), (road if road else ""))


def get_save_map(buses, filename):
    if buses:
        pins = ""
        count = 1
        for b in buses:
            pins += 'pin-s-{count}+000000({long},{lat}),'.format(
                count=str(count),
                long=str(b.longitude),
                lat=str(b.latitude)
            )
            count += 1
        pins = pins[:-1]
        res = requests.get('https://api.mapbox.com/styles/v1/mapbox/traffic-day-v2/static/'
                           '{pins}/auto/400x300@2x?access_token={token}'.format(
            pins=pins,
            token=mapbox_key
        ), stream=True)
        if res.status_code == 200:
            with open(filename, 'wb') as image:
                for chunk in res:
                    image.write(chunk)
                image.close()
            return filename
    return None


def bus_location(routeNumber: int):
    buses = get_buses(route=routeNumber)
    if buses:
        map_buses = []
        final_message = ""
        count = 1
        for b in buses:
            if len(final_message) < 210:
                address = get_nearest_address(b.latitude, b.longitude)
                if address:
                    final_message += '{count}) Bus {id} ({dir}) - near {address}\n'.format(
                        count=str(count),
                        id=str(b.vehicle),
                        dir=b.direction,
                        address=address
                    )
                    count += 1
                    map_buses.append(b)
        if len(final_message) < 257:
            final_message += 'itsmarta.com/{id}.aspx'.format(id=routeNumber)
        return final_message, get_save_map(map_buses, 'tmp/map.png')
    else:
        return "No buses on that route right now.", None


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

    def _get_train_travel_time_message(self, start_station: marta.TrainStations, end_station: marta.TrainStations) -> str:
        minutes = start_station.details.time_to(end_station.details)
        return f"It takes approximately {minutes}{'s' if minutes > 1 else ''} to go from {start_station.details.station_name} to {end_station.details.station_name}"

    def _get_train_arrival_times_message(self, station: marta.TrainStations, direction=None, line=None) -> str:
        rail_client = RailClient(api_key=self._marta_api_key)

        arrivals = rail_client.get_arrivals()
        if direction:
            arrivals = arrivals.heading(direction=direction)
        if line:
            arrivals = arrivals.on_line(line=line)

        if not arrivals:
            return f"No trains near {station.details.station_name} right now."

        message = ""
        for arrival in arrivals:
            arrival_entry = f"{arrival.line} - {arrival.destination} ({arrival.direction.to_string(vehicle_type=VehicleType.TRAIN)}): {arrival.waiting_time.seconds * 60} min(s)\n "
            if not can_add_to_tweet(message, arrival_entry):
                break
            message += f"{arrival_entry}"

        return message

    def _get_train_line_from_tweet(self) -> Union[marta.TrainLine, None]:
        possible_lines = marta.TrainLine.__members__.keys()
        for word in self._tweet_text.split():
            word = word.strip().upper()
            if word in possible_lines:
                return marta.TrainLine[word]
        return None

    def _get_direction_from_tweet(self) -> Union[marta.Direction, None]:
        possible_directions = marta.Direction.__members__.keys()
        for word in self._tweet_text.split():
            word = word.strip().upper().replace("BOUND", "")
            if word in possible_directions:
                return marta.Direction[word]
        return None

    def _get_train_stations_from_tweet(self) -> List[marta.TrainStations]:
        """
        Get all train stations mentioned in tweet
        """
        stations = []
        for word in self._tweet_text.split():
            matching_station = TrainStations.from_keyword(keyword=word)
            if matching_station:
                stations.append(matching_station)

        return stations

    def _process_train_tweet(self) -> str:
        """
        Process a tweet about trains, returning a response
        """
        stations = self._get_train_stations_from_tweet()
        direction = self._get_direction_from_tweet()
        line = self._get_train_line_from_tweet()

        if len(stations) == 0:
            return "I couldn't detect a station in your tweet. Please include at least one station name."
        elif len(stations) == 1:
            # get arrival times for that station
            return self._get_train_arrival_times_message(station=stations[0], direction=direction, line=line)
        else:
            # get travel time between the two stations (use first two stations detected)
            if stations[0] == stations[1]:
                # Might have been an accident, or they might be asking about a station's arrival times
                return self._get_train_arrival_times_message(station=stations[0], direction=direction, line=line)
            return self._get_train_travel_time_message(start_station=stations[0], end_station=stations[1])

    def _process_bus_tweet(self) -> [str, str]:
        """
        Process a tweet about buses, returning a response and an image
        """
        for word in self._tweet_text.split():
            if word.isnumeric() and int(word) in []:
                return bus_location(routeNumber=int(word))
        return "I don't know what you're asking. Please include which route number.", None

    def process(self) -> [str, Union[str, None]]:
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

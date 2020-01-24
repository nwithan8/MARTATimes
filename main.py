#!/usr/bin/python3

import os
import string
import tweepy
from tweepy.streaming import StreamListener
from tweepy import Stream
from martapi.api import get_buses, get_trains
from routes import *
import logging
import sys
import requests

# Twitter API Credentials
consumer_key = os.environ.get('TWITTER_CONSUMER_KEY')
consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET')
access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
access_secret = os.environ.get('TWITTER_ACCESS_SECRET')

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_secret)
twitter = tweepy.API(auth)

# LocationIQ Credentials
location_iq_key = os.environ.get('LOCATION_IQ_KEY')

# Mapbox Credentials
mapbox_key = os.environ.get('MAPBOX_KEY')

# Logging

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s [%(levelname)8s] %(message)s')
log = logging.getLogger('')

translator = str.maketrans('', '', string.punctuation)


def marta_mentioned(status):
    if hasattr(status, 'retweeted_status'):
        return False
    elif not status.entities['user_mentions']:
        return False
    else:
        for u in status.entities['user_mentions']:
            if u['screen_name'].lower() == 'martatimes':
                return True
        return False


def process_tweet(status):
    text = status.text.lower().translate(translator).split()
    if 'train' in text:
        starting_station = None
        ending_station = None
        direction = None
        line = None
        if 'lake' in text:
            station = east_or_west_lake(text[text.index('lake') - 1])  # check word before lake
            if starting_station:
                ending_station = station
            else:
                starting_station = station
        if not ending_station:
            for station, info in stations.items():
                for keyword in info[0]:
                    if keyword in text:
                        if keyword == 'lake':
                            station = east_or_west_lake(text[text.index(keyword) - 1])  # check word before lake
                        if starting_station:
                            ending_station = station
                            break
                        else:
                            starting_station = station
        if starting_station:
            if ending_station and ending_station != starting_station:
                return train_travel_time(startPoint=starting_station, endPoint=ending_station), None
            else:
                for direct, proper in directions.items():
                    if direct in text and not station_or_direction(text[text.index(direct):]):
                        direction = proper
                        break
                for li, proper in lines.items():
                    if li in text:
                        line = proper
                        break
                return train_arrival_times(station=starting_station, direction=direction, line=line), None
        return "I don't know what you're asking. Please include which station(s).", None
    if 'bus' in text:
        for word in text:
            if word.isnumeric() and int(word) in bus_routes:
                return bus_location(routeNumber=int(word))
        return "I don't know what you're asking. Please include which route number.", None
    return "I don't know what you're asking.\n" \
           "If you'd like train times, please include the word 'train' and which station(s).\n" \
           "If you'd like bus times, please include the word 'bus' and which route number.", None


def east_or_west_lake(word):
    if word.startswith('e'):
        return 'EAST LAKE STATION'
    if word.startswith('w'):
        return 'WEST LAKE STATION'
    return None


def station_or_direction(text):
    """
    Returns True if stations, False if direction
    """
    if len(text) == 1:
        return False
    if text[0].lower() == "north":
        if text[1].lower() == "springs" or text[1].lower() == "avenue":
            return True
        else:
            return False
    elif text[0].lower() == "east":
        if text[1].lower() == "lake" or text[1].lower() == "point":
            return True
        else:
            return False
    elif text[0].lower() == "west":
        if text[1].lower() == "lake" or text[1].lower() == "end":
            return True
        else:
            return False


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


def train_travel_time(startPoint, endPoint):
    if stations[startPoint][4] != stations[endPoint][4]:  # one is ns, other is ew (5points is nsew, but time = 0,
        # so not effect)
        # start -> 5p + 5p -> end
        time = abs(stations[startPoint][3]) + abs(stations[endPoint][3])
    else:
        # both on same track, so start - end
        time = abs(stations[startPoint][3] - stations[endPoint][3])
    return "It takes approximately {time} {minutes} to go from {start} to {end}".format(
        time=str(time),
        minutes=('minutes' if time > 1 else 'minute'),
        start=startPoint.title(),
        end=endPoint.title()
    )


def train_arrival_times(station, direction=None, line=None):
    final_trains = get_trains(line=line, station=station, direction=direction)
    if final_trains:
        final_message = ""
        for t in final_trains:
            if len(final_message) < 240:  # good buffer for the 280 character limit
                final_message += '{line} - {dest} ({dir}): ({time})\n'.format(
                    line=t.line.capitalize(),
                    dest=t.destination,
                    dir=t.direction,
                    time=(t.waiting_time if t.waiting_time[0].isdigit() else t.waiting_time)
                )
            else:
                break
        return final_message
    else:
        return "No trains near that station."


def respond(status, response, image=None):
    if image:
        twitter.update_with_media(image, '@{} {}'.format(str(status.user.screen_name), response),
                                  in_reply_to_status_id=status.id)
        os.remove(image)
    else:
        twitter.update_status('@{} {}'.format(str(status.user.screen_name), response), in_reply_to_status_id=status.id)
    log.info("Responded with: {}".format(response))


class StdOutListener(StreamListener):

    def on_status(self, status):
        if marta_mentioned(status):
            response, image = process_tweet(status)
            log.info("Replying to this tweet from @{}: '{}'".format(status.user.screen_name, status.text))
            log.info('Replying with: {}'.format(response))
            respond(status, response, image)
        return True

    def on_error(self, status_code):
        log.error("Error, code" + str(status_code))


l = StdOutListener()
stream = Stream(auth, l)
stream.filter(track=['martatimes'])

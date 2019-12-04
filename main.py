#!/usr/bin/python

import re
import os
import string
import tweepy
import json
from tweepy.streaming import StreamListener
from tweepy import Stream
import twitter
from collections import defaultdict
from martapi.api import get_buses, get_trains

#Twitter API Credentials
consumer_key = os.environ.get('TWITTER_CONSUMER_KEY')
consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET')
access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
access_secret = os.environ.get('TWITTER_ACCESS_SECRET')

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_secret)
twitter = tweepy.API(auth)

stations = {
  "AIRPORT STATION": [
    [
      'airport',
      'hartsfield',
      'hartsfield-jackson'
    ],
    "6000 S Terminal Pkwy Atlanta, GA 30337",
    "https://itsmarta.com/Airport.aspx",
    -16,
    'ns'
  ],
  "ARTS CENTER STATION": [
    [
      'arts',
      'artscenter'
    ],
    "1255 West Peachtree St Atlanta, GA 30309",
    "https://itsmarta.com/Arts-Center.aspx",
    6,
    'ns'
  ],
  "ASHBY STATION": [
    [
      'ashby'
    ],
    "65 Joseph E Lowery Blvd Atlanta, GA 30314",
    "https://itsmarta.com/Ashby.aspx",
    -3,
    'ew'
  ],
  "AVONDALE STATION": [
    [
      'avondale'
    ],
    "915 E Ponce de Leon Ave Decatur, GA 30030",
    "https://itsmarta.com/Avondale.aspx",
    15,
    'ew'
  ],
  "BANKHEAD STATION": [
    [
      'bankhead'
    ],
    "1335 Donald Hollowell Pkwy Atlanta, GA 30318",
    "https://itsmarta.com/Bankhead.aspx",
    -9,
    'ew'
  ],
  "BROOKHAVEN STATION": [
    [
      'brookhaven'
    ],
    "4047 Peachtree Road, NE Atlanta, GA 30319",
    "https://itsmarta.com/Brookhaven.aspx",
    17,
    'ns'
  ],
  "BUCKHEAD STATION": [
    [
      'buckhead'
    ],
    "3360 Peachtree Rd, NE Atlanta, GA 30326",
    "https://itsmarta.com/Buckhead.aspx",
    16,
    'ns'
  ],
  "CHAMBLEE STATION": [
    [
      'chamblee'
    ],
    "5200 New Peachtree Road Chamblee, GA 30341",
    "https://itsmarta.com/Chamblee.aspx",
    21,
    'ns'
  ],
  "CIVIC CENTER STATION": [
    [
      'civic',
      'civiccenter'
    ],
    "435 West Peachtree St, NW Atlanta, GA 30308",
    "https://itsmarta.com/Civic-Center.aspx",
    2,
    'ns'
  ],
  "COLLEGE PARK STATION": [
    [
      'college',
      'collegepark'
    ],
    "3800 Main St Atlanta, GA 30337",
    "https://itsmarta.com/College-Park.aspx",
    -15,
    'ns'
  ],
  "DECATUR STATION": [
    [
      'decatur'
    ],
    "400 Church St Decatur, GA 30030",
    "https://itsmarta.com/Decatur.aspx",
    13,
    'ew'
  ],
  "OMNI DOME STATION": [
    [
      'congress',
      'omnidome',
      'dome',
      'mercedesbenz',
      'mercedes-benz',
      'cnn',
      'statefarmarena',
      'philipsarena',
      'gwcc',
      'georgiaworldcongresscenter',
      'worldcongresscenter'
    ],
    "100 Centennial Olympic Park Atlanta, GA 30303",
    "https://itsmarta.com/Omni.aspx",
    -1,
    'ew'
  ],
  "DORAVILLE STATION": [
    [
      'doraville'
    ],
    "6000 New Peachtree Rd Doraville, GA 30340",
    "https://itsmarta.com/Doraville.aspx",
    24,
    'ns'
  ],
  "DUNWOODY STATION": [
    [
      'dunwoody'
    ],
    "1118 Hammond Dr Atlanta, GA 30328",
    "https://itsmarta.com/Dunwoody.aspx",
    22,
    'ns'
  ],
  "EAST LAKE STATION": [
    [
      'lake',
      'eastlake'
    ],
    "2260 College Ave Atlanta, GA 30307",
    "https://itsmarta.com/East-Lake.aspx",
    11,
    'ew'
  ],
  "EAST POINT STATION": [
    [
      'point',
      'eastpoint'
    ],
    "2848 East Main St East Point, GA 30344",
    "https://itsmarta.com/East-Point.aspx",
    -12,
    'ns'
  ],
  "EDGEWOOD CANDLER PARK STATION": [
    [
      'edgewood',
      'candlerpark'
    ],
    "1475 DeKalb Ave, NE Atlanta, GA 30307",
    "https://itsmarta.com/Edgewood-Candler-Park.aspx",
    8,
    'ew'
  ],
  "FIVE POINTS STATION": [
    [
      'five',
      'fivepoints',
      '5points'
    ],
    "30 Alabama St SW Atlanta, GA 30303",
    "https://itsmarta.com/Five-Points.aspx",
    0,
    'nsew'
  ],
  "GARNETT STATION": [
    [
      'garnett'
    ],
    "225 Peachtree St, SW Atlanta, GA 30303",
    "https://itsmarta.com/Garnett.aspx",
    -1,
    'ns'
  ],
  "GEORGIA STATE STATION": [
    [
      'georgia',
      'state',
      'georgiastate',
      'gsu',
      'school'
    ],
    "170 Piedmont Ave, SE Atlanta, GA 30303",
    "https://itsmarta.com/Georgia-State.aspx",
    1,
    'ew'
  ],
  "HAMILTON E HOLMES STATION": [
    [
      'hamilton',
      'holmes',
      'hamiltoneholmes',
      'h.e.holmes',
      'heholmes'
    ],
    "70 Hamilton E Holmes Dr, NW Atlanta, GA 30311",
    "https://itsmarta.com/Hamilton-E-Holmes.aspx",
    -9,
    'ew'
  ],
  "INDIAN CREEK STATION": [
    [
      'indian',
      'indiancreek'
    ],
    "901 Durham Park Rd Stone Mountain, GA 30083",
    "https://itsmarta.com/Indian-Creek.aspx",
    20,
    'ew'
  ],
  "INMAN PARK STATION": [
    [
      'inman',
      'inmanpark'
    ],
    "055 DeKalb Ave, NE Atlanta, GA 30307",
    "https://itsmarta.com/Inman-Park.aspx",
    6,
    'ew'
  ],
  "KENSINGTON STATION": [
    [
      'kensington'
    ],
    "3350 Kensington Rd Decatur, GA 30032",
    "https://itsmarta.com/Kensington.aspx",
    18,
    'ew'
  ],
  "KING MEMORIAL STATION": [
    [
      'king',
      'kingmemorial',
      'mlk'
    ],
    "377 Decatur St, SE Atlanta, GA 30312",
    "https://itsmarta.com/King-Memorial.aspx",
    3,
    'ew'
  ],
  "LAKEWOOD STATION": [
    [
      'lakewood'
    ],
    "2020 Lee St, SW Atlanta, GA 30310",
    "https://itsmarta.com/Lakewood.aspx",
    -8,
    'ns'
  ],
  "LENOX STATION": [
    [
      'lenox'
    ],
    "955 East Paces Ferry Rd, NE Atlanta, GA 30326",
    "https://itsmarta.com/Lenox.aspx",
    14,
    'ns'
  ],
  "LINDBERGH STATION": [
    [
      'lindbergh'
    ],
    "2424 Piedmont Rd, NE Atlanta, GA 30324",
    "https://itsmarta.com/Lindbergh.aspx",
    10,
    'ns'
  ],
  "MEDICAL CENTER STATION": [
    [
      'medical',
      'medicalcenter',
      'medcenter'
    ],
    "5711 Peachtree-Dunwoody Rd, NE Atlanta, GA 30342",
    "https://itsmarta.com/Medical-Center.aspx",
    20,
    'ns'
  ],
  "MIDTOWN STATION": [
    [
      'midtown'
    ],
    "41 Tenth St, NE Atlanta, GA 30309",
    "https://itsmarta.com/Midtown.aspx",
    4,
    'ns'
  ],
  "NORTH AVE STATION": [
    [
      'avenue',
      'northave',
      'northavenue',
      'gt',
      'georgiatech',
      'tech'
    ],
    "713 West Peachtree St, NW Atlanta, GA 30308",
    "https://itsmarta.com/North-Ave.aspx",
    3,
    'ns'
  ],
  "NORTH SPRINGS STATION": [
    [
      'springs',
      'northsprings'
    ],
    "7010 Peachtree Dunwoody Rd Sandy Springs, GA 30328",
    "https://itsmarta.com/North-Springs.aspx",
    27,
    'ns'
  ],
  "OAKLAND CITY STATION": [
    [
      'oakland',
      'oaklandcity'
    ],
    "1400 Lee St, SW Atlanta, GA 30310",
    "https://itsmarta.com/Oakland-City.aspx",
    -6,
    'ns'
  ],
  "PEACHTREE CENTER STATION": [
    [
      'peachtree',
      'peachtreecenter'
    ],
    "216 Peachtree St, NE Atlanta, GA 30303",
    "https://itsmarta.com/Peachtree-Center.aspx",
    1,
    'ns'
  ],
  "SANDY SPRINGS STATION": [
    [
      'sandy',
      'sandysprings'
    ],
    "1101 Mount Vernon Hwy Atlanta, GA 30338",
    "https://itsmarta.com/Sandy-Springs.aspx",
    25,
    'ns'
  ],
  "VINE CITY STATION": [
    [
      'vine',
      'vinecity'
    ],
    "502 Rhodes St, NW Atlanta, GA 30314",
    "https://itsmarta.com/Vine-City.aspx",
    -2,
    'ew'
  ],
  "WEST END STATION": [
    [
      'end',
      'westend'
    ],
    "680 Lee St, SW Atlanta, GA 30310",
    "https://itsmarta.com/West-End.aspx",
    -4,
    'ns'
  ],
  "WEST LAKE STATION": [
    [
      'lake',
      'westlake'
    ],
    "80 Anderson Ave, SW Atlanta, GA 30314",
    "https://itsmarta.com/West-Lake.aspx",
    -6,
    'ew'
  ]
}

nicknames = {
    'airport': 'AIRPORT STATION',
    'arts': 'ARTS CENTER STATION',
    'ashby': 'ASHBY STATION',
    'avondale': 'AVONDALE STATION',
    'bankhead': 'BANKHEAD STATION',
    'brookhaven': 'BROOKHAVEN STATION',
    'buckhead': 'BUCKHEAD STATION',
    'chamblee': 'CHAMBLEE STATION',
    'civic': 'CIVIC CENTER STATION',
    'college': 'COLLEGE PARK STATION',
    'decatur': 'DECATUR STATION',
    'doraville': 'DORAVILLE STATION',
    'dunwoody': 'DUNWOODY STATION',
    'east lake': 'EAST LAKE STATION',
    'point': 'EAST POINT STATION',
    'edgewood': 'EDGEWOOD CANDLER PARK STATION',
    'candler': 'EDGEWOOD CANDLER PARK STATION',
    'five': 'FIVE POINTS STATION',
    '5': 'FIVE POINTS STATION',
    'garnett': 'GARNETT STATION',
    'state': 'GEORGIA STATE STATION',
    'gsu': 'GEORGIA STATE STATION',
    'hamilton': 'HAMILTON E HOLMES STATION',
    'holmes': 'HAMILTON E HOLMES STATION',
    'indian': 'INDIAN CREEK STATION',
    'inman': 'INMAN PARK STATION',
    'kensington': 'KENSINGTON STATION',
    'king': 'KING MEMORIAL STATION',
    'lakewood': 'LAKEWOOD STATION',
    'lenox': 'LENOX STATION',
    'lindbergh': 'LINDBERGH STATION',
    'medical': 'MEDICAL CENTER STATION',
    'midtown': 'MIDTOWN STATION',
    'avenue': 'NORTH AVENUE STATION',
    'tech': 'NORTH AVENUE STATION',
    'springs': 'NORTH SPRINGS STATION',
    'oakland': 'OAKLAND CITY STATION',
    'peachtree': 'PEACHTREE CENTER STATION',
    'sandy': 'SANDY SPRINGS STATION',
    'vine': 'VINE CITY STATION',
    'end': 'WEST END STATION',
    'west lake': 'WEST LAKE STATION'
}

directions = ['north','south','east','west']

translator = str.maketrans('', '', string.punctuation)

def marta_mentioned(status):
    if hasattr(status, 'retweeted_status'):
        return False
    elif not status.entities['user_mentions']:
        return False
    else:
        mentioned = False
        for u in status.entities['user_mentions']:
            if u['screen_name'].lower() == 'martatimes':
                mentioned = True
                break
        if mentioned:
            return True
        else:
            return False
        
def process_tweet(status):
    
    text = status.text.lower().translate(translator).split()
    starting_station = None
    ending_station = None
    direction = None
    response = None
    for keyword, station in nicknames.items():
        if keyword in text:
            if starting_station:
                ending_station = station
                break
            else:
                starting_station = station
    for d in directions:
        if d in text and not station_or_direction(text[text.index(d):]):
            direction = d
    if starting_station:
        if ending_station and ending_station != starting_station:
            response = travel_time(starting_station, ending_station)
        else:
            response = arrival_times(starting_station, direction)
    else:
        response = "I don't know what you're asking. Please include which station(s)."
    return response
        
def station_or_direction(text):
    """
    Returns True if stations, False if direction
    """
    text = text
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
        
def travel_time(startPoint, endPoint):
    time = 0
    if (stations[startPoint][4] != stations[endPoint][4]): # one is ns, other is ew (5points is nsew, but time = 0, so not effect)
        # s -> 5 + 5 -> e
        time = abs(stations[startPoint][3]) + abs(stations[endPoint][3])
    else:
        # both on same track, so s - e
        time = abs(stations[startPoint][3] - stations[endPoint][3])
    return "It takes approximately " + str(time) + (" minutes" if time > 1 else " minute") + " to go from " + startPoint.title() + " to " + endPoint.title()

def arrival_times(station, direction):
    trains = get_trains(station=station)
    line = None
    final_trains = []
    if trains:
        if direction is not None and direction.lower() in ['n','s','e','w','north','south','east','west','northbound','southbound','eastbound','westbound']:
            if direction.lower().startswith('n'):
                direction = 'N'
            elif direction.lower().startswith('s'):
                direction = 'S'
            elif direction.lower().startswith('e'):
                direction = 'E'
            elif direction.lower().startswith('w'):
                direction = 'W'
            if line is not None and line.lower() in ['g','r','b','gold','red','green','blue','y','yellow','o','orange']:
                if line.lower().startswith('r'):
                    line = 'RED'
                elif line.lower().startswith('y') or line.lower().startswith('o') or line.lower().startswith('go'):
                    line = 'GOLD'
                elif line.lower().startswith('b'):
                    line = 'BLUE'
                elif line.lower().startswith('g'):
                    line = 'GREEN'
            else:
                line = None
        else:
            direction = None
            final_trains = []
        used = []
        if direction:
            if line:
                for t in trains:
                    if t.line == line and t.direction == direction and str(t.line + t.direction) not in used:
                        if t.waiting_time[0].isdigit():
                            used.append(str(t.line + t. direction))
                        final_trains.append(t)
            else:
                for t in trains:
                    if t.direction == direction and str(t.line + t.direction) not in used:
                        if t.waiting_time[0].isdigit():
                            used.append(str(t.line + t.direction))
                        final_trains.append(t)
        else:
            for t in trains:
                if str(t.line + t.direction) not in used:
                    if t.waiting_time[0].isdigit():
                            used.append(str(t.line + t. direction))
                    final_trains.append(t)
        if final_trains:
            final_message = ""
            for t in final_trains:
                if len(final_message) < 240:
                    final_message = final_message +  t.line.capitalize() + " - " + t.destination + " (" + t.direction + "): " + (t.waiting_time if t.waiting_time[0].isdigit() else t.waiting_time) + "\n"
                else:
                    break
            return final_message
        else:
            return "No trains in the near future."
    else:
        return "No trains near that station."
    

def respond(status, response):
    twitter.update_status('@' + str(status.user.screen_name) + " " + response, in_reply_to_status_id=status.id)
    print("Responded with: " + response)

class StdOutListener(StreamListener):

    def on_status(self, status):
        if marta_mentioned(status):
            response = process_tweet(status)
            print("Replying to this tweet from @" + status.user.screen_name + ": \'" + status.text + "\'...")
            respond(status, response)
        return True

    def on_error(self, status_code):
        print("Error, code" + str(status_code))

l = StdOutListener()
stream = Stream(auth, l)
stream.filter(track=['martatimes'])


#!/usr/bin/python3

import sqlite3
import itertools
import json
import os
import datetime

def load_json(path):
  out = None
  if os.path.isfile(path):
    with open(path, 'r') as f:
      out = json.load(f)
  return out

path_transit_database = "tokyo-transit.db"
path_events = "events.json"

conn = sqlite3.connect(path_transit_database)
c = conn.cursor()

route_request_template = '''
  SELECT from_id,
         to_id,
         mins,
         cost,
         transfers
  FROM routes
  WHERE from_id = "{}"
  AND to_id = "{}";
'''

translation_request_template = '''
    SELECT station_id
    FROM stations
    WHERE english = "{}"
'''

def get_station_id(station_name):
  request = translation_request_template.format(station_name)
  c.execute(request)
  res = c.fetchone()
  if res is not None:
    return int(res[0])
  else:
    return None

def cost_string(cost):
    return "free" if cost == 0 else "¥‎{}".format(cost)

def duration_string(duration):
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        if minutes > 0:
            return "{}h {}m".format(hours, minutes)
        else:
            return "{}h".format(hours)
    else:
        return "{}m".format(minutes)

class Event(object):
    def __init__(self, name, station, duration, cost=0, tags=[]):
        self.name = name
        self.station = station
        self.station_id = get_station_id(station)
        if type(duration) is float or type(duration) is int:
            self.duration = datetime.timedelta(hours=duration)
        else:
            self.duration = duration
        self.cost = cost
        self.tags = [tags]

    def __str__(self):
        return "{}, {} Station, {} Yen, {}, {}".format(self.name,
            self.station,
            self.duration,
            self.cost,
            self.tags)

class Route(object):
    def __init__(self, from_station_id, to_station_id):
        self.from_station_id = from_station_id
        self.to_station_id = to_station_id
        self.duration = None
        self.cost = None
        self.calculate()

    def calculate(self, reverse=False):
        stations = [self.from_station_id, self.to_station_id]
        if reverse:
            stations.reverse()
        request = route_request_template.format(*stations)
        c.execute(request)
        res = c.fetchone()
        if res is None:
            if reverse is False:
                return self.calculate(reverse=True)
            else:
                print("Cant find link between stations")
                raise
        else:
            self.duration = datetime.timedelta(minutes=res[2])
            self.cost = res[3]

class Requirements(object):
    def __init__(self, max_cost, max_duration):
        self.max_cost = max_cost
        self.max_duration = max_duration

class Tour(object):
    def __init__(self, start_time):
        self.start_time = start_time
        self.cost = 0
        self.duration = datetime.timedelta()
        self.tags = []
        self.events = []
        self.routes = []

    def add_event(self, event):
        self.events.append(event)
        self.cost += event.cost
        self.duration += event.duration

    def add_events(self, events):
        for event in events:
            self.add_event(event)

    def add_route(self, route):
        self.cost += route.cost
        self.duration += route.duration
        self.routes.append(route)

    def calculate_routes(self):
        if len(self.events) > 1:
            station_ids = [x.station_id for x in self.events]
            for index in range(len(station_ids) - 1):
                self.add_route(Route(self.events[index].station_id,
                                     self.events[index+1].station_id))

    def print_itineary(self):
        print(" - Total cost: {}".format(cost_string(self.cost)))
        print(" - Total time: {}".format(duration_string(self.duration)))
        print(" - Itineary:")
        clock = self.start_time
        num_events = len(self.events)
        verb = "Meet"
        for index in range(num_events):
            event = self.events[index]
            print("     {}: {} at {} Station".format(clock.strftime("%H:%M"), verb, event.station))
            verb = "Arrive"
            print("            {} ({}, {})".format(event.name, duration_string(event.duration), cost_string(event.cost)))
            print("")
            clock += event.duration
            if index < len(self.routes):
                route = self.routes[index]
                print("     {}: Train from {} Station to {} Station ({} mins, {})".format(
                    clock.strftime("%H:%M"),
                    event.station,
                    self.events[index + 1].station,
                    duration_string(route.duration),
                    cost_string(route.cost)))
                clock += route.duration
                print("")
        print("     {}: Finish tour at {} Station".format(clock.strftime("%H:%M"), self.events[-1].station))

def tour_is_acceptable(tour, requirements):
    if tour.cost > requirements.max_cost:
        return False
    elif tour.duration > requirements.max_duration:
        return False
    else:
        return True

def check_tour_acceptable(tour, requirements):
    """ Optimisation to avoid calculating routes if not necessary"""
    if tour_is_acceptable(tour, requirements):
        tour.calculate_routes()
        return tour_is_acceptable(tour, requirements)
    return False

def generate_event_combinations(event_list):
    combos = []
    for i in range(1, len(event_list)+1):
        els = [list(x) for x in itertools.combinations(event_list, i)]
        combos.extend(els)
    return combos

def load_events(path_events):
    event_list = load_json(path_events)
    events = [Event(*event) for event in event_list]
    return events


max_cost = 100000
tour_start = datetime.datetime(2020, 7, 4, 8, 0)
tour_end = datetime.datetime(2020, 7, 4, 17, 0)
max_duration = tour_end - tour_start
requirements = Requirements(max_cost, max_duration)

events = load_events(path_events)
valid_tours = []

for event_combination in generate_event_combinations(events):
    valid_permutations = []
    for event_permutations in itertools.permutations(event_combination):
        tour = Tour(tour_start)
        tour.add_events(event_permutations)
        if check_tour_acceptable(tour, requirements):
            valid_permutations.append(tour)

    durations = [tour.duration for tour in valid_permutations]
    if len(durations) != 0:
        min_duration = min(durations)
        valid_tours += [tour for tour in valid_permutations if tour.duration == min_duration]

for i, tour in enumerate(valid_tours):
    print("Tour {}".format(i))
    tour.print_itineary()
    print("")

#!/usr/bin/python3

import csv
import datetime
import itertools
import json
import os
import sqlite3
import time

path_transit_database = "tokyo-transit.db"
path_events = "events.csv"

conn = sqlite3.connect(path_transit_database)
c = conn.cursor()


def load_csv(csv_path):
    out = []
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        out = list(reader)
    return out


def parse_csv(csv_path, key_translations={}):
    csv_data = load_csv(csv_path)
    header = csv_data[0]
    # Apply any header translations
    for key in key_translations:
        header[header.index(key)] = key_translations[key]

    data = csv_data[1:]
    out = []
    for row in data:
        out.append({key: row[idx]
                    for idx, key in enumerate(header) if key is not None})
    return out


def load_events(path_events):
    keys = {
        "Place Name": "name",
        "Train Station": "station",
        "Time at Place (hours)": "duration",
        "Cost (per person)": "cost",
        "Opens": "opens",
        "Closes": "closes",
        "Category": "category",
        "Description": "description",
        "Station Valid": None
    }
    data = parse_csv(path_events, keys)
    events = [Event(x) for x in data]
    return events


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

    def __init__(self, info):
        self.name = info['name']
        self.station = Station(info['station'])
        if type(info['duration']) is float or type(info['duration']) is int:
            self.duration = datetime.timedelta(hours=info['duration'])
        elif type(info['duration']) is str:
            self.duration = datetime.timedelta(hours=float(info['duration']))
        else:
            self.duration = info['duration']

        self.cost = int(info['cost'])
        self.opens = time.strftime(info['opens'])
        self.closes = time.strftime(info['closes'])
        self.category = info['category']
        self.description = info['description']

    def __str__(self):
        return "Event: " + str({
            "name": self.name,
            "station": self.station,
            "duration": self.duration,
            "cost": self.cost,
            "opens": self.opens,
            "closes": self.closes,
            "category": self.category,
            "description": self.description
        })


class Station(object):
    request_template = '''
        SELECT station_id
        FROM stations
        WHERE english = "{}"
    '''

    def __init__(self, name):
        self.name = name
        self.id = self.get_station_id(name)

    def __str__(self):
        return "Station: " + str({
            "name": self.name,
            "id": self.id
        })

    def get_station_id(self, name):
        request = self.request_template.format(self.name)
        c.execute(request)
        res = c.fetchone()
        if res is not None:
            return int(res[0])
        else:
            return None


class Route(object):
    request_template = '''
      SELECT from_id,
             to_id,
             mins,
             cost,
             transfers
      FROM routes
      WHERE from_id = "{}"
      AND to_id = "{}";
    '''

    def __init__(self, from_station, to_station):
        self.from_station = from_station
        self.to_station = to_station
        if from_station.id == to_station.id:
            self.duration = datetime.timedelta(minutes=0)
            self.cost = 0
        else:
            self.duration = None
            self.cost = None
            self.calculate()

    def calculate(self, reverse=False):
        stations = [self.from_station.id, self.to_station.id]
        if reverse:
            stations.reverse()
        request = self.request_template.format(*stations)
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


class Specifications(object):
    cost_max = None
    cost_min = None
    duration_max = None
    duration_min = None
    num_people = None
    time_end_early = None
    time_end_late = None
    time_start = None

    def __init__(self, num_people=1, start_hour=8, start_minute=0):
        self.num_people = num_people
        self.time_start = datetime.datetime(
            1970, 1, 1, start_hour, start_minute)

    def set_cost_max(self, cost):
        self.cost_max = cost

    def set_cost_min(self, cost):
        self.cost_min = cost

    def set_time_end_late(self, hour, minute):
        self.time_end_late = datetime.datetime(1970, 1, 1, hour, minute)
        self.duration_max = self.time_end_late - self.time_start

    def set_time_end_early(self, hour, minute):
        self.time_end_early = datetime.datetime(1970, 1, 1, hour, minute)
        self.duration_min = self.time_end_early - self.time_start


class Tour(object):

    def __init__(self, specs):
        self.specs = specs
        self.cost_events = 0
        self.cost_transport = 0
        self.duration_events = datetime.timedelta()
        self.duration_transport = datetime.timedelta()
        self.events = []
        self.routes = []

    def add_event(self, event):
        self.events.append(event)
        self.cost_events += event.cost
        self.duration_events += event.duration

    def add_events(self, events):
        for event in events:
            self.add_event(event)

    def add_route(self, route):
        self.cost_transport += route.cost
        self.duration_transport += route.duration
        self.routes.append(route)

    def total_cost(self):
        return self.cost_events + self.cost_transport

    def total_duration(self):
        return self.duration_events + self.duration_transport

    def calculate_routes(self):
        if len(self.events) > 1:
            stations = [x.station for x in self.events]
            for index in range(len(stations) - 1):
                self.add_route(Route(stations[index],
                                     stations[index + 1]))

    def meets_specs(self):
        if specs.cost_max is not None and self.total_cost() > specs.cost_max:
            return False
        elif specs.cost_min is not None and self.total_cost() < specs.cost_min:
            return False
        elif specs.duration_max is not None and self.total_duration() > specs.duration_max:
            return False
        elif specs.duration_min is not None and self.total_duration() < specs.duration_min:
            return False
        else:
            return True

    def optimise(self):
        if self.meets_specs():
            self.calculate_routes()

    def print_itineary(self):
        print(" - Total cost: {}".format(cost_string(self.total_cost())))
        print(" - Total time: {}".format(duration_string(self.total_duration())))
        print(" - Itineary:")
        clock = self.specs.time_start
        num_events = len(self.events)
        verb = "Meet"
        for index in range(num_events):
            event = self.events[index]
            print("     {}: {} at {} Station".format(
                clock.strftime("%H:%M"), verb, event.station.name))
            verb = "Arrive"
            print("            {} ({}, {})".format(event.name,
                                                   duration_string(event.duration), cost_string(event.cost)))
            print("")
            clock += event.duration
            if index < len(self.routes):
                route = self.routes[index]
                print("     {}: Train from {} Station to {} Station ({} mins, {})".format(
                    clock.strftime("%H:%M"),
                    event.station.name,
                    self.events[index + 1].station.name,
                    duration_string(route.duration),
                    cost_string(route.cost)))
                clock += route.duration
                print("")
        print("     {}: Finish tour at {} Station".format(
            clock.strftime("%H:%M"), self.events[-1].station.name))


def generate_event_combinations(event_list):
    combos = []
    for i in range(1, len(event_list) + 1):
        els = [list(x) for x in itertools.combinations(event_list, i)]
        combos.extend(els)
    return combos


events = load_events(path_events)

# Setup tour specifications
specs = Specifications(num_people=1, start_hour=8)
specs.set_cost_max(100000)
specs.set_time_end_early(16, 0)
specs.set_time_end_late(17, 0)

valid_tours = []

event_combos = generate_event_combinations(events)
for event_combination in event_combos:
    tour = Tour(specs)
    tour.add_events(event_combination)
    tour.optimise()
    if tour.meets_specs():
        valid_tours.append(tour)
    # valid_permutations = []
    # print('strt')
    # for event_permutations in itertools.permutations(event_combination):
    #     # print('perm')
    #     tour = Tour(tour_start)
    #     tour.add_events(event_permutations)
    #     if check_tour_acceptable(tour, specs):
    #         valid_permutations.append(tour)
    # print('end')

    # durations = [tour.duration for tour in valid_permutations]
    # print('checked')
    # if len(durations) != 0:
    #     min_duration = min(durations)
    #     valid_tours += [tour for tour in valid_permutations if tour.duration == min_duration]

for i, tour in enumerate(valid_tours):
    print("Tour {}".format(i))
    tour.print_itineary()
    print("")

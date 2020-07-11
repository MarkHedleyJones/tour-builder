#!/usr/bin/python3

import csv
import datetime
import itertools
import json
import os
import sqlite3
import time

path_transit_database = "tokyo-transit.db"
path_activities = "activities.csv"

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


def load_activities(path_activities):
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
    data = parse_csv(path_activities, keys)
    activities = [Activity(x) for x in data]
    return activities


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


class Specifications(object):
    min_end_time = None
    max_end_time = None
    max_cost = None
    max_duration = None
    min_cost = None
    min_duration = None
    num_people = None
    start_time = None

    def __init__(self, num_people=1, start_hour=8, start_minute=0):
        self.num_people = num_people
        self.start_time = datetime.datetime(
            1970, 1, 1, start_hour, start_minute)

    def set_max_cost(self, cost):
        self.max_cost = cost

    def set_min_cost(self, cost):
        self.min_cost = cost

    def set_max_end_time(self, hour, minute):
        self.max_end_time = datetime.datetime(1970, 1, 1, hour, minute)
        self.max_duration = self.max_end_time - self.start_time

    def set_min_end_time(self, hour, minute):
        self.min_end_time = datetime.datetime(1970, 1, 1, hour, minute)
        self.min_duration = self.min_end_time - self.start_time

    def too_expensive(self, cost):
        return self.max_cost is not None and cost > self.max_cost

    def too_cheap(self, cost):
        return self.min_cost is not None and cost < self.min_cost

    def too_long(self, duration):
        return self.max_duration is not None and duration > self.max_duration

    def too_short(self, duration):
        return self.min_duration is not None and duration < self.min_duration

    def below_maximum(self, cost, duration):
        return not self.too_expensive(cost) and not self.too_long(duration)


class Event(object):
    # TODO: Move opens and closes to Event (even for trains etc)
    def __init__(self, cost, duration):
        self.cost = cost
        self.duration = duration


class Activity(Event):
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
        return "Activity: " + str({
            "name": self.name,
            "station": self.station,
            "duration": self.duration,
            "cost": self.cost,
            "opens": self.opens,
            "closes": self.closes,
            "category": self.category,
            "description": self.description
        })


class Transport(Event):

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

    def __init__(self, start, finish):
        if type(start) != type(finish):
            print("Error!")
        elif type(start) == Station:
            self.from_station = start
            self.to_station = finish
        elif type(start) == Activity:
            self.from_station = start.station
            self.to_station = finish.station
        if self.from_station.id == self.to_station.id:
            self.duration = datetime.timedelta(minutes=0)
            self.cost = 0
        else:
            self.duration = None
            self.cost = None
            self.calculate()

    def calculate(self):
        stations = [self.from_station.id, self.to_station.id]
        stations.sort()
        request = self.request_template.format(*stations)
        c.execute(request)
        res = c.fetchone()
        if res is None:
            print("Cant find link between stations")
            raise
        else:
            self.duration = datetime.timedelta(minutes=res[2])
            self.cost = res[3]


class Tour(object):

    def __init__(self, specs):
        self.cost = 0
        self.duration = datetime.timedelta(minutes=0)
        self.end_time = specs.start_time
        self.events = []
        self.specs = specs

    def _add_event(self, event):
        self.cost += event.cost
        self.duration += event.duration
        self.end_time += event.duration
        self.events.append(event)

    def add_activity(self, event):
        success = False
        last_event = self.events[-1] if len(self.events) > 0 else None
        cost = self.cost + event.cost
        duration = self.duration + event.duration

        # Check if transport is required
        if last_event is None or last_event.station == event.station:
            # Check that this wouldn't exceed budgets
            if self.specs.below_maximum(cost, duration):
                self._add_event(event)
                success = True
        else:
            # Calculate the transport
            transport = Transport(last_event, event)
            cost += transport.cost
            duration += transport.duration

            # Check that this wouldn't exceed budgets
            if self.specs.below_maximum(cost, duration):
                self._add_event(transport)
                self._add_event(event)
                success = True

        return success


def generate_event_combinations(event_list):
    combos = []
    for i in range(1, len(event_list) + 1):
        els = [list(x) for x in itertools.combinations(event_list, i)]
        combos.extend(els)
    return combos


activities = load_activities(path_activities)

# Setup tour specifications
specs = Specifications(num_people=1, start_hour=8)
specs.set_max_cost(100000)
specs.set_min_end_time(16, 0)
specs.set_max_end_time(17, 0)

valid_tours = []

event_combos = generate_event_combinations(activities)
for event_combination in event_combos:
    tour = Tour(specs)
    for activity in event_combination:
        tour.add_activity(activity)

#!/usr/bin/python3

import copy
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

ref_date = datetime.date(1970, 1, 1)
day_start = datetime.time(0, 0, 0)
day_end = datetime.time(23, 59, 59)


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
        return "{} Station".format(self.name)

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

    def __init__(self, num_people=1, start_time=datetime.time(8, 0)):
        self.num_people = num_people
        self.start_time = datetime.datetime.combine(ref_date, start_time)

    def set_max_cost(self, cost):
        self.max_cost = cost

    def set_min_cost(self, cost):
        self.min_cost = cost

    def set_max_end_time(self, max_end_time):
        self.max_end_time = datetime.datetime.combine(ref_date, max_end_time)
        self.max_duration = self.max_end_time - self.start_time

    def set_min_end_time(self, min_end_time):
        self.min_end_time = datetime.datetime.combine(ref_date, min_end_time)
        self.min_duration = self.min_end_time - self.start_time

    def too_expensive(self, cost):
        return self.max_cost is not None and cost > self.max_cost

    def too_cheap(self, cost):
        return self.min_cost is not None and cost < self.min_cost

    def too_long(self, duration):
        return self.max_duration is not None and duration > self.max_duration

    def too_short(self, duration):
        return self.min_duration is not None and duration < self.min_duration

    def above_maximum(self, cost, duration):
        return self.too_expensive(cost) or self.too_long(duration)

    def below_maximum(self, cost, duration):
        return not self.too_expensive(cost) and not self.too_long(duration)

    def above_minimum(self, cost, duration):
        return not self.too_cheap(cost) and not self.too_short(duration)

    def within_spec(self, cost, duration):
        return self.above_minimum(cost, duration) and self.below_maximum(cost, duration)


def to_time(input, default=datetime.time(0, 0)):
    if input is None or input == '':
        return datetime.datetime.combine(ref_date, default)
    elif type(input) is type(datetime.datetime.now()):
        return input
    elif type(input) is type(datetime.time()):
        return datetime.datetime.combine(ref_date, input)
    elif type(input) is str:
        a = datetime.datetime.strptime(input, '%H:%M')
        return datetime.datetime.combine(ref_date, a.time())
    else:
        print("Error: unknown time type {}".format(input))


def to_duration(input, default=datetime.timedelta()):
    if input is None or input is '':
        return datetime.timedelta(minutes=0)
    elif type(input) is str:
        return datetime.timedelta(hours=float(input))
    elif type(input) is type(datetime.timedelta()):
        return input
    elif type(input) is float or type(input) is int:
        return datetime.timedelta(hours=input)
    else:
        print(type(input))
        print("Error: unknown duration type {}".format(input))


def to_money(input, default=0):
    if type(input) is int:
        return input
    elif input is None:
        return default
    else:
        return int(input)


class Event(object):
    # TODO: Move opens and closes to Event (even for trains etc)
    def __init__(self, cost=None, duration=None, available_from=None,
                 available_until=None):
        self.cost = to_money(cost)
        self.duration = to_duration(duration)
        self.available_from = to_time(available_from)
        self.available_until = to_time(available_until, default=day_end)

    def __str__(self):
        return "Generic event"


class Meet(Event):
    def __init__(self, station, duration=None):
        self.station = station
        if duration is None:
            duration = datetime.timedelta(minutes=15)
        super().__init__(cost=0, duration=duration)

    def __str__(self):
        return "Meet at {}".format(self.station)


class Activity(Event):
    category_to_verb = {
        'restaurant': 'Dine at',
        'cultural': 'See',
        'cafe': 'Take a break at',
        'shopping': "Shop at"
    }

    def __init__(self, info):
        self.name = info['name']
        self.station = Station(info['station'])
        self.category = info['category']
        self.description = info['description']
        super().__init__(cost=int(info['cost']),
                         duration=info['duration'],
                         available_from=info['opens'],
                         available_until=info['closes'])

    def __str__(self):
        verb = "Visit"
        if self.category in self.category_to_verb:
            verb = self.category_to_verb[self.category]
        return "{} {}".format(verb, self.name)

    def __repr__(self):
        return self.name


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

    def __str__(self):
        return "Train from {} to {}".format(self.from_station, self.to_station)


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

        # Check that we can start this now
        if self.end_time < event.available_from:
            return False
        # Check that its available for as long as we need
        if self.end_time + event.duration > event.available_until:
            return False

        # Check if transport is required
        if last_event is None:
            # Add the first meet & greet
            self._add_event(Meet(event.station))
            # Check that this event wouldn't exceed budgets
            if self.specs.below_maximum(cost, duration):
                self._add_event(event)
                return True
        elif last_event.station.name == event.station.name:
            # Check that this wouldn't exceed budgets
            if self.specs.below_maximum(cost, duration):
                self._add_event(event)
                return True
        else:
            # Calculate the transport
            transport = Transport(last_event, event)
            cost += transport.cost
            duration += transport.duration
            # Check that this wouldn't exceed budgets
            if self.specs.below_maximum(cost, duration):
                self._add_event(transport)
                self._add_event(event)
                return True
        return False

    def within_spec(self):
        return self.specs.within_spec(self.cost, self.duration)

    def exceeds_spec(self):
        return self.specs.above_maximum(self.cost, self.duration)

    def remaining_time(self):
        return self.specs.max_duration - self.duration

    def remaining_money(self):
        return self.specs.max_cost - self.cost

    def __str__(self):
        return "Tour with {} events".format(len(self.events))

    def print_itineary(self):
        print(" - Total cost: {}".format(cost_string(self.cost)))
        print(" - Total time: {}".format(duration_string(self.duration)))
        print(" - Itineary:")
        verb = "Meet"
        clock = self.specs.start_time
        for event in self.events:
            print("     {}: {}".format(clock.strftime("%H:%M"), event))
            clock += event.duration
        print("     {}: Finish tour at {}".format(
            clock.strftime("%H:%M"), self.events[-1].station))


def generate_event_combinations(event_list):
    combos = []
    for i in range(1, len(event_list) + 1):
        els = [list(x) for x in itertools.combinations(event_list, i)]
        combos.extend(els)
    return combos


activities = load_activities(path_activities)

# Setup tour specifications
specs = Specifications(num_people=1, start_time=datetime.time(8, 0))
specs.set_max_cost(100000)
specs.set_min_end_time(datetime.time(16, 0))
specs.set_max_end_time(datetime.time(17, 0))


def build_tours(valid_tours, tour, activities, depth=0):
    depth += 1

    cost_limit = tour.remaining_money()
    duration_limit = tour.remaining_time()

    activities = [x for x in activities if x.duration <
                  duration_limit and x.cost < cost_limit]

    for index in range(len(activities)):
        activities_copy = copy.copy(activities)
        activity = activities_copy[index]
        activities_copy.remove(activity)
        tour_copy = copy.deepcopy(tour)
        if tour_copy.add_activity(activity):
            if tour_copy.within_spec():
                valid_tours.append(tour_copy)
            build_tours(valid_tours, tour_copy, activities_copy, depth)


tours = []

for index in range(len(activities)):
    activity_list = copy.copy(activities)
    tour = Tour(specs)
    if tour.add_activity(activity_list.pop(index)):
        build_tours(tours, tour, activity_list)

for tour_number, tour in enumerate(tours):
    print("Tour Idea {}:".format(tour_number))
    tour.print_itineary()
    print("")
("")

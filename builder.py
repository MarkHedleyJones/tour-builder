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


def time(hours, minutes=0, seconds=0):
    return datetime.datetime.combine(ref_date,
                                     datetime.time(hours, minutes, seconds))


day_start = time(0)
day_end = time(23, 59, 59)
minimum_event_duration = datetime.timedelta(minutes=15)

meal_times = {
    'breakfast': {
        'start': day_start,
        'end': time(10, 30)
    },
    'lunch': {
        'start': time(10, 30),
        'end': time(15, 30)
    },
    'dinner': {
        'start': time(15, 30),
        'end': day_end
    },
    'coffee': {
        'start': day_start,
        'end': time(17, 0)
    }
}


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
    activities = []
    for activity in data:
        activities.append(Activity(location=Station(activity['station']),
                                   duration=to_duration(activity['duration']),
                                   title=activity['name'],
                                   cost=to_money(activity['cost']),
                                   available_from=to_time(activity['opens']),
                                   available_until=to_time(activity['closes']),
                                   category=activity['category']))
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


class Location(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class Station(Location):
    request_template = '''
        SELECT station_id
        FROM stations
        WHERE english = "{}"
    '''

    def __init__(self, name):
        super(Station, self).__init__(name)
        self.id = self.get_station_id(name)

    def get_station_id(self, name):
        request = self.request_template.format(self.name)
        c.execute(request)
        res = c.fetchone()
        if res is not None:
            return int(res[0])
        else:
            raise
            return None

    def __str__(self):
        return "{} Station".format(self.name)


class Specifications(object):
    min_end_time = None
    max_end_time = None
    max_cost = None
    max_duration = None
    min_cost = None
    min_duration = None
    num_people = None
    start_time = None
    include_breakfast = None
    include_lunch = None
    include_dinner = None
    include_coffee = None

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


def to_time(input, default=day_start):
    if input is None or input == '':
        return default
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
    def __init__(self, title, location, duration, cost, category=None):
        self.title = title
        self.location = location
        self.duration = duration
        self.cost = cost
        self.category = category

    def __str__(self):
        return self.title


class Meet(Event):
    def __init__(self, location):
        super(Meet, self).__init__(title=location.name,
                                   location=location,
                                   duration=datetime.timedelta(minutes=15),
                                   cost=0,
                                   category="meet")


class Activity(Event):
    available_from = None
    available_until = None

    def __init__(self, title, location, duration, cost,
                 available_from=day_start, available_until=day_end,
                 category=None):
        super(Activity, self).__init__(title, location, duration, cost)
        self.available_from = available_from
        self.available_until = available_until
        self.category = category

    def meal_category(self, time):
        if self.category == 'food':
            for meal_type in meal_times.keys():
                if time > meal_times[meal_type]['start'] \
                        and time < meal_times[meal_type]['end']:
                    return meal_type
        elif self.category == 'coffee':
            if time > meal_times['coffee']['start'] \
                    and time < meal_times['coffee']['end']:
                return 'coffee'
        return False

    def __str__(self):
        return self.title

    def __repr__(self):
        return self.title


class Transport(Event):
    def __init__(self, from_location, to_location, duration, cost, category="move"):
        self.destination = to_location
        title = "{} -> {}".format(from_location, to_location)
        super(Transport, self).__init__(
            title, from_location, duration, cost, category)


class TrainRide(Transport):

    def __init__(self, from_station, to_station):
        super(TrainRide, self).__init__(from_station, to_station,
                                        datetime.timedelta(), 0, "ride")
        self.calculate()

    def calculate(self):
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
        stations = [self.location.id, self.destination.id]
        stations.sort()
        request = request_template.format(*stations)
        c.execute(request)
        res = c.fetchone()
        if res is None:
            print("Cant find link between stations")
            raise
        else:
            self.duration = datetime.timedelta(minutes=res[2])
            self.cost = res[3]

    def __str__(self):
        return "Ride {} -> {}".format(self.location, self.destination)


def get_transport(start, end):
    if isinstance(start, Event):
        start = start.location
    if isinstance(end, Event):
        end = end.location

    # For now we're only working with train stations
    if type(start) != Station:
        print("Bad start location")
        print(type(start))
        raise
    if type(end) != Station:
        print("Bad end location")
        print(type(end))
        raise

    # Return nothing if the start location is the end location
    if start.name == end.name:
        return None

    # Return a train ride
    return TrainRide(start, end)


class Tour(object):

    category_to_verb = {
        'food': 'Eat at',
        'cultural': 'See',
        'coffee': 'Grab a drink at',
        'shopping': "Shop at",
        'meet': "Meet at",
        'ride': "Ride from"
    }

    def __init__(self, specs):
        self.cost = 0
        self.duration = datetime.timedelta(minutes=0)
        self.end_time = specs.start_time
        self.events = []
        self.specs = specs
        self.included_meals = {}

    def _add_event(self, event):
        if type(event) == Activity:
            meal = event.meal_category(self.end_time)
            index = len(self.events)
            if meal is not False:
                self.included_meals[index] = meal
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
        if (self.end_time + event.duration) > event.available_until:
            return False

        # Check that this meal hasn't already been included in the tour
        food_categories = ['coffee', 'food']
        if type(event) == Activity:
            # Don't do two food activities in a row
            if event.category in food_categories \
                    and last_event is not None \
                    and last_event.category in food_categories:
                return False

            # Don't have the same meal twice
            meal = event.meal_category(self.end_time)
            if meal is not False and meal in self.included_meals.values():
                return False
            elif meal is False and event.category == 'coffee':
                # It's cofee but out of hours!
                return False

        # Check if transport is required
        if last_event is None:
            # Add the first meet & greet
            self._add_event(Meet(event.location))
            # Check that this event wouldn't exceed budgets
            if self.specs.below_maximum(cost, duration):
                self._add_event(event)
                return True
        elif last_event.location.name == event.location.name:
            # Check that this wouldn't exceed budgets
            if self.specs.below_maximum(cost, duration):
                self._add_event(event)
                return True
        else:
            # Calculate the transport
            transport = get_transport(last_event, event)
            if transport is not None:
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
        print(" - Included meals: {}".format(", ".join(self.included_meals.values())))
        print(" - Itineary:")
        clock = self.specs.start_time
        for index, event in enumerate(self.events):
            title = "{}".format(event.title)
            if index in self.included_meals.keys():
                title = "{} at {}".format(
                    self.included_meals[index].title(), event.title)
            elif event.category in self.category_to_verb:
                title = "{} {}".format(
                    self.category_to_verb[event.category], event.title)

            print("     {}: {}".format(clock.strftime("%H:%M"), title))
            clock += event.duration
        print("     {}: Finish tour at {}".format(
            clock.strftime("%H:%M"), self.events[-1].location))


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
        next_activity = activities_copy[index]
        activities_copy.remove(next_activity)
        tour_copy = copy.deepcopy(tour)
        if tour_copy.add_activity(next_activity):
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

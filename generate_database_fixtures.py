#!/usr/bin/python3

import copy
import csv
import datetime
import itertools
import json
import os
import sqlite3
import time

path_activities = "activities.csv"
path_fixtures = "django_db_fixtures.json"
path_transit_database = "tokyo-transit.db"

conn = sqlite3.connect(path_transit_database)
c = conn.cursor()

station_id_pks = {}
station_name_pks = {}
activity_type_pks = {}


def write_json(path, data):
    with open(path, 'w') as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False))


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
    return parse_csv(path_activities, keys)


def gen_station_fixtures(basename):
    global station_id_pks, station_name_pks

    query = '''
        SELECT
            english,
            station_id
        FROM stations
    '''
    c.execute(query)
    results = c.fetchall()
    out = []
    for index, result in enumerate(results):
        pk = index + 1
        station_name = result[0]
        station_id = int(result[1])
        if station_id in station_id_pks:
            print("A station with this station_id has already been added, skipping")
            print(result)
            continue
        out.append({
            'model': "{}.station".format(basename),
            'pk': pk,
            'fields': {
                'station_id': station_id
            }
        })
        out.append({
            'model': "{}.location".format(basename),
            'pk': pk,
            'fields': {
                'name': "{}".format(station_name)
            }
        })
        station_id_pks[station_id] = pk
        station_name_pks[station_name] = pk
    return out


def gen_transport_fixtures(basename):
    global station_id_pks
    query = '''
        SELECT from_id,
             to_id,
             mins,
             cost,
             transfers
        FROM routes;
    '''
    c.execute(query)
    results = c.fetchall()
    out = []
    for index, result in enumerate(results):
        pk = index + 1
        if int(result[0]) not in station_id_pks or int(result[1]) not in station_id_pks:
            print("Error: Can't find the station for this trip!")
            print(result)
            continue

        from_station_pk = station_id_pks[int(result[0])]
        to_station_pk = station_id_pks[int(result[1])]
        duration_str = str(datetime.timedelta(minutes=int(result[2])))
        cost = int(result[3])
        transfers = int(result[4])
        # Add both directions in as the same trip (for now)
        out.append({
            'model': "{}.trainride".format(basename),
            'pk': pk,
            'fields': {
                'from_station': from_station_pk,
                'to_station': to_station_pk,
                'duration': duration_str,
                'cost': cost,
                'transfers': transfers
            }
        })
        out.append({
            'model': "{}.trainride".format(basename),
            'pk': pk,
            'fields': {
                'from_station': to_station_pk,
                'to_station': from_station_pk,
                'duration': duration_str,
                'cost': cost,
                'transfers': transfers
            }
        })
    return out


def gen_activitytype_fixtures(basename):
    global activity_type_pks
    # Can this be turned into an enumeration (would that be better)?
    categories = [
        ('food', 'Anywhere you can eat (except maid, cat, robot restaurants)'),
        ('coffee', 'Somewhere you primarily drink'),
        ('cultural', 'e.g. Temples, Shrines'),
        ('anime', 'Anything popular with anime fans'),
        ('observatory', 'e.g. Tall buildings you can see the city/scenery from'),
        ('park', 'e.g. Hibiya Park, Shinjuku Park (except theme-parks)'),
        ('shopping', 'Shopping centres'),
        ('museum', 'Any type of museum'),
        ('zoo', 'Any type of animal park'),
        ('theme-food', "E.g. maid-cafe, cat-cafe, robot-restaurant etc."),
        ('theme-park', 'e.g. fujiQ highland, universial studios'),
    ]
    out = []
    for index, category in enumerate(categories):
        pk = index + 1
        out.append({
            'model': "{}.activitytype".format(basename),
            'pk': pk,
            'fields': {
                'title': category[0],
                'description': category[1]
            }
        })
        activity_type_pks[category[0]] = pk
    return out


def gen_activities_fixtures(basename):
    global activity_type_pks, station_name_pks

    activities = load_activities(path_activities)
    out = []
    for index, activity in enumerate(activities):
        pk = index + 1
        title = activity['name']
        duration = str(datetime.timedelta(hours=float(activity['duration'])))
        cost = int(activity['cost'])

        available_from = "00:00:00"
        if activity['opens'] != "":
            available_from = "{}:00".format(activity['opens'])

        available_until = "23:59:59"
        if activity['closes'] != "":
            available_until = "{}:00".format(activity['closes'])

        activity_type = activity_type_pks[activity['category']]
        train_station = station_name_pks[activity['station']]
        out.append({
            'model': "{}.activity".format(basename),
            'pk': pk,
            'fields': {
                'title': title,
                'duration': duration,
                'cost': cost,
                'available_from': available_from,
                'available_until': available_until,
                'activity_type': activity_type,
                'train_station': train_station
            }
        })
    return out


def main():
    app_name = 'tourbuilder'
    station_fixtures = gen_station_fixtures(app_name)
    transport_fixtures = gen_transport_fixtures(app_name)
    activitytype_fixtures = gen_activitytype_fixtures(app_name)
    activities_fixtures = gen_activities_fixtures(app_name)

    out = []
    out += station_fixtures
    out += transport_fixtures
    # out += activitytype_fixtures
    # out += activities_fixtures

    write_json(path_fixtures, out)


if __name__ == "__main__":
    main()

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
path_attractions = "attractions.json"

conn = sqlite3.connect(path_transit_database)
c = conn.cursor()

attractions = load_json(path_attractions)

route_request_template = '''
  SELECT from_id,
         to_id,
         mins,
         cost,
         transfers
  FROM routes
  WHERE from_id = (
    SELECT station_id
    FROM stations
    WHERE english = "{}"
  )
  AND to_id = (
    SELECT station_id
    FROM stations
    WHERE english = "{}"
  );
'''

translation_request_template = '''
    SELECT station_id
    FROM stations
    WHERE english = "{}"
'''

def request_translation(station):
  request = translation_request_template.format(station)
  c.execute(request)
  res = c.fetchone()
  if res is not None:
    return res[0]
  else:
    return None

def request_route(from_station, to_station, first=True):
  request = route_request_template.format(from_station, to_station)
  c.execute(request)
  res = c.fetchone()
  if res is not None:
    return {
      'from_station': res[0],
      'to_station': res[1],
      'minutes': res[2],
      'yen': res[3],
      'transfers': res[4]
    }
  else:
    if first:
        return request_route(to_station, from_station, False)
    else:
        return None

combs = []

for i in range(1, len(attractions)+1):
    els = [list(x) for x in itertools.combinations(attractions, i)]
    combs.extend(els)

valid_tours = []

cost_max = 100000
tour_start = datetime.datetime(2020, 7, 4, 8, 0)
tour_end = datetime.datetime(2020, 7, 4, 17, 0)

duration_limit = tour_end - tour_start

def tour_is_acceptable(meta):
    if meta['total_cost'] > cost_max:
        return False
    if meta['duration'] > duration_limit:
        return False
    return True


for combo in combs:
    tours = itertools.permutations(combo)
    valid_tours_temp = []
    for tour in tours:
        meta = {
            'total_cost': 0,
            'duration': datetime.timedelta(),
            'tags': []
        }
        for attraction in tour:
            meta['total_cost'] += attraction[3]
            meta['duration'] += datetime.timedelta(hours=attraction[2])
            meta['tags'].append(attraction[4])

        if tour_is_acceptable(meta):
            train_rides = []
            if len(tour) > 1:
                stations = [x[1] for x in tour]
                for index in range(len(stations) - 1):
                    from_station = tour[index][1]
                    to_station = tour[index+1][1]
                    route = request_route(from_station, to_station)
                    train_rides.append(route)
                for train_ride in train_rides:
                    meta['total_cost'] += train_ride['yen']
                    meta['duration'] += datetime.timedelta(minutes=train_ride['minutes'])

            if tour_is_acceptable(meta):
                valid_tours_temp.append({
                    'meta': meta,
                    'train_rides': train_rides,
                    'attractions': tour
                })

    # Filter sub_optimal combinations
    times = [x['meta']['duration'] for x in valid_tours_temp]
    print(valid_tours_temp)
    if len(times) > 0:
        min_time = min(times)
        for valid_tour in valid_tours_temp:
            if valid_tour['meta']['duration'] == min_time:
                valid_tours.append(valid_tour)


for i, tour in enumerate(valid_tours):
    print("Tour {}".format(i))
    print(" - Total cost:     {} Yen".format(tour['meta']['total_cost']))
    print(" - Total duration: {}".format(tour['meta']['duration']))
    print(" - Itineary:")
    temp_time = tour_start
    num_attractions = len(tour['attractions'])
    verb = "Meet"
    for index in range(num_attractions):
        attraction = tour['attractions'][index]
        print("    - {}: {} at {} Station".format(temp_time.strftime("%H:%M"), verb, attraction[1]))
        verb = "Arrive"
        print("             {} ({} hours, {} Yen)".format(attraction[0], attraction[2], attraction[3]))
        temp_time += datetime.timedelta(hours=attraction[2])
        if num_attractions > 1 and index < len(tour['train_rides']):
            route = tour['train_rides'][index]
            print("    - {}: Catch train from {} Station to {} Station ({} mins, {} Yen)".format(temp_time.strftime("%H:%M"), tour['attractions'][index][1], tour['attractions'][index+1][1], route['minutes'], route['yen']))
            temp_time += datetime.timedelta(minutes=route['minutes'])
    print("    - {}: Finish tour at {} Station".format(temp_time.strftime("%H:%M"), attraction[1]))
    print("")

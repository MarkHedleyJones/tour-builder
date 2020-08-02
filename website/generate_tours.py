#!/usr/bin/python3

import os
import django
import copy
import datetime
import pytz

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
django.setup()

from tourbuilder.models import Activity, TrainRide, Location, Station, Tour

tzone = pytz.timezone('Asia/Tokyo')
day_start = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=tzone)
day_end = datetime.datetime(1970, 1, 1, 23, 59, 59, tzinfo=tzone)

activities = list(Activity.objects.all())


class TourProto(object):

    def __init__(self):
        self.cost = 0
        self.duration = datetime.timedelta()
        self.available_from = day_start
        self.available_until = day_end
        self.activities = []
        self.train_rides = []

    def calculate_availability(self, available_from, available_until, duration):
        available_from = max(self.available_from,
                                  available_from - self.duration)
        available_until = min(self.available_until,
                                   available_until - (self.duration + duration))
        return available_from, available_until

    def can_probably_add_activity(self, activity):
        # available_from, available_until = self.calculate_availability()
        return True

    def add_activity(self, activity):
        activity_total_cost = activity.cost
        activity_total_duration = activity.duration
        train_ride = None
        if len(self.activities) > 0:
            last_activity = self.activities[-1]
            if last_activity.train_station_id != activity.train_station_id:
                out = TrainRide.objects.all()
                out = out.filter(from_station_id=last_activity.train_station.id)
                out = out.filter(to_station_id=activity.train_station.id)
                if len(out) == 1:
                    train_ride = out[0]
                else:
                    print("Error fetching train ride {} to {}".format(last_activity.train_station.name,
                                                                      activity.train_station.name))
                activity_total_cost += train_ride.cost
                activity_total_duration += train_ride.duration

        available_from, available_until = self.calculate_availability(activity.available_from,
                                                                      activity.available_until,
                                                                      activity_total_duration)

        if available_from <= available_until:
            self.cost += activity_total_cost
            self.available_from = available_from
            self.available_until = available_until
            self.duration += activity_total_duration
            self.activities.append(activity)
            if train_ride is not None:
                self.train_rides.append(train_ride)
            return True
        else:
            return False


def build_tours(tours, tour, activities, depth=0):
    depth += 1
    print(len(tours))
    if len(tours) > 100:
        return
    activities = [x for x in activities if tour.can_probably_add_activity(x)]

    for index in range(len(activities)):
        tour_tmp = copy.deepcopy(tour)
        activities_tmp = copy.copy(activities)
        next_activity = activities_tmp[index]
        activities_tmp.remove(next_activity)
        if tour_tmp.add_activity(next_activity):
            tours.append(tour_tmp)
            build_tours(tours, tour_tmp, activities_tmp, depth)


tours = []
for index in range(len(activities)):
    tour_tmp = TourProto()
    activities_tmp = copy.copy(activities)
    if tour_tmp.add_activity(activities_tmp.pop(index)):
        build_tours(tours, tour_tmp, activities_tmp)

for proto_tour in tours:
    tour = Tour()
    tour.cost = proto_tour.cost
    tour.duration = proto_tour.duration
    tour.available_from = proto_tour.available_from
    tour.available_until = proto_tour.available_until
    tour.save()
    for activity in proto_tour.activities:
        tour.activities.add(activity)
    for train_ride in proto_tour.train_rides:
        tour.train_rides.add(train_ride)
    tour.save()

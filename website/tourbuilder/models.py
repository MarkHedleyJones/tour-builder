from django.db import models
from django.utils import timezone
import datetime
import pytz


tzone = pytz.timezone('Asia/Tokyo')
day_start = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=tzone)
day_end = datetime.datetime(1970, 1, 1, 23, 59, 59, tzinfo=tzone)


class Location(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Category(models.Model):
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=200)

    def __str__(self):
        return self.title


class Station(Location):
    station_id = models.IntegerField(unique=True)


class Activity(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    train_station = models.ForeignKey(Station, on_delete=models.CASCADE)
    available_from = models.DateTimeField(default=day_start)
    available_until = models.DateTimeField(default=day_end)
    cost = models.PositiveIntegerField(default=0)
    duration = models.DurationField(default=datetime.timedelta)
    title = models.CharField(max_length=50)

    def __str__(self):
        return self.title


class TrainRide(models.Model):
    from_station = models.ForeignKey(Station,
                                     related_name='from_station',
                                     on_delete=models.CASCADE)
    to_station = models.ForeignKey(Station,
                                   related_name='to_station',
                                   on_delete=models.CASCADE)
    duration = models.DurationField(default=datetime.timedelta)
    cost = models.PositiveIntegerField(default=0)
    transfers = models.PositiveIntegerField(default=0)

    def __str__(self):
        return "{} to {}".format(self.from_station.name, self.to_station.name)


class Tour(models.Model):
    activities = models.ManyToManyField(Activity)
    available_from = models.DateTimeField(default=day_start)
    available_until = models.DateTimeField(default=day_end)
    cost = models.PositiveIntegerField(default=0)
    duration = models.DurationField(default=datetime.timedelta)
    train_rides = models.ManyToManyField(TrainRide)

    def __str__(self):
        return "{} - {}".format(self.duration, ", ".join(map(str, self.activities.all())))

from django.db import models

# Create your models here.


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
    available_from = models.TimeField()
    available_until = models.TimeField()
    cost = models.PositiveIntegerField()
    duration = models.DurationField()
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
    duration = models.DurationField()
    cost = models.PositiveIntegerField()
    transfers = models.PositiveIntegerField()

    def __str__(self):
        return "{} to {}".format(self.from_station.name, self.to_station.name)


class Tour(models.Model):
    cost = models.PositiveIntegerField()
    duration = models.DurationField()
    available_from = models.TimeField()
    available_until = models.TimeField()
    activities = models.ManyToManyField(Activity)
    trainRides = models.ManyToManyField(TrainRide)

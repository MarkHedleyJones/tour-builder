from django.contrib import admin

# Register your models here.
from .models import Location, ActivityType, TrainStation, Activity, TrainRide

admin.site.register(Location)
admin.site.register(ActivityType)
admin.site.register(TrainStation)
admin.site.register(Activity)
admin.site.register(TrainRide)

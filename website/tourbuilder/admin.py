from django.contrib import admin

# Register your models here.
from .models import Location, Category, Station, Activity, TrainRide

admin.site.register(Location)
admin.site.register(Category)
admin.site.register(Station)
admin.site.register(Activity)
admin.site.register(TrainRide)

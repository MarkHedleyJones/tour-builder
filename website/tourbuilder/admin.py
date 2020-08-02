from django.contrib import admin

# Register your models here.
from .models import Location, Category, Station, Activity, TrainRide, Tour

class TourA(admin.ModelAdmin):
    # when using an autocomplete to find a child, search in the field 'name'
    raw_id_fields = ('train_rides',)


admin.site.register(Location)
admin.site.register(Category)
admin.site.register(Station)
admin.site.register(Activity)
admin.site.register(TrainRide)
admin.site.register(Tour, TourA)

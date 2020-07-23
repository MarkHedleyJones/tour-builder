import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
django.setup()

from tourbuilder.models import Activity, TrainRide, Location, Station

activities = Activity.objects.all()

for activity in activities:
    print(activity)

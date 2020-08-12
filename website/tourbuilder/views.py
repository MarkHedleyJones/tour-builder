from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
# from django.template import loader

from .models import Activity, Location, Station, Tour


def index(request):
    tours = Tour.objects.all()
    return render(request, 'tourbuilder/index.html', {'tours': tours})


def tour(request, tour_id):
    tour = get_object_or_404(Tour, pk=tour_id)
    return render(request, 'tourbuilder/tour.html', {'tour': tour})


def activity(request, activity_id):
    activity = get_object_or_404(Activity, pk=activity_id)
    return render(request, 'tourbuilder/activity.html', {'activity': activity})


def location(request, location_id):
    location = get_object_or_404(Location, pk=location_id)
    return render(request, 'tourbuilder/location.html', {'location': location})


def station(request, station_id):
    station = get_object_or_404(Location, pk=station_id)
    return render(request, 'tourbuilder/station.html', {'station': station})

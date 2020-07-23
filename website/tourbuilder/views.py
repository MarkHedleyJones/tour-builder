# from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader

from .models import Activity, Location, Station


def index(request):
    return HttpResponse("Hello, world. You're at the polls index.")


def activity(request, activity_id):
    return HttpResponse("You're looking at activity {}".format(activity_id))


def location(request, location_id):
    return HttpResponse("You're looking at location {}".format(location_id))


def station(request, station_id):
    return HttpResponse("You're looking at station {}".format(station_id))

from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('activity/<int:activity_id>/', views.activity),
    path('location/<int:location_id>/', views.location),
    path('station/<int:station_id>/', views.station),
]

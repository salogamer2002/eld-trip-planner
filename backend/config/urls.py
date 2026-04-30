"""URL configuration for ELD Trip Planner."""
from django.urls import path, include

urlpatterns = [
    path('api/', include('trips.urls')),
]

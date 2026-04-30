"""API views for trip planning."""
import json
import subprocess
from datetime import datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .hos_engine import calculate_trip

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


def _curl_get(url):
    """Use system curl to bypass Python's broken SSL."""
    try:
        result = subprocess.run(
            ['curl', '-s', '-S', '--max-time', '15', url],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"Curl error: {e}")
    return None


def geocode_location(query):
    """Geocode a location string to coordinates using Nominatim."""
    import urllib.parse
    encoded = urllib.parse.quote(query)
    url = f"{NOMINATIM_URL}?q={encoded}&format=json&limit=1&countrycodes=us"
    data = _curl_get(url)
    if data and len(data) > 0:
        return {
            'lat': float(data[0]['lat']),
            'lon': float(data[0]['lon']),
            'display_name': data[0].get('display_name', query),
        }
    return None


def get_route(coords_list):
    """Get route from OSRM between multiple coordinate pairs."""
    coords_str = ";".join(f"{c['lon']},{c['lat']}" for c in coords_list)
    url = f"{OSRM_URL}/{coords_str}?overview=full&geometries=geojson&steps=true&alternatives=false"
    data = _curl_get(url)
    if data and data.get('code') == 'Ok' and data.get('routes'):
        route = data['routes'][0]
        legs = []
        for i, leg in enumerate(route['legs']):
            leg_coords = []
            for step in leg['steps']:
                leg_coords.extend(step['geometry']['coordinates'])
            legs.append({
                'distance': leg['distance'] / 1609.34,
                'duration': leg['duration'] / 3600,
                'start_location': [coords_list[i]['lon'], coords_list[i]['lat']],
                'end_location': [coords_list[i+1]['lon'], coords_list[i+1]['lat']],
                'geometry': leg_coords,
            })
        return {
            'legs': legs,
            'geometry': route['geometry'],
            'total_distance': route['distance'] / 1609.34,
            'total_duration': route['duration'] / 3600,
        }
    print(f"OSRM response: {data}")
    return None


@api_view(['POST'])
def plan_trip(request):
    """Plan a trip with HOS-compliant stops and generate ELD logs."""
    current_location = request.data.get('current_location', '')
    pickup_location = request.data.get('pickup_location', '')
    dropoff_location = request.data.get('dropoff_location', '')
    cycle_hours_used = float(request.data.get('cycle_hours_used', 0))

    if not all([current_location, pickup_location, dropoff_location]):
        return Response(
            {'error': 'All location fields are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if cycle_hours_used < 0 or cycle_hours_used > 70:
        return Response(
            {'error': 'Cycle hours must be between 0 and 70.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Geocode locations
    current_geo = geocode_location(current_location)
    pickup_geo = geocode_location(pickup_location)
    dropoff_geo = geocode_location(dropoff_location)

    if not current_geo:
        return Response({'error': f'Could not find location: {current_location}'}, status=400)
    if not pickup_geo:
        return Response({'error': f'Could not find location: {pickup_location}'}, status=400)
    if not dropoff_geo:
        return Response({'error': f'Could not find location: {dropoff_location}'}, status=400)

    # Get route
    route = get_route([current_geo, pickup_geo, dropoff_geo])
    if not route:
        return Response({'error': 'Could not calculate route. Please try again.'}, status=400)

    route['start_name'] = current_geo['display_name'].split(',')[0]
    route['pickup_name'] = pickup_geo['display_name'].split(',')[0]
    route['dropoff_name'] = dropoff_geo['display_name'].split(',')[0]

    # Calculate HOS-compliant trip
    trip_result = calculate_trip(route, cycle_hours_used)

    return Response({
        'route': {
            'geometry': route['geometry'],
            'total_distance': round(route['total_distance'], 1),
            'total_duration': round(route['total_duration'], 1),
        },
        'locations': {
            'current': {'name': current_geo['display_name'], 'coords': [current_geo['lat'], current_geo['lon']]},
            'pickup': {'name': pickup_geo['display_name'], 'coords': [pickup_geo['lat'], pickup_geo['lon']]},
            'dropoff': {'name': dropoff_geo['display_name'], 'coords': [dropoff_geo['lat'], dropoff_geo['lon']]},
        },
        'stops': trip_result['stops'],
        'daily_logs': trip_result['daily_logs'],
        'summary': trip_result['summary'],
    })

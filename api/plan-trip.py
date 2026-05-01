"""Vercel Serverless Function for trip planning."""
import json
import math
import os
import sys
import subprocess
import urllib.parse
import urllib.request
import time
from http.server import BaseHTTPRequestHandler

# Add api directory to path for hos_engine import
sys.path.insert(0, os.path.dirname(__file__))
from hos_engine import calculate_trip


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


def _fetch_json(url, retries=2):
    """Fetch JSON from a URL using urllib (no external deps needed)."""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'ELDTripPlanner/1.0'
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"Fetch attempt {attempt+1} error: {e}")
        if attempt < retries:
            time.sleep(0.5)
    return None


def geocode_location(query):
    """Geocode a location string to coordinates using Nominatim."""
    encoded = urllib.parse.quote(query)
    url = f"{NOMINATIM_URL}?q={encoded}&format=json&limit=1&countrycodes=us"
    data = _fetch_json(url)
    if data and len(data) > 0:
        return {
            'lat': float(data[0]['lat']),
            'lon': float(data[0]['lon']),
            'display_name': data[0].get('display_name', query),
        }
    return None


def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))


def generate_intermediate_points(start, end, num_points=50):
    points = []
    for i in range(num_points + 1):
        t = i / num_points
        lat = start['lat'] + t * (end['lat'] - start['lat'])
        lon = start['lon'] + t * (end['lon'] - start['lon'])
        points.append([lon, lat])
    return points


def get_route(coords_list):
    """Get route from OSRM, with fallback to estimation."""
    coords_str = ";".join(f"{c['lon']},{c['lat']}" for c in coords_list)
    url = f"{OSRM_URL}/{coords_str}?overview=full&geometries=geojson&steps=true&alternatives=false"
    data = _fetch_json(url)

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

    # Fallback estimation
    print("OSRM unavailable, using fallback")
    ROAD_FACTOR = 1.3
    AVG_SPEED = 55
    legs = []
    all_coords = []
    total_dist = 0
    total_dur = 0

    for i in range(len(coords_list) - 1):
        start = coords_list[i]
        end = coords_list[i + 1]
        straight_dist = haversine_miles(start['lat'], start['lon'], end['lat'], end['lon'])
        road_dist = straight_dist * ROAD_FACTOR
        road_dur = road_dist / AVG_SPEED
        leg_coords = generate_intermediate_points(start, end, num_points=100)
        all_coords.extend(leg_coords)
        legs.append({
            'distance': road_dist,
            'duration': road_dur,
            'start_location': [start['lon'], start['lat']],
            'end_location': [end['lon'], end['lat']],
            'geometry': leg_coords,
        })
        total_dist += road_dist
        total_dur += road_dur

    return {
        'legs': legs,
        'geometry': {'type': 'LineString', 'coordinates': all_coords},
        'total_distance': total_dist,
        'total_duration': total_dur,
    }


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            current_location = data.get('current_location', '')
            pickup_location = data.get('pickup_location', '')
            dropoff_location = data.get('dropoff_location', '')
            cycle_hours_used = float(data.get('cycle_hours_used', 0))

            if not all([current_location, pickup_location, dropoff_location]):
                return self._json_response(400, {'error': 'All location fields are required.'})

            if cycle_hours_used < 0 or cycle_hours_used > 70:
                return self._json_response(400, {'error': 'Cycle hours must be between 0 and 70.'})

            # Geocode
            current_geo = geocode_location(current_location)
            pickup_geo = geocode_location(pickup_location)
            dropoff_geo = geocode_location(dropoff_location)

            if not current_geo:
                return self._json_response(400, {'error': f'Could not find: {current_location}'})
            if not pickup_geo:
                return self._json_response(400, {'error': f'Could not find: {pickup_location}'})
            if not dropoff_geo:
                return self._json_response(400, {'error': f'Could not find: {dropoff_location}'})

            # Route
            route = get_route([current_geo, pickup_geo, dropoff_geo])
            if not route:
                return self._json_response(400, {'error': 'Could not calculate route.'})

            route['start_name'] = current_geo['display_name'].split(',')[0]
            route['pickup_name'] = pickup_geo['display_name'].split(',')[0]
            route['dropoff_name'] = dropoff_geo['display_name'].split(',')[0]

            # HOS calculation
            trip_result = calculate_trip(route, cycle_hours_used)

            return self._json_response(200, {
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

        except Exception as e:
            return self._json_response(500, {'error': str(e)})

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _json_response(self, status_code, data):
        self.send_response(status_code)
        self._cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

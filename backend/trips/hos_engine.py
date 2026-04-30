"""
Hours of Service (HOS) Calculation Engine
FMCSA Property-Carrying CMV Driver Rules:
- 11-hour driving limit
- 14-hour driving window
- 30-minute break after 8 hours cumulative driving
- 70-hour/8-day cycle limit
- 10 consecutive hours off-duty between shifts
- Fueling every 1000 miles
- 1 hour pickup/dropoff
"""
import math
from datetime import datetime, timedelta


# HOS Constants
MAX_DRIVING_HOURS = 11
MAX_DUTY_WINDOW = 14
BREAK_AFTER_HOURS = 8
BREAK_DURATION = 0.5  # 30 minutes
OFF_DUTY_REQUIRED = 10
MAX_CYCLE_HOURS = 70
FUEL_INTERVAL_MILES = 1000
FUEL_STOP_DURATION = 0.5
PICKUP_DURATION = 1.0
DROPOFF_DURATION = 1.0
AVG_SPEED_MPH = 55
PRE_TRIP_DURATION = 0.25  # 15 min
POST_TRIP_DURATION = 0.25


def interpolate_point(coords, fraction):
    """Get a point along a route at a given fraction (0-1) of total distance."""
    if not coords or len(coords) < 2:
        return coords[0] if coords else [0, 0]
    if fraction <= 0:
        return coords[0]
    if fraction >= 1:
        return coords[-1]

    total = 0
    segments = []
    for i in range(len(coords) - 1):
        dx = coords[i+1][0] - coords[i][0]
        dy = coords[i+1][1] - coords[i][1]
        d = math.sqrt(dx*dx + dy*dy)
        segments.append(d)
        total += d

    target = fraction * total
    accum = 0
    for i, seg_len in enumerate(segments):
        if accum + seg_len >= target and seg_len > 0:
            t = (target - accum) / seg_len
            lng = coords[i][0] + t * (coords[i+1][0] - coords[i][0])
            lat = coords[i][1] + t * (coords[i+1][1] - coords[i][1])
            return [lng, lat]
        accum += seg_len
    return coords[-1]


def calculate_trip(route_data, cycle_hours_used, start_time=None):
    """
    Main HOS trip calculation.

    route_data: dict with 'legs' containing route segments from OSRM
    cycle_hours_used: float hours already used in 70hr/8day cycle
    start_time: datetime for trip start (defaults to now)

    Returns dict with stops, daily_logs, and trip_summary.
    """
    if start_time is None:
        start_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        if datetime.now().hour >= 8:
            start_time += timedelta(days=1)

    legs = route_data.get('legs', [])
    all_stops = []
    daily_logs = []

    current_time = start_time
    shift_driving = 0.0
    shift_on_duty = 0.0
    driving_since_break = 0.0
    cycle_hours = float(cycle_hours_used)
    miles_since_fuel = 0.0
    total_miles_driven = 0.0

    leg_labels = ['current_to_pickup', 'pickup_to_dropoff']

    # Pre-trip inspection
    all_stops.append({
        'type': 'start',
        'label': 'Trip Start & Pre-Trip Inspection',
        'location': legs[0]['start_location'] if legs else [0, 0],
        'location_name': route_data.get('start_name', 'Start'),
        'time': current_time.isoformat(),
        'duration': PRE_TRIP_DURATION,
        'status': 'on_duty',
    })
    shift_on_duty += PRE_TRIP_DURATION
    cycle_hours += PRE_TRIP_DURATION
    current_time += timedelta(hours=PRE_TRIP_DURATION)

    for leg_idx, leg in enumerate(legs):
        leg_distance = leg['distance']  # miles
        leg_coords = leg.get('geometry', [])
        leg_name = leg_labels[leg_idx] if leg_idx < len(leg_labels) else f'leg_{leg_idx}'

        # Pickup/Dropoff stop at start of second leg and end of last leg
        if leg_idx == 1:
            all_stops.append({
                'type': 'pickup',
                'label': 'Pickup (Loading)',
                'location': leg['start_location'],
                'location_name': route_data.get('pickup_name', 'Pickup'),
                'time': current_time.isoformat(),
                'duration': PICKUP_DURATION,
                'status': 'on_duty',
            })
            shift_on_duty += PICKUP_DURATION
            cycle_hours += PICKUP_DURATION
            current_time += timedelta(hours=PICKUP_DURATION)

        miles_remaining = leg_distance
        miles_covered_in_leg = 0.0

        while miles_remaining > 0.01:
            # Calculate how far we can drive before hitting any limit
            drive_limit_hrs = MAX_DRIVING_HOURS - shift_driving
            window_limit_hrs = MAX_DUTY_WINDOW - shift_on_duty
            break_limit_hrs = BREAK_AFTER_HOURS - driving_since_break
            cycle_limit_hrs = MAX_CYCLE_HOURS - cycle_hours
            fuel_limit_miles = FUEL_INTERVAL_MILES - miles_since_fuel
            fuel_limit_hrs = fuel_limit_miles / AVG_SPEED_MPH

            max_drive_hrs = min(
                drive_limit_hrs,
                window_limit_hrs,
                break_limit_hrs,
                cycle_limit_hrs,
                fuel_limit_hrs,
            )

            if max_drive_hrs <= 0.01:
                # Determine which limit was hit
                if cycle_limit_hrs <= 0.01:
                    # 34-hour restart needed
                    restart_hrs = 34.0
                    all_stops.append(_make_stop(
                        'restart', '34-Hour Restart (Mandatory)',
                        leg_coords, miles_covered_in_leg, leg_distance,
                        current_time, restart_hrs, 'off_duty'
                    ))
                    current_time += timedelta(hours=restart_hrs)
                    shift_driving = 0
                    shift_on_duty = 0
                    driving_since_break = 0
                    cycle_hours = 0
                elif drive_limit_hrs <= 0.01 or window_limit_hrs <= 0.01:
                    # 10-hour off-duty required
                    all_stops.append(_make_stop(
                        'rest', '10-Hour Off-Duty Rest',
                        leg_coords, miles_covered_in_leg, leg_distance,
                        current_time, OFF_DUTY_REQUIRED, 'sleeper'
                    ))
                    current_time += timedelta(hours=OFF_DUTY_REQUIRED)
                    shift_driving = 0
                    shift_on_duty = 0
                    driving_since_break = 0
                    # Pre-trip after rest
                    shift_on_duty += PRE_TRIP_DURATION
                    cycle_hours += PRE_TRIP_DURATION
                    current_time += timedelta(hours=PRE_TRIP_DURATION)
                elif break_limit_hrs <= 0.01:
                    # 30-minute break
                    all_stops.append(_make_stop(
                        'break', '30-Minute Rest Break',
                        leg_coords, miles_covered_in_leg, leg_distance,
                        current_time, BREAK_DURATION, 'off_duty'
                    ))
                    shift_on_duty += BREAK_DURATION
                    cycle_hours += BREAK_DURATION
                    current_time += timedelta(hours=BREAK_DURATION)
                    driving_since_break = 0
                else:
                    # Fuel stop
                    all_stops.append(_make_stop(
                        'fuel', 'Fuel Stop',
                        leg_coords, miles_covered_in_leg, leg_distance,
                        current_time, FUEL_STOP_DURATION, 'on_duty'
                    ))
                    shift_on_duty += FUEL_STOP_DURATION
                    cycle_hours += FUEL_STOP_DURATION
                    current_time += timedelta(hours=FUEL_STOP_DURATION)
                    miles_since_fuel = 0
                continue

            max_drive_miles = max_drive_hrs * AVG_SPEED_MPH
            drive_miles = min(max_drive_miles, miles_remaining)
            drive_hrs = drive_miles / AVG_SPEED_MPH

            # Check if fuel stop needed during this segment
            if miles_since_fuel + drive_miles >= FUEL_INTERVAL_MILES:
                miles_to_fuel = FUEL_INTERVAL_MILES - miles_since_fuel
                hrs_to_fuel = miles_to_fuel / AVG_SPEED_MPH

                shift_driving += hrs_to_fuel
                shift_on_duty += hrs_to_fuel
                driving_since_break += hrs_to_fuel
                cycle_hours += hrs_to_fuel
                miles_remaining -= miles_to_fuel
                miles_covered_in_leg += miles_to_fuel
                total_miles_driven += miles_to_fuel
                current_time += timedelta(hours=hrs_to_fuel)
                miles_since_fuel = 0

                all_stops.append(_make_stop(
                    'fuel', 'Fuel Stop',
                    leg_coords, miles_covered_in_leg, leg_distance,
                    current_time, FUEL_STOP_DURATION, 'on_duty'
                ))
                shift_on_duty += FUEL_STOP_DURATION
                cycle_hours += FUEL_STOP_DURATION
                current_time += timedelta(hours=FUEL_STOP_DURATION)
                continue

            # Drive the segment
            shift_driving += drive_hrs
            shift_on_duty += drive_hrs
            driving_since_break += drive_hrs
            cycle_hours += drive_hrs
            miles_remaining -= drive_miles
            miles_covered_in_leg += drive_miles
            total_miles_driven += drive_miles
            miles_since_fuel += drive_miles
            current_time += timedelta(hours=drive_hrs)

            # After driving, check if we need a mandatory stop
            if miles_remaining > 0.01:
                if driving_since_break >= BREAK_AFTER_HOURS - 0.01:
                    all_stops.append(_make_stop(
                        'break', '30-Minute Rest Break',
                        leg_coords, miles_covered_in_leg, leg_distance,
                        current_time, BREAK_DURATION, 'off_duty'
                    ))
                    shift_on_duty += BREAK_DURATION
                    cycle_hours += BREAK_DURATION
                    current_time += timedelta(hours=BREAK_DURATION)
                    driving_since_break = 0

                if shift_driving >= MAX_DRIVING_HOURS - 0.01 or shift_on_duty >= MAX_DUTY_WINDOW - 0.01:
                    all_stops.append(_make_stop(
                        'rest', '10-Hour Off-Duty Rest',
                        leg_coords, miles_covered_in_leg, leg_distance,
                        current_time, OFF_DUTY_REQUIRED, 'sleeper'
                    ))
                    current_time += timedelta(hours=OFF_DUTY_REQUIRED)
                    shift_driving = 0
                    shift_on_duty = 0
                    driving_since_break = 0
                    shift_on_duty += PRE_TRIP_DURATION
                    cycle_hours += PRE_TRIP_DURATION
                    current_time += timedelta(hours=PRE_TRIP_DURATION)

                if cycle_hours >= MAX_CYCLE_HOURS - 0.01:
                    restart_hrs = 34.0
                    all_stops.append(_make_stop(
                        'restart', '34-Hour Restart',
                        leg_coords, miles_covered_in_leg, leg_distance,
                        current_time, restart_hrs, 'off_duty'
                    ))
                    current_time += timedelta(hours=restart_hrs)
                    shift_driving = 0
                    shift_on_duty = 0
                    driving_since_break = 0
                    cycle_hours = 0

    # Dropoff
    dropoff_loc = legs[-1]['end_location'] if legs else [0, 0]
    all_stops.append({
        'type': 'dropoff',
        'label': 'Dropoff (Unloading)',
        'location': dropoff_loc,
        'location_name': route_data.get('dropoff_name', 'Dropoff'),
        'time': current_time.isoformat(),
        'duration': DROPOFF_DURATION,
        'status': 'on_duty',
    })
    shift_on_duty += DROPOFF_DURATION
    cycle_hours += DROPOFF_DURATION
    current_time += timedelta(hours=DROPOFF_DURATION)

    # Post-trip
    all_stops.append({
        'type': 'end',
        'label': 'Post-Trip Inspection & End',
        'location': dropoff_loc,
        'location_name': route_data.get('dropoff_name', 'Dropoff'),
        'time': current_time.isoformat(),
        'duration': POST_TRIP_DURATION,
        'status': 'on_duty',
    })
    shift_on_duty += POST_TRIP_DURATION
    cycle_hours += POST_TRIP_DURATION
    current_time += timedelta(hours=POST_TRIP_DURATION)

    # Generate daily logs from stops
    daily_logs = _generate_daily_logs(all_stops, start_time, current_time, route_data)

    total_distance = sum(l['distance'] for l in legs)
    return {
        'stops': all_stops,
        'daily_logs': daily_logs,
        'summary': {
            'total_distance_miles': round(total_distance, 1),
            'total_driving_hours': round(total_miles_driven / AVG_SPEED_MPH, 1),
            'trip_start': start_time.isoformat(),
            'trip_end': current_time.isoformat(),
            'total_days': math.ceil((current_time - start_time).total_seconds() / 86400),
            'num_fuel_stops': sum(1 for s in all_stops if s['type'] == 'fuel'),
            'num_rest_stops': sum(1 for s in all_stops if s['type'] == 'rest'),
            'num_breaks': sum(1 for s in all_stops if s['type'] == 'break'),
        }
    }


def _make_stop(stop_type, label, coords, miles_covered, total_miles, time, duration, status):
    """Helper to create a stop dict with interpolated location."""
    fraction = miles_covered / total_miles if total_miles > 0 else 0
    location = interpolate_point(coords, fraction) if coords else [0, 0]
    return {
        'type': stop_type,
        'label': label,
        'location': location,
        'location_name': f'Mile {int(miles_covered)}',
        'time': time.isoformat(),
        'duration': duration,
        'status': status,
    }


def _generate_daily_logs(stops, trip_start, trip_end, route_data):
    """Generate FMCSA-format daily log entries from trip stops."""
    # Build a timeline of status changes
    events = []
    for stop in stops:
        stop_time = datetime.fromisoformat(stop['time'])
        events.append({
            'time': stop_time,
            'type': stop['type'],
            'status': stop['status'],
            'duration': stop.get('duration', 0),
            'label': stop['label'],
            'location_name': stop.get('location_name', ''),
        })

    # Sort events by time
    events.sort(key=lambda e: e['time'])

    # Build a continuous timeline with driving segments between stops
    timeline = []
    for i, event in enumerate(events):
        # Add the stop event itself
        timeline.append({
            'start': event['time'],
            'end': event['time'] + timedelta(hours=event['duration']),
            'status': event['status'],
            'label': event['label'],
            'location': event['location_name'],
        })

        # If there's a next event, add driving time between this event's end and next event's start
        if i < len(events) - 1:
            drive_start = event['time'] + timedelta(hours=event['duration'])
            drive_end = events[i + 1]['time']
            if (drive_end - drive_start).total_seconds() > 60:
                timeline.append({
                    'start': drive_start,
                    'end': drive_end,
                    'status': 'driving',
                    'label': 'Driving',
                    'location': '',
                })

    # Split timeline into days
    if not timeline:
        return []

    first_day = trip_start.date()
    last_day = trip_end.date()
    num_days = (last_day - first_day).days + 1

    daily_logs = []
    for day_offset in range(num_days):
        day_date = first_day + timedelta(days=day_offset)
        day_start = datetime.combine(day_date, datetime.min.time())
        day_end = day_start + timedelta(hours=24)

        day_entries = []
        day_remarks = []
        totals = {'off_duty': 0, 'sleeper': 0, 'driving': 0, 'on_duty': 0}
        day_miles = 0

        for seg in timeline:
            seg_start = max(seg['start'], day_start)
            seg_end = min(seg['end'], day_end)
            if seg_start >= seg_end:
                continue

            hours = (seg_end - seg_start).total_seconds() / 3600
            start_hour = (seg_start - day_start).total_seconds() / 3600
            end_hour = (seg_end - day_start).total_seconds() / 3600

            status = seg['status']
            if status == 'driving':
                totals['driving'] += hours
                day_miles += hours * AVG_SPEED_MPH
            elif status == 'sleeper':
                totals['sleeper'] += hours
            elif status == 'on_duty':
                totals['on_duty'] += hours
            else:
                totals['off_duty'] += hours

            day_entries.append({
                'start_hour': round(start_hour, 2),
                'end_hour': round(end_hour, 2),
                'status': status,
                'label': seg['label'],
            })

            if seg['location'] and seg['label'] != 'Driving':
                day_remarks.append({
                    'time': round(start_hour, 2),
                    'location': seg['location'],
                    'activity': seg['label'],
                })

        # Fill remaining time as off-duty
        accounted = sum(totals.values())
        if accounted < 24:
            totals['off_duty'] += (24 - accounted)

        # Ensure entries cover full 24 hours by adding off-duty gaps
        day_entries = _fill_gaps(day_entries)

        daily_logs.append({
            'date': day_date.isoformat(),
            'day_number': day_offset + 1,
            'entries': day_entries,
            'remarks': day_remarks,
            'totals': {k: round(v, 2) for k, v in totals.items()},
            'total_miles': round(day_miles, 1),
            'from_location': route_data.get('start_name', ''),
            'to_location': route_data.get('dropoff_name', ''),
        })

    return daily_logs


def _fill_gaps(entries):
    """Fill gaps in the timeline with off-duty entries."""
    if not entries:
        return [{'start_hour': 0, 'end_hour': 24, 'status': 'off_duty', 'label': 'Off Duty'}]

    filled = []
    entries.sort(key=lambda e: e['start_hour'])

    if entries[0]['start_hour'] > 0.01:
        filled.append({
            'start_hour': 0,
            'end_hour': entries[0]['start_hour'],
            'status': 'off_duty',
            'label': 'Off Duty',
        })

    for i, entry in enumerate(entries):
        filled.append(entry)
        if i < len(entries) - 1:
            gap_start = entry['end_hour']
            gap_end = entries[i + 1]['start_hour']
            if gap_end - gap_start > 0.01:
                filled.append({
                    'start_hour': gap_start,
                    'end_hour': gap_end,
                    'status': 'off_duty',
                    'label': 'Off Duty',
                })

    last = entries[-1]
    if last['end_hour'] < 23.99:
        filled.append({
            'start_hour': last['end_hour'],
            'end_hour': 24,
            'status': 'off_duty',
            'label': 'Off Duty',
        })

    return filled

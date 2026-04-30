# 🚛 TruckLog Pro — ELD Trip Planner

A full-stack application that generates **HOS-compliant routes** and **FMCSA-format ELD daily log sheets** for interstate truck drivers (property carriers, 70hr/8-day cycle).

## 🎯 Features

- **Trip Planning** — Enter current location, pickup, dropoff, and cycle hours used
- **Route Calculation** — Uses OSRM for accurate driving routes across the US
- **HOS Compliance Engine** — Automatically enforces all FMCSA rules:
  - 11-hour driving limit
  - 14-hour driving window
  - 30-minute break after 8 hours cumulative driving
  - 70-hour/8-day cycle limit
  - 10 consecutive hours off-duty between shifts
  - 34-hour restart when cycle limit reached
  - Fueling stops every 1,000 miles
  - 1 hour for pickup and dropoff operations
- **Interactive Map** — Dark-themed map with route visualization and stop markers
- **Daily ELD Log Sheets** — Canvas-rendered FMCSA-format driver daily logs with:
  - 24-hour grid with 15-minute increments
  - Color-coded duty status lines (Off Duty, Sleeper Berth, Driving, On Duty Not Driving)
  - Total hours per status
  - Remarks section with location annotations

## 🛠️ Tech Stack

- **Backend**: Django + Django REST Framework (Python)
- **Frontend**: React + Vite (JavaScript)
- **Map**: Leaflet + OpenStreetMap (CARTO dark tiles)
- **Routing**: OSRM (Open Source Routing Machine)
- **Geocoding**: OpenStreetMap Nominatim

## 🚀 Quick Start

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py runserver 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

## 📐 HOS Rules Implemented

| Rule | Limit | Implementation |
|------|-------|---------------|
| Driving Limit | 11 hours per shift | Enforced with mandatory 10-hour rest |
| Driving Window | 14 hours on-duty | Cannot drive after 14th hour |
| Rest Break | 30 min after 8 hrs driving | Inserted automatically along route |
| Off-Duty Rest | 10 consecutive hours | Full shift reset |
| Cycle Limit | 70 hours / 8 days | 34-hour restart when exceeded |
| Fueling | Every 1,000 miles | 30-minute fuel stops |
| Pickup/Dropoff | 1 hour each | On-duty not driving |

## 📁 Project Structure

```
eld-trip-planner/
├── backend/
│   ├── config/          # Django settings, URLs, WSGI
│   ├── trips/
│   │   ├── hos_engine.py  # Core HOS calculation engine
│   │   ├── views.py       # REST API endpoints
│   │   └── urls.py        # API routing
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TripForm.jsx       # Trip input form
│   │   │   ├── TripSummary.jsx    # Summary cards
│   │   │   ├── RouteMap.jsx       # Interactive Leaflet map
│   │   │   ├── StopsTimeline.jsx  # Chronological stops
│   │   │   └── ELDLogSheet.jsx    # Canvas-rendered ELD logs
│   │   ├── App.jsx
│   │   └── index.css    # Premium dark theme
│   └── package.json
└── README.md
```

## 🌐 Deployment

- **Frontend**: Deploy to Vercel (`cd frontend && vercel`)
- **Backend**: Deploy to Render/Railway with `gunicorn config.wsgi`

Set `VITE_API_URL` environment variable in frontend to point to your deployed backend URL.

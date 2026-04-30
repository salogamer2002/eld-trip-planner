import { useEffect, useRef } from 'react'
import L from 'leaflet'

const STOP_ICONS = {
  start: { color: '#10b981', symbol: '▶' },
  end: { color: '#ef4444', symbol: '⬛' },
  pickup: { color: '#10b981', symbol: 'P' },
  dropoff: { color: '#3b82f6', symbol: 'D' },
  fuel: { color: '#f59e0b', symbol: 'F' },
  rest: { color: '#8b5cf6', symbol: 'R' },
  break: { color: '#06b6d4', symbol: 'B' },
  restart: { color: '#ec4899', symbol: '34' },
}

function createIcon(type) {
  const cfg = STOP_ICONS[type] || { color: '#6b7280', symbol: '?' }
  return L.divIcon({
    className: '',
    html: `<div style="
      width:28px;height:28px;border-radius:50%;
      background:${cfg.color};color:#fff;
      display:flex;align-items:center;justify-content:center;
      font-size:11px;font-weight:700;font-family:Inter,sans-serif;
      border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.4);
    ">${cfg.symbol}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  })
}

export default function RouteMap({ route, stops, locations }) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)

  useEffect(() => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove()
      mapInstanceRef.current = null
    }

    const map = L.map(mapRef.current, {
      zoomControl: true,
      attributionControl: true,
    })
    mapInstanceRef.current = map

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OSM &copy; CARTO',
      maxZoom: 19,
    }).addTo(map)

    // Draw route
    if (route?.geometry?.coordinates) {
      const latlngs = route.geometry.coordinates.map(c => [c[1], c[0]])
      // Glow effect
      L.polyline(latlngs, {
        color: '#3b82f6', weight: 8, opacity: 0.25,
      }).addTo(map)
      // Main line
      L.polyline(latlngs, {
        color: '#60a5fa', weight: 4, opacity: 0.9,
      }).addTo(map)

      map.fitBounds(L.latLngBounds(latlngs).pad(0.1))
    }

    // Add stop markers
    stops.forEach((stop) => {
      let markerLat, markerLng

      // Use geocoded coords for known locations (they're [lat, lon])
      if (stop.type === 'start' && locations?.current?.coords) {
        markerLat = locations.current.coords[0]
        markerLng = locations.current.coords[1]
      } else if (stop.type === 'pickup' && locations?.pickup?.coords) {
        markerLat = locations.pickup.coords[0]
        markerLng = locations.pickup.coords[1]
      } else if ((stop.type === 'dropoff' || stop.type === 'end') && locations?.dropoff?.coords) {
        markerLat = locations.dropoff.coords[0]
        markerLng = locations.dropoff.coords[1]
      } else {
        // Interpolated stops from HOS engine are [lon, lat] (GeoJSON order)
        const coords = stop.location
        if (!coords || coords.length < 2) return
        markerLng = coords[0]  // longitude first in GeoJSON
        markerLat = coords[1]  // latitude second
      }

      if (!markerLat || !markerLng) return

      const marker = L.marker([markerLat, markerLng], {
        icon: createIcon(stop.type),
      }).addTo(map)

      const time = new Date(stop.time).toLocaleString('en-US', {
        weekday: 'short', month: 'short', day: 'numeric',
        hour: 'numeric', minute: '2-digit', hour12: true,
      })

      marker.bindPopup(`
        <div style="font-family:Inter,sans-serif;">
          <strong>${stop.label}</strong><br/>
          <span style="font-size:12px;opacity:.8;">${time}</span><br/>
          <span style="font-size:12px;opacity:.8;">📍 ${stop.location_name}</span>
        </div>
      `)
    })

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [route, stops, locations])

  return (
    <div className="map-container">
      <div ref={mapRef} style={{ height: '100%', width: '100%' }} />
    </div>
  )
}

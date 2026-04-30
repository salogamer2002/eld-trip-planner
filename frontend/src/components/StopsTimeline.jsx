export default function StopsTimeline({ stops }) {
  const formatTime = (iso) => {
    const d = new Date(iso)
    return d.toLocaleString('en-US', {
      weekday: 'short', month: 'short', day: 'numeric',
      hour: 'numeric', minute: '2-digit', hour12: true,
    })
  }

  const formatDuration = (hrs) => {
    if (hrs < 1) return `${Math.round(hrs * 60)} min`
    const h = Math.floor(hrs)
    const m = Math.round((hrs - h) * 60)
    return m > 0 ? `${h}h ${m}m` : `${h}h`
  }

  const typeEmojis = {
    start: '🟢', end: '🔴', pickup: '📦', dropoff: '🏁',
    fuel: '⛽', rest: '🛏️', break: '☕', restart: '🔄',
  }

  return (
    <div className="stops-timeline">
      {stops.map((stop, i) => (
        <div className="stop-item" key={i}>
          <div className={`stop-dot ${stop.type}`} />
          <div className="stop-content">
            <div className="stop-label">
              {typeEmojis[stop.type] || '📍'} {stop.label}
            </div>
            <div className="stop-meta">
              <span>🕐 {formatTime(stop.time)}</span>
              {stop.duration > 0 && (
                <span>⏱️ {formatDuration(stop.duration)}</span>
              )}
              <span>📍 {stop.location_name}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function TripSummary({ summary, locations }) {
  const cards = [
    { icon: '🛣️', value: `${summary.total_distance_miles} mi`, label: 'Total Distance' },
    { icon: '🕐', value: `${summary.total_driving_hours} hrs`, label: 'Driving Time' },
    { icon: '📅', value: summary.total_days, label: 'Total Days' },
    { icon: '⛽', value: summary.num_fuel_stops, label: 'Fuel Stops' },
    { icon: '🛏️', value: summary.num_rest_stops, label: 'Rest Stops' },
    { icon: '☕', value: summary.num_breaks, label: '30-Min Breaks' },
  ]

  return (
    <section>
      <div className="section-header">
        <h2 className="section-title">📊 Trip Summary</h2>
        <p className="section-subtitle">
          {locations.current.name.split(',').slice(0, 2).join(',')} →{' '}
          {locations.pickup.name.split(',').slice(0, 2).join(',')} →{' '}
          {locations.dropoff.name.split(',').slice(0, 2).join(',')}
        </p>
      </div>
      <div className="summary-grid">
        {cards.map((card, i) => (
          <div className="summary-card" key={i}>
            <div className="icon">{card.icon}</div>
            <div className="value">{card.value}</div>
            <div className="label">{card.label}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

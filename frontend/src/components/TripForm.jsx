import { useState } from 'react'

export default function TripForm({ onSubmit, loading }) {
  const [form, setForm] = useState({
    current_location: '',
    pickup_location: '',
    dropoff_location: '',
    cycle_hours_used: 0,
  })

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit(form)
  }

  return (
    <form className="trip-form-card" onSubmit={handleSubmit}>
      <div className="section-header">
        <h1 className="section-title">🚀 Plan Your Trip</h1>
        <p className="section-subtitle">
          Enter trip details to generate an HOS-compliant route with ELD logs
        </p>
      </div>

      <div className="form-grid">
        <div className="form-group">
          <label className="form-label" htmlFor="current_location">
            <span className="icon">📍</span> Current Location
          </label>
          <input
            id="current_location"
            className="form-input"
            type="text"
            name="current_location"
            placeholder="e.g. Dallas, TX"
            value={form.current_location}
            onChange={handleChange}
            required
          />
          <span className="form-input-hint">City, State or full address</span>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="pickup_location">
            <span className="icon">📦</span> Pickup Location
          </label>
          <input
            id="pickup_location"
            className="form-input"
            type="text"
            name="pickup_location"
            placeholder="e.g. Houston, TX"
            value={form.pickup_location}
            onChange={handleChange}
            required
          />
          <span className="form-input-hint">Where you pick up the load</span>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="dropoff_location">
            <span className="icon">🏁</span> Dropoff Location
          </label>
          <input
            id="dropoff_location"
            className="form-input"
            type="text"
            name="dropoff_location"
            placeholder="e.g. Los Angeles, CA"
            value={form.dropoff_location}
            onChange={handleChange}
            required
          />
          <span className="form-input-hint">Final delivery destination</span>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="cycle_hours_used">
            <span className="icon">⏱️</span> Current Cycle Used (Hrs)
          </label>
          <input
            id="cycle_hours_used"
            className="form-input"
            type="number"
            name="cycle_hours_used"
            min="0"
            max="70"
            step="0.5"
            placeholder="0"
            value={form.cycle_hours_used}
            onChange={handleChange}
            required
          />
          <span className="form-input-hint">Hours used in current 70hr/8-day cycle (0–70)</span>
        </div>
      </div>

      <div className="form-actions">
        <button className="btn-primary" type="submit" disabled={loading}>
          {loading ? (
            <>
              <div className="spinner" /> Calculating...
            </>
          ) : (
            <>🗺️ Generate Route & ELD Logs</>
          )}
        </button>
      </div>
    </form>
  )
}

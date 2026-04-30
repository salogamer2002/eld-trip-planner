import { useEffect, useRef } from 'react'

const STATUS_ROWS = ['off_duty', 'sleeper', 'driving', 'on_duty']
const STATUS_LABELS = ['1. Off Duty', '2. Sleeper Berth', '3. Driving', '4. On Duty (Not Driving)']
const STATUS_COLORS = {
  off_duty: '#10b981',
  sleeper: '#8b5cf6',
  driving: '#3b82f6',
  on_duty: '#f59e0b',
}

export default function ELDLogSheet({ log, driverName, carrierName }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const W = 1000
    const H = 620
    canvas.width = W * 2
    canvas.height = H * 2
    ctx.scale(2, 2)
    canvas.style.width = W + 'px'
    canvas.style.height = H + 'px'

    drawLog(ctx, W, H, log, driverName, carrierName)
  }, [log, driverName, carrierName])

  const dateStr = new Date(log.date + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  })

  return (
    <div className="log-sheet-wrapper">
      <div className="log-sheet-header">
        <div>
          <span className="log-day-badge">Day {log.day_number}</span>
          <span className="log-date" style={{ marginLeft: '0.75rem' }}>{dateStr}</span>
        </div>
        <span className="log-date">{log.total_miles} miles driven</span>
      </div>
      <div className="eld-canvas-container">
        <canvas ref={canvasRef} />
      </div>
      <div className="log-totals">
        <div className="log-total-item">
          <span className="log-total-label">Off Duty</span>
          <span className="log-total-value" style={{ color: '#10b981' }}>{log.totals.off_duty}h</span>
        </div>
        <div className="log-total-item">
          <span className="log-total-label">Sleeper Berth</span>
          <span className="log-total-value" style={{ color: '#8b5cf6' }}>{log.totals.sleeper}h</span>
        </div>
        <div className="log-total-item">
          <span className="log-total-label">Driving</span>
          <span className="log-total-value" style={{ color: '#3b82f6' }}>{log.totals.driving}h</span>
        </div>
        <div className="log-total-item">
          <span className="log-total-label">On Duty (Not Driving)</span>
          <span className="log-total-value" style={{ color: '#f59e0b' }}>{log.totals.on_duty}h</span>
        </div>
        <div className="log-total-item">
          <span className="log-total-label">Total</span>
          <span className="log-total-value">
            {(log.totals.off_duty + log.totals.sleeper + log.totals.driving + log.totals.on_duty).toFixed(1)}h
          </span>
        </div>
      </div>

      {log.remarks && log.remarks.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <div className="log-total-label" style={{ marginBottom: '0.5rem' }}>Remarks</div>
          {log.remarks.map((r, i) => (
            <div key={i} style={{
              fontSize: '0.8rem', color: '#8b92a8', marginBottom: '0.25rem',
              paddingLeft: '0.5rem', borderLeft: '2px solid #3b82f6'
            }}>
              {formatHour(r.time)} — {r.activity} @ {r.location}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function formatHour(h) {
  const hr = Math.floor(h)
  const min = Math.round((h - hr) * 60)
  const ampm = hr >= 12 ? 'PM' : 'AM'
  const display = hr === 0 ? 12 : hr > 12 ? hr - 12 : hr
  return `${display}:${min.toString().padStart(2, '0')} ${ampm}`
}

function drawLog(ctx, W, H, log, driverName, carrierName) {
  // Background
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, W, H)

  // Layout constants
  const marginLeft = 30
  const marginRight = 30
  const headerHeight = 100
  const gridTop = headerHeight + 10
  const gridLeft = 160
  const gridRight = W - marginRight - 50
  const gridWidth = gridRight - gridLeft
  const rowHeight = 40
  const gridHeight = rowHeight * 4
  const totalColWidth = 50
  const remarksTop = gridTop + gridHeight + 30

  // ===== HEADER =====
  ctx.fillStyle = '#1a1f35'
  ctx.fillRect(0, 0, W, 50)

  ctx.fillStyle = '#ffffff'
  ctx.font = 'bold 16px Inter, sans-serif'
  ctx.textAlign = 'left'
  ctx.fillText("DRIVER'S DAILY LOG", marginLeft, 32)

  ctx.font = '11px Inter, sans-serif'
  ctx.fillStyle = '#94a3b8'
  ctx.fillText('(24 Hours)', marginLeft + 195, 32)

  ctx.textAlign = 'right'
  ctx.fillStyle = '#60a5fa'
  ctx.font = 'bold 12px Inter, sans-serif'
  ctx.fillText('FMCSA HOS COMPLIANT', W - marginRight, 32)

  // Info row
  ctx.textAlign = 'left'
  ctx.fillStyle = '#334155'
  ctx.font = '11px Inter, sans-serif'

  const dateDisplay = new Date(log.date + 'T00:00:00').toLocaleDateString('en-US', {
    month: '2-digit', day: '2-digit', year: 'numeric'
  })

  const fields = [
    { label: 'Date:', value: dateDisplay, x: marginLeft },
    { label: 'Miles:', value: String(log.total_miles), x: 180 },
    { label: 'Driver:', value: driverName || 'Driver', x: 300 },
    { label: 'Carrier:', value: carrierName || 'Carrier', x: 480 },
    { label: 'From:', value: (log.from_location || '').substring(0, 20), x: marginLeft, y: 80 },
    { label: 'To:', value: (log.to_location || '').substring(0, 20), x: 300, y: 80 },
  ]

  fields.forEach(f => {
    const y = f.y || 65
    ctx.fillStyle = '#64748b'
    ctx.font = '10px Inter, sans-serif'
    ctx.fillText(f.label, f.x, y)
    ctx.fillStyle = '#1e293b'
    ctx.font = '12px Inter, sans-serif'
    ctx.fillText(f.value, f.x + ctx.measureText(f.label).width + 6, y)
  })

  // ===== GRID HEADER (Hour labels) =====
  ctx.fillStyle = '#f1f5f9'
  ctx.fillRect(gridLeft, gridTop - 22, gridWidth, 20)
  ctx.strokeStyle = '#cbd5e1'
  ctx.lineWidth = 1
  ctx.strokeRect(gridLeft, gridTop - 22, gridWidth, 20)

  const hourWidth = gridWidth / 24
  ctx.fillStyle = '#334155'
  ctx.font = 'bold 9px Inter, sans-serif'
  ctx.textAlign = 'center'

  for (let h = 0; h <= 24; h++) {
    const x = gridLeft + h * hourWidth
    let label = ''
    if (h === 0 || h === 24) label = 'M'
    else if (h === 12) label = 'N'
    else label = String(h > 12 ? h - 12 : h)
    ctx.fillText(label, x, gridTop - 8)
  }

  // ===== ROW LABELS =====
  ctx.textAlign = 'left'
  for (let r = 0; r < 4; r++) {
    const y = gridTop + r * rowHeight
    // Alternating row background
    ctx.fillStyle = r % 2 === 0 ? '#fafbfc' : '#f1f5f9'
    ctx.fillRect(marginLeft, y, gridLeft - marginLeft, rowHeight)

    ctx.fillStyle = '#334155'
    ctx.font = 'bold 10px Inter, sans-serif'
    ctx.fillText(STATUS_LABELS[r], marginLeft + 6, y + rowHeight / 2 + 4)
  }

  // ===== GRID CELLS =====
  for (let r = 0; r < 4; r++) {
    const y = gridTop + r * rowHeight
    ctx.fillStyle = r % 2 === 0 ? '#fafbfc' : '#f1f5f9'
    ctx.fillRect(gridLeft, y, gridWidth, rowHeight)
  }

  // Grid lines - vertical (hours)
  for (let h = 0; h <= 24; h++) {
    const x = gridLeft + h * hourWidth
    ctx.strokeStyle = h % 1 === 0 ? '#cbd5e1' : '#e2e8f0'
    ctx.lineWidth = h === 0 || h === 12 || h === 24 ? 1.5 : 0.5
    ctx.beginPath()
    ctx.moveTo(x, gridTop)
    ctx.lineTo(x, gridTop + gridHeight)
    ctx.stroke()
  }

  // 15-min marks
  for (let h = 0; h < 24; h++) {
    for (let q = 1; q < 4; q++) {
      const x = gridLeft + (h + q / 4) * hourWidth
      ctx.strokeStyle = '#e2e8f0'
      ctx.lineWidth = 0.3
      ctx.beginPath()
      ctx.moveTo(x, gridTop)
      ctx.lineTo(x, gridTop + gridHeight)
      ctx.stroke()
    }
  }

  // Grid lines - horizontal (rows)
  for (let r = 0; r <= 4; r++) {
    const y = gridTop + r * rowHeight
    ctx.strokeStyle = '#cbd5e1'
    ctx.lineWidth = r === 0 || r === 4 ? 1.5 : 0.8
    ctx.beginPath()
    ctx.moveTo(gridLeft, y)
    ctx.lineTo(gridRight, y)
    ctx.stroke()
  }

  // ===== TOTAL HOURS COLUMN =====
  ctx.fillStyle = '#f1f5f9'
  ctx.fillRect(gridRight, gridTop - 22, totalColWidth, 20)
  ctx.strokeStyle = '#cbd5e1'
  ctx.strokeRect(gridRight, gridTop - 22, totalColWidth, 20)
  ctx.fillStyle = '#334155'
  ctx.font = 'bold 9px Inter, sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText('TOTAL', gridRight + totalColWidth / 2, gridTop - 8)

  const totalValues = [
    log.totals.off_duty, log.totals.sleeper, log.totals.driving, log.totals.on_duty
  ]
  for (let r = 0; r < 4; r++) {
    const y = gridTop + r * rowHeight
    ctx.fillStyle = r % 2 === 0 ? '#fafbfc' : '#f1f5f9'
    ctx.fillRect(gridRight, y, totalColWidth, rowHeight)
    ctx.strokeStyle = '#cbd5e1'
    ctx.strokeRect(gridRight, y, totalColWidth, rowHeight)

    ctx.fillStyle = STATUS_COLORS[STATUS_ROWS[r]]
    ctx.font = 'bold 13px Inter, sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(totalValues[r].toFixed(1), gridRight + totalColWidth / 2, y + rowHeight / 2 + 5)
  }

  // ===== DRAW DUTY STATUS LINES =====
  const entries = log.entries || []
  ctx.lineWidth = 3
  ctx.lineCap = 'round'

  entries.forEach((entry) => {
    const rowIdx = STATUS_ROWS.indexOf(entry.status)
    if (rowIdx < 0) return

    const x1 = gridLeft + (entry.start_hour / 24) * gridWidth
    const x2 = gridLeft + (entry.end_hour / 24) * gridWidth
    const y = gridTop + rowIdx * rowHeight + rowHeight / 2

    const color = STATUS_COLORS[entry.status]
    ctx.strokeStyle = color
    ctx.lineWidth = 3.5

    // Horizontal line for this status period
    ctx.beginPath()
    ctx.moveTo(x1, y)
    ctx.lineTo(x2, y)
    ctx.stroke()

    // Small dots at endpoints
    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(x1, y, 3, 0, Math.PI * 2)
    ctx.fill()
    ctx.beginPath()
    ctx.arc(x2, y, 3, 0, Math.PI * 2)
    ctx.fill()
  })

  // Draw vertical transition lines between entries
  ctx.strokeStyle = '#475569'
  ctx.lineWidth = 1.5
  ctx.setLineDash([3, 2])

  for (let i = 0; i < entries.length - 1; i++) {
    const curr = entries[i]
    const next = entries[i + 1]
    if (Math.abs(curr.end_hour - next.start_hour) > 0.05) continue

    const currRow = STATUS_ROWS.indexOf(curr.status)
    const nextRow = STATUS_ROWS.indexOf(next.status)
    if (currRow < 0 || nextRow < 0 || currRow === nextRow) continue

    const x = gridLeft + (curr.end_hour / 24) * gridWidth
    const y1 = gridTop + currRow * rowHeight + rowHeight / 2
    const y2 = gridTop + nextRow * rowHeight + rowHeight / 2

    ctx.beginPath()
    ctx.moveTo(x, y1)
    ctx.lineTo(x, y2)
    ctx.stroke()
  }
  ctx.setLineDash([])

  // ===== REMARKS SECTION =====
  ctx.fillStyle = '#1a1f35'
  ctx.fillRect(marginLeft, remarksTop, W - marginLeft - marginRight, 24)
  ctx.fillStyle = '#ffffff'
  ctx.font = 'bold 11px Inter, sans-serif'
  ctx.textAlign = 'left'
  ctx.fillText('REMARKS', marginLeft + 8, remarksTop + 16)

  const remarks = log.remarks || []
  ctx.font = '10px Inter, sans-serif'
  ctx.fillStyle = '#334155'
  remarks.slice(0, 8).forEach((r, i) => {
    const ry = remarksTop + 38 + i * 16
    ctx.fillText(`${formatHour(r.time)}  —  ${r.activity} @ ${r.location}`, marginLeft + 8, ry)
  })

  // ===== BOTTOM BORDER =====
  ctx.fillStyle = '#3b82f6'
  ctx.fillRect(0, H - 3, W, 3)
}

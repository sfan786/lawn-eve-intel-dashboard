import React, { useState, useEffect, useCallback } from 'react'
import { formatCountdown, formatEveTime } from '../utils/campaignHelpers'
import CornerBrackets from './common/CornerBrackets'

const inputStyle = {
    background: 'var(--bg-deep)', border: '1px solid var(--border-dim)', color: 'var(--text-primary)', padding: 4, fontSize: 11, fontFamily: 'Share Tech Mono'
}

const actionBtnStyle = {
    background: 'transparent',
    border: '1px solid var(--cyan-dim)',
    fontFamily: 'Share Tech Mono',
    fontSize: 10,
    padding: '2px 8px',
    cursor: 'pointer'
}

export default function TimerBoard() {
    const [timers, setTimers] = useState([])
    const [showForm, setShowForm] = useState(false)
    const [newTimer, setNewTimer] = useState({
        system_name: "", structure_type: "Fortizar", owner: "", event_type: "Armor", timestamp: "", notes: ""
    })
    const [now, setNow] = useState(new Date())
    const [password, setPassword] = useState(localStorage.getItem("timer_auth") || "")
    const [isAuthenticated, setIsAuthenticated] = useState(false)
    const [authError, setAuthError] = useState(false)

    const checkAuth = useCallback(async () => {
        if (!password) return
        try {
            const res = await fetch("/api/auth/check", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ password })
            })
            if (res.ok) {
                setIsAuthenticated(true)
                setAuthError(false)
                localStorage.setItem("timer_auth", password)
            } else {
                setIsAuthenticated(false)
                setAuthError(true)
            }
        } catch (e) {
            setIsAuthenticated(false)
        }
    }, [password])

    const fetchTimers = useCallback(async () => {
        const res = await fetch("/api/timers")
        if (res.ok) {
            const data = await res.json()
            setTimers(data)
        }
    }, [])

    useEffect(() => {
        fetchTimers()
        const interval = setInterval(() => setNow(new Date()), 1000)
        if (password) checkAuth()
        return () => clearInterval(interval)
    }, [fetchTimers, checkAuth, password])

    const handleLogin = (e) => {
        e.preventDefault()
        checkAuth()
    }

    const handleLogout = () => {
        setIsAuthenticated(false)
        setPassword("")
        localStorage.removeItem("timer_auth")
        setShowForm(false)
    }

    function parseDuration(input) {
        if (!input) return null
        const regex = /(\d+)\s*([dhms])/g
        let totalMs = 0
        let match
        while ((match = regex.exec(input)) !== null) {
            const value = parseInt(match[1])
            const unit = match[2]
            if (unit === 'd') totalMs += value * 86400000
            else if (unit === 'h') totalMs += value * 3600000
            else if (unit === 'm') totalMs += value * 60000
            else if (unit === 's') totalMs += value * 1000
        }
        return totalMs > 0 ? totalMs : null
    }

    const handleAdd = async () => {
        if (!newTimer.system_name || !newTimer.timestamp) return

        let isoTimestamp = newTimer.timestamp
        const durationMs = parseDuration(newTimer.timestamp)

        if (durationMs) {
            isoTimestamp = new Date(Date.now() + durationMs).toISOString()
        }

        const res = await fetch("/api/timers", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Timer-Auth": password
            },
            body: JSON.stringify({ ...newTimer, timestamp: isoTimestamp })
        })

        if (res.ok) {
            setShowForm(false)
            setNewTimer({ system_name: "", structure_type: "Fortizar", owner: "", event_type: "Armor", timestamp: "", notes: "" })
            fetchTimers()
        } else if (res.status === 401) {
            setIsAuthenticated(false)
            setAuthError(true)
        }
    }

    const handleDelete = async (id) => {
        if (!confirm("Delete this timer?")) return
        const res = await fetch(`/api/timers/${id}`, {
            method: "DELETE",
            headers: { "X-Timer-Auth": password }
        })

        if (res.ok) {
            fetchTimers()
        } else if (res.status === 401) {
            setIsAuthenticated(false)
            setAuthError(true)
        }
    }

    return (
        <div className="panel panel-wide" style={{ marginBottom: 16 }}>
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">⏱ Strategic Timerboard</span>
                {isAuthenticated ? (
                    <div style={{ display: 'flex', gap: 8 }}>
                        <button onClick={() => setShowForm(!showForm)} style={actionBtnStyle}>
                            {showForm ? "CANCEL" : "+ ADD TIMER"}
                        </button>
                        <button onClick={handleLogout} style={actionBtnStyle}>LOGOUT</button>
                    </div>
                ) : (
                    <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'Share Tech Mono' }}>READ ONLY</span>
                )}
            </div>

            {!isAuthenticated && showForm && (
                <div style={{ padding: 10, background: 'rgba(255,51,85,0.1)', marginBottom: 10, border: '1px solid var(--red-dim)' }}>
                    <form onSubmit={handleLogin} style={{ display: 'flex', gap: 8 }}>
                        <input
                            type="password"
                            placeholder="Enter Password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            style={{ ...inputStyle, flex: 1 }}
                        />
                        <button type="submit" style={{ ...actionBtnStyle, background: 'var(--red-dim)', color: '#fff' }}>LOGIN</button>
                    </form>
                    {authError && <div style={{ color: 'var(--red)', fontSize: 10, marginTop: 4 }}>Invalid password</div>}
                </div>
            )}

            {isAuthenticated && showForm && (
                <div style={{ padding: 10, background: 'rgba(0,212,255,0.05)', marginBottom: 10, border: '1px solid var(--border-dim)' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 8 }}>
                        <input placeholder="System" value={newTimer.system_name} onChange={e => setNewTimer({ ...newTimer, system_name: e.target.value })} style={inputStyle} />
                        <input placeholder="Structure (e.g. Fortizar)" value={newTimer.structure_type} onChange={e => setNewTimer({ ...newTimer, structure_type: e.target.value })} style={inputStyle} />
                        <input placeholder="Owner" value={newTimer.owner} onChange={e => setNewTimer({ ...newTimer, owner: e.target.value })} style={inputStyle} />
                        <select value={newTimer.event_type} onChange={e => setNewTimer({ ...newTimer, event_type: e.target.value })} style={inputStyle}>
                            <option>Armor</option>
                            <option>Hull</option>
                            <option>Shield</option>
                            <option>Anchoring</option>
                        </select>
                        <input
                            type="text"
                            placeholder="Duration (e.g. 1d 4h 30m)"
                            value={newTimer.timestamp}
                            onChange={e => setNewTimer({ ...newTimer, timestamp: e.target.value })}
                            style={inputStyle}
                        />
                        <input placeholder="Notes" value={newTimer.notes} onChange={e => setNewTimer({ ...newTimer, notes: e.target.value })} style={inputStyle} />
                    </div>
                    <button onClick={handleAdd} style={{
                        width: '100%', background: 'var(--cyan-dim)', color: '#fff', border: 'none', padding: 6, fontFamily: 'Orbitron', fontSize: 11
                    }}>SAVE TIMER</button>
                </div>
            )}

            {timers.length === 0 && !showForm && (
                <div style={{ padding: 10, textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-muted)', fontSize: 11, fontStyle: 'italic' }}>No active timers. Secure the lawn.</div>
                    {!isAuthenticated && (
                        <button onClick={() => setShowForm(true)} style={{ marginTop: 8, background: 'none', border: '1px solid var(--text-muted)', color: 'var(--text-muted)', fontSize: 10, padding: '2px 8px', cursor: 'pointer' }}>
                            LOGIN TO MANAGE
                        </button>
                    )}
                </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {timers.map(t => {
                    const time = new Date(t.timestamp)
                    const diff = time - now
                    const isPast = diff < 0
                    const timeLeft = formatCountdown(time)

                    return (
                        <React.Fragment key={t.id}>
                        <div className="campaign-entry-compact" style={{ borderLeft: `3px solid ${isPast ? 'var(--text-muted)' : 'var(--cyan)'}` }}>
                            <div style={{ width: 80, fontSize: 10, color: 'var(--text-secondary)' }}>
                                {t.event_type.toUpperCase()}
                            </div>
                            <div style={{ width: 120, fontWeight: 'bold', color: 'var(--cyan)' }}>
                                {t.system_name}
                            </div>
                            <div style={{ width: 100, fontSize: 11, color: 'var(--text-primary)' }}>
                                {t.structure_type}
                            </div>
                            <div style={{ width: 120, fontSize: 11, color: 'var(--text-muted)' }}>
                                {t.owner}
                            </div>
                            <div style={{ flex: 1, textAlign: 'right', fontFamily: 'Share Tech Mono', color: isPast ? 'var(--red)' : 'var(--text-primary)' }}>
                                {isPast ? "EXPIRED" : timeLeft}
                                <span style={{ marginLeft: 8, fontSize: 10, color: 'var(--text-muted)' }}>
                                    {formatEveTime(time.toISOString())}
                                </span>
                            </div>
                            {isAuthenticated && (
                                <button onClick={() => handleDelete(t.id)} style={{
                                    marginLeft: 12, background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 14
                                }}>×</button>
                            )}
                        </div>
                        {t.notes && (
                            <div style={{ paddingLeft: 8, paddingBottom: 4, fontSize: 10, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                {t.notes}
                            </div>
                        )}
                        </React.Fragment>
                    )
                })}
            </div>
        </div>
    )
}

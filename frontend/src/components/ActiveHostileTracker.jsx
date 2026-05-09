import React, { useState, useEffect } from 'react'
import CornerBrackets from './common/CornerBrackets'

function threatLevel(entity) {
    if (entity.primary_kills >= 3) return { label: 'HIGH', color: '#ff3355', bg: 'rgba(255,51,85,0.15)' }
    if (entity.primary_kills >= 1 || entity.kill_count >= 4) return { label: 'MED', color: '#ffaa00', bg: 'rgba(255,170,0,0.12)' }
    return { label: 'LOW', color: '#6a8090', bg: 'rgba(106,128,144,0.1)' }
}

function timeAgo(isoStr) {
    if (!isoStr) return '—'
    const diff = Date.now() - new Date(isoStr).getTime()
    const m = Math.floor(diff / 60000)
    if (m < 1) return 'just now'
    if (m < 60) return `${m}m ago`
    const h = Math.floor(m / 60)
    return `${h}h ${m % 60}m ago`
}

export default function ActiveHostileTracker({ lastUpdate }) {
    const [hostiles, setHostiles] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        setLoading(true)
        fetch('/api/intel/active_hostiles')
            .then(r => { if (!r.ok) throw new Error(r.status); return r.json() })
            .then(data => { setHostiles(data); setLoading(false); setError(null) })
            .catch(e => { setError(e.message); setLoading(false) })
    }, [lastUpdate])

    if (loading) return null
    if (error) return null

    const primaryActive = hostiles.filter(h => h.primary_kills > 0).length

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">ACTIVE HOSTILE TRACKER</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {primaryActive > 0 && (
                        <span className="panel-badge" style={{ background: 'rgba(255,51,85,0.2)', borderColor: '#ff3355', color: '#ff3355' }}>
                            {primaryActive} IN PRIMARY
                        </span>
                    )}
                    <span className="panel-badge">
                        {hostiles.length > 0 ? `${hostiles.length} entities · recent kills` : 'recent kills'}
                    </span>
                </div>
            </div>

            {hostiles.length === 0 && (
                <div style={{
                    padding: '10px 12px', background: 'rgba(0,255,136,0.06)',
                    border: '1px solid rgba(0,255,136,0.2)',
                    fontFamily: 'Orbitron, sans-serif', fontSize: 10,
                    letterSpacing: 2, color: '#00ff88',
                }}>
                    REGION CLEAR — no hostile kill activity detected in recent feed
                </div>
            )}

            {hostiles.length > 0 && <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-dim)' }}>
                        {['ENTITY', 'THREAT', 'KILLS', 'ACTIVE IN', 'SHIPS', 'LAST SEEN'].map(h => (
                            <th key={h} style={{
                                padding: '3px 8px', textAlign: 'left',
                                fontFamily: 'Orbitron, sans-serif', fontSize: 8,
                                letterSpacing: 2, color: 'var(--text-muted)', fontWeight: 600,
                            }}>{h}</th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {hostiles.map(entity => {
                        const threat = threatLevel(entity)
                        return (
                            <tr key={entity.id} style={{
                                borderBottom: '1px solid rgba(0,212,255,0.05)',
                                background: entity.primary_kills > 0 ? 'rgba(255,51,85,0.04)' : 'transparent',
                            }}>
                                {/* Entity name + logo */}
                                <td style={{ padding: '6px 8px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <img
                                            src={`https://images.evetech.net/${entity.type}s/${entity.id}/logo?size=32`}
                                            alt=""
                                            style={{ width: 24, height: 24, borderRadius: 3, flexShrink: 0 }}
                                            onError={e => { e.target.style.display = 'none' }}
                                        />
                                        <div>
                                            <div style={{
                                                fontFamily: 'Share Tech Mono, monospace', fontSize: 11,
                                                color: entity.primary_kills > 0 ? '#ff6677' : 'var(--text-primary)',
                                                fontWeight: entity.primary_kills > 0 ? 700 : 400,
                                                maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                                            }}>{entity.name}</div>
                                            <div style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-muted)' }}>
                                                {entity.type.toUpperCase()} · {entity.pilot_count} pilots
                                            </div>
                                        </div>
                                    </div>
                                </td>

                                {/* Threat badge */}
                                <td style={{ padding: '6px 8px', whiteSpace: 'nowrap' }}>
                                    <span style={{
                                        fontFamily: 'Orbitron, sans-serif', fontSize: 8, letterSpacing: 2,
                                        fontWeight: 700, color: threat.color,
                                        background: threat.bg, border: `1px solid ${threat.color}44`,
                                        padding: '2px 6px',
                                    }}>{threat.label}</span>
                                </td>

                                {/* Kill counts */}
                                <td style={{ padding: '6px 8px', whiteSpace: 'nowrap' }}>
                                    <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
                                        {entity.kill_count}
                                    </span>
                                    {entity.primary_kills > 0 && (
                                        <span style={{ marginLeft: 4, fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: '#ff3355' }}>
                                            ({entity.primary_kills} primary)
                                        </span>
                                    )}
                                </td>

                                {/* Systems active in */}
                                <td style={{ padding: '6px 8px' }}>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                                        {entity.systems.slice(0, 4).map(s => (
                                            <span key={s.name} style={{
                                                fontFamily: 'Share Tech Mono, monospace', fontSize: 9,
                                                background: 'rgba(0,212,255,0.08)', border: '1px solid rgba(0,212,255,0.2)',
                                                color: 'var(--cyan)', padding: '1px 5px',
                                            }}>{s.name}{s.count > 1 ? ` ×${s.count}` : ''}</span>
                                        ))}
                                    </div>
                                </td>

                                {/* Top ship types */}
                                <td style={{ padding: '6px 8px' }}>
                                    <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-secondary)' }}>
                                        {entity.ship_types.slice(0, 3).map(s => s.count > 1 ? `${s.name} ×${s.count}` : s.name).join(', ') || '—'}
                                    </span>
                                </td>

                                {/* Last seen */}
                                <td style={{ padding: '6px 8px', whiteSpace: 'nowrap' }}>
                                    <div style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-secondary)' }}>
                                        {entity.last_seen_system}
                                    </div>
                                    <div style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-muted)' }}>
                                        {timeAgo(entity.last_seen)}
                                    </div>
                                </td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>}
        </div>
    )
}

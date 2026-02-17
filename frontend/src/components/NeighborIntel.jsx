import React, { useState, useEffect } from 'react'

export default function NeighborIntel({ lastUpdate }) {
    const [neighbors, setNeighbors] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetch("/api/intel/neighbors")
            .then(r => r.json())
            .then(data => {
                setNeighbors(data)
                setLoading(false)
            })
            .catch(err => {
                console.error("Failed to load neighbor intel", err)
                setLoading(false)
            })
    }, [lastUpdate])

    if (loading) return null
    if (!neighbors.length) return null

    return (
        <div className="panel panel-wide">
            <div className="panel-header">
                <span className="panel-title">Neighbor Threat Profiling (Previous 24h)</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 10 }}>
                {neighbors.map(n => (
                    <div key={n.id} style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-dim)', padding: 10 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <img
                                    src={`https://images.evetech.net/${n.type}s/${n.id}/logo?size=32`}
                                    alt={n.name}
                                    style={{ width: 32, height: 32, borderRadius: 4 }}
                                />
                                <div>
                                    <div style={{ fontWeight: 'bold', color: 'var(--cyan)' }}>{n.name}</div>
                                    <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{n.type.toUpperCase()} • Kills: {n.total_kills_24h}</div>
                                </div>
                            </div>
                            <div style={{
                                padding: '2px 6px', borderRadius: 2, fontSize: 10, fontWeight: 'bold',
                                background: n.threat_level === 'High' ? 'var(--red)' : n.threat_level === 'Medium' ? 'var(--amber)' : 'var(--green)',
                                color: '#000'
                            }}>
                                {n.threat_level.toUpperCase()} THREAT
                            </div>
                        </div>

                        <div style={{ marginBottom: 8 }}>
                            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>TOP SHIPS</div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                {n.top_ships.map((s, i) => (
                                    <span key={i} style={{ background: 'rgba(255,255,255,0.1)', padding: '1px 4px', borderRadius: 2, fontSize: 10 }}>
                                        {s.count}x {s.name}
                                    </span>
                                ))}
                            </div>
                        </div>

                        <div>
                            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>ACTIVITY (UTC)</div>
                            <div style={{ display: 'flex', alignItems: 'flex-end', height: 20, gap: 1 }}>
                                {n.activity_heatmap.map((val, h) => {
                                    const max = Math.max(...n.activity_heatmap) || 1
                                    const height = Math.max(2, (val / max) * 100)
                                    const color = val > 0 ? 'var(--red)' : '#333'
                                    return (
                                        <div key={h} title={`${h}:00 UTC - ${val} kills`} style={{
                                            flex: 1,
                                            height: `${height}%`,
                                            background: color,
                                            opacity: val > 0 ? 0.8 : 0.3
                                        }} />
                                    )
                                })}
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 8, color: '#555', marginTop: 1 }}>
                                <span>00</span><span>06</span><span>12</span><span>18</span><span>23</span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}

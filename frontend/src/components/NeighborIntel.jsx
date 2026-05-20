import React, { useState, useEffect } from 'react'
import CornerBrackets from './common/CornerBrackets'

const THREAT_COLOR = { High: '#ff3355', Medium: '#ffaa00', Low: '#00ff88' }

const ROLE_COLOR = {
    TITAN: '#ff2244', SUPER: '#ff5500', DREAD: '#ff7744',
    CARRIER: '#ffaa44', FAX: '#ffdd00',
    BLOPS: '#cc44ff', RECON: '#aa55ff', BOMBER: '#8855dd',
    T3C: '#7755cc', COVOPS: '#6644aa',
}

function HeatmapBar({ heatmap, peakTz }) {
    const max = Math.max(...heatmap, 1)
    return (
        <div>
            <div style={{ display: 'flex', alignItems: 'flex-end', height: 22, gap: 1, marginBottom: 2 }}>
                {heatmap.map((val, h) => {
                    const pct = Math.max(3, (val / max) * 100)
                    return (
                        <div key={h} title={`${h.toString().padStart(2, '0')}:00 UTC — ${val} kills`} style={{
                            flex: 1, height: `${pct}%`,
                            background: val > 0 ? '#ff3355' : '#1a2530',
                            opacity: val > 0 ? 0.75 + (val / max) * 0.25 : 1,
                        }} />
                    )
                })}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 8, color: '#334455', marginBottom: 2 }}>
                <span>00</span><span>06</span><span>12</span><span>18</span><span>23</span>
            </div>
            {peakTz && (
                <div style={{ fontSize: 8, color: '#6a8090', fontFamily: 'Share Tech Mono, monospace' }}>
                    peak: {peakTz}
                </div>
            )}
        </div>
    )
}

function ShipBadge({ name, count }) {
    return (
        <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 3,
            background: 'rgba(0,212,255,0.07)', border: '1px solid rgba(0,212,255,0.15)',
            padding: '1px 6px', fontSize: 9,
            fontFamily: 'Share Tech Mono, monospace', color: 'var(--text-secondary)',
            whiteSpace: 'nowrap',
        }}>
            <span style={{ color: 'var(--cyan)', fontWeight: 700 }}>{count}×</span>
            {name}
        </span>
    )
}

function RoleBadge({ role }) {
    const color = ROLE_COLOR[role] ?? '#aaaaaa'
    return (
        <span style={{
            fontSize: 7, fontFamily: 'Orbitron, sans-serif', letterSpacing: 1, fontWeight: 700,
            color, border: `1px solid ${color}44`, padding: '0 3px', borderRadius: 2,
            whiteSpace: 'nowrap',
        }}>{role}</span>
    )
}

function PinnedCard({ n }) {
    const threatColor = THREAT_COLOR[n.threat_level] ?? '#6a8090'
    return (
        <div style={{
            background: 'rgba(0,0,0,0.3)',
            border: `1px solid ${n.threat_level === 'High' ? 'rgba(255,51,85,0.3)' : n.threat_level === 'Medium' ? 'rgba(255,170,0,0.2)' : 'var(--border-dim)'}`,
            padding: 10, display: 'flex', flexDirection: 'column', gap: 8,
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <img
                        src={`https://images.evetech.net/${n.type}s/${n.id}/logo?size=32`}
                        alt={n.name}
                        style={{ width: 32, height: 32, borderRadius: 3, flexShrink: 0 }}
                        onError={e => { e.target.style.display = 'none' }}
                    />
                    <div>
                        <div style={{ fontWeight: 700, color: 'var(--cyan)', fontSize: 11, fontFamily: 'Share Tech Mono, monospace' }}>{n.name}</div>
                        <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 1 }}>
                            {n.type.toUpperCase()} · {n.total_kills} kills · {n.isk_label} ISK
                        </div>
                    </div>
                </div>
                <div style={{
                    padding: '2px 7px', fontSize: 9, fontWeight: 700, letterSpacing: 1,
                    fontFamily: 'Orbitron, sans-serif',
                    background: `${threatColor}22`, border: `1px solid ${threatColor}66`,
                    color: threatColor, whiteSpace: 'nowrap', alignSelf: 'flex-start',
                }}>
                    {n.threat_level.toUpperCase()}
                </div>
            </div>

            {n.top_ships?.length > 0 && (
                <div>
                    <div style={{ fontSize: 8, fontFamily: 'Orbitron, sans-serif', letterSpacing: 2, color: 'var(--text-muted)', marginBottom: 4 }}>DOCTRINE</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {n.top_ships.map((s, i) => <ShipBadge key={i} name={s.name} count={s.count} />)}
                        {n.capital_roles?.map(r => <RoleBadge key={r} role={r} />)}
                    </div>
                </div>
            )}

            {n.activity_heatmap && (
                <div>
                    <div style={{ fontSize: 8, fontFamily: 'Orbitron, sans-serif', letterSpacing: 2, color: 'var(--text-muted)', marginBottom: 4 }}>ACTIVITY (UTC)</div>
                    <HeatmapBar heatmap={n.activity_heatmap} peakTz={n.peak_tz} />
                </div>
            )}

            {n.neighbor_regions?.length > 0 && (
                <div style={{ fontSize: 9, fontFamily: 'Share Tech Mono, monospace' }}>
                    <span style={{ color: 'var(--text-muted)', marginRight: 4 }}>NEAR LAWN:</span>
                    <span style={{ color: '#ffaa00' }}>{n.neighbor_regions.join(', ')}</span>
                </div>
            )}
        </div>
    )
}

function DetectedCard({ n }) {
    return (
        <div style={{
            background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-dim)',
            padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 5, opacity: 0.85,
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 10, fontFamily: 'Share Tech Mono, monospace', color: 'var(--text-secondary)' }}>{n.name}</span>
                <span style={{ fontSize: 9, color: '#ff6677', fontFamily: 'Share Tech Mono, monospace' }}>{n.kills_in_neighbor_space}k nearby</span>
            </div>
            {n.top_ships?.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                    {n.top_ships.map((s, i) => <ShipBadge key={i} name={s.name} count={s.count} />)}
                    {n.capital_roles?.map(r => <RoleBadge key={r} role={r} />)}
                </div>
            )}
        </div>
    )
}

export default function NeighborIntel({ lastUpdate }) {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        fetch('/api/intel/neighbors')
            .then(r => r.json())
            .then(d => { setData(d); setLoading(false) })
            .catch(() => setLoading(false))
    }, [lastUpdate])

    if (loading || !data) return null

    const pinned = data.pinned || []
    const detected = (data.detected || []).filter(d => d.kills_in_neighbor_space > 0)

    if (!pinned.length && !detected.length) return null

    const highCount = pinned.filter(n => n.threat_level === 'High').length

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">Neighbor Threat Profiling</span>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    {highCount > 0 && (
                        <span className="panel-badge" style={{ color: '#ff3355', borderColor: '#ff335566', background: 'rgba(255,51,85,0.1)' }}>
                            {highCount} HIGH
                        </span>
                    )}
                    <span className="panel-badge">24h · doctrine</span>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 8 }}>
                {pinned.map(n => <PinnedCard key={n.id} n={n} />)}
            </div>

            {detected.length > 0 && (
                <div style={{ marginTop: 10 }}>
                    <div style={{
                        fontSize: 8, fontFamily: 'Orbitron, sans-serif', letterSpacing: 2,
                        color: 'var(--text-muted)', marginBottom: 6,
                    }}>ACTIVE IN NEIGHBOR SPACE</div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 6 }}>
                        {detected.map(n => <DetectedCard key={n.id} n={n} />)}
                    </div>
                </div>
            )}
        </div>
    )
}

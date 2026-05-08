import React, { useState, useEffect } from 'react'

const THREAT_COLOR = {
    high:     'var(--red)',
    elevated: 'var(--amber)',
    quiet:    'var(--text-muted)',
}

const THREAT_LABEL = {
    high:     'HIGH',
    elevated: 'ELEVATED',
    quiet:    'QUIET',
}

export default function RegionalIntel({ lastUpdate }) {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [expanded, setExpanded] = useState({})

    useEffect(() => {
        setLoading(true)
        fetch('/api/intel/regional')
            .then(r => r.json())
            .then(d => { setData(d); setLoading(false) })
            .catch(() => setLoading(false))
    }, [lastUpdate])

    if (loading || !data) return null

    const regions = data.regions || []
    if (!regions.length) return null

    const activeRegions = regions.filter(r => r.threat !== 'quiet')
    const quietCount = regions.length - activeRegions.length
    const totalKills = regions.reduce((s, r) => s + r.total_kills, 0)

    const toggleRegion = (name) => setExpanded(e => ({ ...e, [name]: !e[name] }))

    return (
        <div className="panel panel-wide">
            <div className="panel-header">
                <span className="panel-title">Regional Activity</span>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    {activeRegions.length > 0 && (
                        <span className="panel-badge" style={{ color: activeRegions.some(r => r.threat === 'high') ? 'var(--red)' : 'var(--amber)' }}>
                            {activeRegions.length} ACTIVE
                        </span>
                    )}
                    <span className="panel-badge">{totalKills} kills / {quietCount} quiet</span>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 6 }}>
                {regions.map(region => {
                    const isExpanded = expanded[region.name]
                    const color = THREAT_COLOR[region.threat]
                    const activeSystems = region.systems.filter(s => s.ship_kills > 0 || s.jumps > 0)

                    return (
                        <div key={region.name} style={{
                            background: 'rgba(0,0,0,0.3)',
                            border: `1px solid ${region.threat === 'quiet' ? 'var(--border-dim)' : color}`,
                            padding: 8,
                            opacity: region.threat === 'quiet' ? 0.6 : 1,
                        }}>
                            {/* Region header row */}
                            <div
                                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: region.systems.length ? 'pointer' : 'default', marginBottom: activeSystems.length ? 6 : 0 }}
                                onClick={() => region.systems.length && toggleRegion(region.name)}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <span style={{ fontSize: 11, fontWeight: 'bold', color: region.threat === 'quiet' ? 'var(--text-muted)' : color, fontFamily: 'Orbitron, sans-serif' }}>
                                        {region.name}
                                    </span>
                                    {region.systems.length > 0 && (
                                        <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>
                                            {isExpanded ? '▲' : '▼'}
                                        </span>
                                    )}
                                </div>
                                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                                    {region.total_kills > 0 && (
                                        <span style={{ fontSize: 10, color: 'var(--red)' }}>
                                            {region.total_kills}k
                                        </span>
                                    )}
                                    {region.total_jumps > 0 && (
                                        <span style={{ fontSize: 10, color: 'var(--cyan)' }}>
                                            {region.total_jumps}j
                                        </span>
                                    )}
                                    <span style={{
                                        fontSize: 9, fontWeight: 'bold', padding: '1px 5px',
                                        background: color, color: region.threat === 'quiet' ? '#444' : '#000',
                                        fontFamily: 'Orbitron, sans-serif',
                                    }}>
                                        {THREAT_LABEL[region.threat]}
                                    </span>
                                </div>
                            </div>

                            {/* Per-system rows — show active systems always, rest behind expand */}
                            {(isExpanded ? region.systems : activeSystems).map(sys => (
                                <div key={sys.system_id} style={{
                                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                    padding: '2px 0', borderTop: '1px solid rgba(255,255,255,0.05)',
                                }}>
                                    <span style={{ fontSize: 10, color: THREAT_COLOR[sys.threat], fontFamily: 'Share Tech Mono, monospace' }}>
                                        {sys.name}
                                    </span>
                                    <div style={{ display: 'flex', gap: 8 }}>
                                        {sys.ship_kills > 0 && (
                                            <span style={{ fontSize: 9, color: 'var(--red)' }}>{sys.ship_kills}k</span>
                                        )}
                                        {sys.pod_kills > 0 && (
                                            <span style={{ fontSize: 9, color: '#ff6677' }}>{sys.pod_kills}p</span>
                                        )}
                                        {sys.jumps > 0 && (
                                            <span style={{ fontSize: 9, color: 'var(--cyan)' }}>{sys.jumps}j</span>
                                        )}
                                        {sys.ship_kills === 0 && sys.jumps === 0 && (
                                            <span style={{ fontSize: 9, color: 'var(--border-dim)' }}>—</span>
                                        )}
                                    </div>
                                </div>
                            ))}

                            {/* Show "X more quiet" when collapsed and there are inactive systems */}
                            {!isExpanded && activeSystems.length < region.systems.length && (
                                <div
                                    style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 4, cursor: 'pointer' }}
                                    onClick={() => toggleRegion(region.name)}
                                >
                                    +{region.systems.length - activeSystems.length} quiet
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

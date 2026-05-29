import React, { useState, useRef } from 'react'
import CornerBrackets from './common/CornerBrackets'

const RISK_COLOR = {
    very_dangerous: '#ff2244',
    dangerous:      '#ff3355',
    moderate:       '#ffaa00',
    snuggly:        '#00d4ff',
    newbie:         '#6a8090',
    nodata:         '#2a3a4a',
}

const RISK_ORDER = ['very_dangerous', 'dangerous', 'moderate', 'snuggly', 'newbie', 'nodata']

const ROLE_COLOR = {
    TITAN:   '#ff2244',
    SUPER:   '#ff5500',
    DREAD:   '#ff7744',
    CARRIER: '#ffaa44',
    FAX:     '#ffdd00',
    BLOPS:   '#cc44ff',
    RECON:   '#aa55ff',
    BOMBER:  '#8855dd',
    T3C:     '#7755cc',
    COVOPS:  '#6644aa',
}

const FLEET_ROLE_COLOR = {
    LOGI:    '#00ff88',
    DICTOR:  '#00d4ff',
    HIC:     '#44aaff',
    BOOSTER: '#ffcc44',
    BS:      '#ff7744',
    BC:      '#ff9944',
    HAC:     '#ffbb44',
    T3C:     '#7755cc',
    CRUISER: '#8a9aa0',
    FRIG:    '#6a8090',
    DESTROYER: '#6a8090',
}

const STANDING_CONFIG = {
    unknown:    { color: '#ff9966' },
    friendly:   { color: '#00d4ff' },
    lawn:       { color: '#00ff88' },
    unresolved: { color: '#ffaa00' },
}

const CAPITAL_ROLES = new Set(['TITAN', 'SUPER', 'DREAD', 'CARRIER', 'FAX'])

function parseNames(raw) {
    if (!raw.trim()) return []
    const names = raw.includes('\n')
        ? raw.split('\n').map(s => s.trim()).filter(Boolean)
        : raw.split(/[\s,]+/).map(s => s.trim()).filter(Boolean)
    return [...new Set(names)]
}

function RoleBadge({ role, count, colorMap }) {
    const color = colorMap[role] ?? '#8a9aa0'
    return (
        <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 3,
            background: `${color}18`, border: `1px solid ${color}55`,
            color, fontFamily: 'Orbitron, sans-serif', fontSize: 8,
            fontWeight: 700, letterSpacing: 1, padding: '1px 5px', borderRadius: 2,
            whiteSpace: 'nowrap',
        }}>
            {role}{count > 1 && <span style={{ color: `${color}cc`, fontSize: 8 }}>×{count}</span>}
        </span>
    )
}

function ThreatBar({ distribution, total }) {
    if (!total) return null
    return (
        <div style={{ display: 'flex', height: 8, borderRadius: 2, overflow: 'hidden', gap: 1 }}>
            {RISK_ORDER.filter(t => distribution[t]).map(tier => (
                <div
                    key={tier}
                    title={`${tier.replace('_', ' ')}: ${distribution[tier]}`}
                    style={{
                        flex: distribution[tier] / total,
                        background: RISK_COLOR[tier],
                        minWidth: 2,
                    }}
                />
            ))}
        </div>
    )
}

export default function FleetCompAnalyzer() {
    const [rawInput, setRawInput] = useState('')
    const [result, setResult] = useState(null)
    const [scanning, setScanning] = useState(false)
    const [error, setError] = useState(null)
    const [showPilots, setShowPilots] = useState(false)

    const names = parseNames(rawInput)

    async function handleAnalyze() {
        if (!names.length) return
        setScanning(true)
        setError(null)
        setShowPilots(false)
        try {
            const resp = await fetch('/api/fleet/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ names }),
            })
            if (!resp.ok) throw new Error(`Server error: ${resp.status}`)
            setResult(await resp.json())
        } catch (e) {
            setError(e.message)
        } finally {
            setScanning(false)
        }
    }

    function handleClear() {
        setRawInput('')
        setResult(null)
        setError(null)
        setShowPilots(false)
    }

    const s = result?.summary
    const pilots = result?.pilots || []

    // Determine threat color from avg danger
    const threatColor = !s ? '#6a8090'
        : s.avg_danger >= 70 ? '#ff3355'
        : s.avg_danger >= 45 ? '#ffaa00'
        : '#00d4ff'

    const capitalRoles = Object.entries(s?.role_counts || {}).filter(([r]) => CAPITAL_ROLES.has(r))
    const specialRoles = Object.entries(s?.role_counts || {}).filter(([r]) => !CAPITAL_ROLES.has(r))
    const fleetRoles = Object.entries(s?.fleet_role_counts || {})

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">FLEET COMP ANALYZER</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {s && (
                        <span className="panel-badge">
                            <span style={{ color: STANDING_CONFIG.unknown.color }}>{s.unknown} hostile</span>
                            {s.friendly > 0 && <span style={{ color: 'var(--text-muted)' }}> · <span style={{ color: STANDING_CONFIG.friendly.color }}>{s.friendly} friendly</span></span>}
                            {s.lawn > 0 && <span style={{ color: 'var(--text-muted)' }}> · <span style={{ color: STANDING_CONFIG.lawn.color }}>{s.lawn} lawn</span></span>}
                            {s.capitals > 0 && <span style={{ color: 'var(--text-muted)' }}> · <span style={{ color: '#ff7744' }}>{s.capitals} caps</span></span>}
                        </span>
                    )}
                    {(rawInput || result) && (
                        <button onClick={handleClear} style={{
                            background: 'none', border: '1px solid var(--border-dim)',
                            color: 'var(--text-secondary)', cursor: 'pointer',
                            fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                            padding: '2px 8px', letterSpacing: 1,
                        }}>CLEAR</button>
                    )}
                </div>
            </div>

            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <textarea
                    value={rawInput}
                    onChange={e => setRawInput(e.target.value)}
                    placeholder="Paste pilot names from local or fleet window (one per line)..."
                    style={{
                        flex: 1, minHeight: 72, background: 'rgba(0,0,0,0.3)',
                        border: '1px solid var(--border-dim)', color: 'var(--text-primary)',
                        fontFamily: 'Share Tech Mono, monospace', fontSize: 11,
                        padding: '8px 10px', resize: 'vertical', outline: 'none',
                    }}
                />
                <button
                    onClick={handleAnalyze}
                    disabled={!names.length || scanning}
                    style={{
                        background: names.length && !scanning ? 'rgba(255,51,85,0.1)' : 'rgba(0,0,0,0.2)',
                        border: `1px solid ${names.length && !scanning ? '#ff3355' : 'var(--border-dim)'}`,
                        color: names.length && !scanning ? '#ff3355' : 'var(--text-muted)',
                        cursor: names.length && !scanning ? 'pointer' : 'default',
                        fontFamily: 'Orbitron, sans-serif', fontSize: 10,
                        fontWeight: 600, letterSpacing: 2,
                        padding: '0 16px', height: 72, whiteSpace: 'nowrap',
                        transition: 'all 0.2s',
                    }}
                >
                    {scanning ? 'ANALYZING...' : 'ANALYZE\nFLEET'}
                </button>
            </div>

            {error && (
                <div style={{
                    marginTop: 8, padding: '6px 10px',
                    background: 'rgba(255,51,85,0.1)', border: '1px solid var(--red)',
                    fontFamily: 'Share Tech Mono, monospace', fontSize: 11, color: 'var(--red)',
                }}>ERROR: {error}</div>
            )}

            {s && (
                <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>

                    {/* Threat overview row */}
                    <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 60 }}>
                            <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 18, fontWeight: 700, color: threatColor, lineHeight: 1 }}>{s.avg_danger}%</span>
                            <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-muted)' }}>AVG DANGER</span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 60 }}>
                            <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1 }}>
                                {s.avg_kills >= 1000 ? `${(s.avg_kills/1000).toFixed(1)}k` : s.avg_kills}
                            </span>
                            <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-muted)' }}>AVG KILLS</span>
                        </div>
                        {s.capitals > 0 && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 50 }}>
                                <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 18, fontWeight: 700, color: '#ff7744', lineHeight: 1 }}>{s.capitals}</span>
                                <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-muted)' }}>CAPITALS</span>
                            </div>
                        )}
                        <div style={{ flex: 1, minWidth: 120 }}>
                            <ThreatBar distribution={s.risk_distribution} total={s.unknown + s.friendly + s.lawn} />
                            <div style={{ display: 'flex', gap: 6, marginTop: 3, flexWrap: 'wrap' }}>
                                {RISK_ORDER.filter(t => s.risk_distribution[t]).map(t => (
                                    <span key={t} style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 8, color: RISK_COLOR[t] }}>
                                        {t.replace('_', ' ')} ×{s.risk_distribution[t]}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Capital warning */}
                    {capitalRoles.length > 0 && (
                        <div style={{
                            padding: '5px 10px', background: 'rgba(255,119,68,0.12)',
                            border: '1px solid #ff774466', display: 'flex', alignItems: 'center', gap: 8,
                        }}>
                            <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 9, color: '#ff7744', fontWeight: 700, letterSpacing: 2 }}>CAPITAL ASSETS</span>
                            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                                {capitalRoles.map(([role, count]) => (
                                    <RoleBadge key={role} role={role} count={count} colorMap={ROLE_COLOR} />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Fleet roles row */}
                    {(specialRoles.length > 0 || fleetRoles.length > 0) && (
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                            <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 8, color: 'var(--text-muted)', letterSpacing: 1, marginRight: 2 }}>ROLES</span>
                            {specialRoles.map(([role, count]) => (
                                <RoleBadge key={role} role={role} count={count} colorMap={ROLE_COLOR} />
                            ))}
                            {fleetRoles.map(([role, count]) => (
                                <RoleBadge key={role} role={role} count={count} colorMap={FLEET_ROLE_COLOR} />
                            ))}
                        </div>
                    )}

                    {/* Alliance breakdown */}
                    {s.top_alliances.length > 0 && (
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                            <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 8, color: 'var(--text-muted)', letterSpacing: 1, marginRight: 2 }}>ALLIANCES</span>
                            {s.top_alliances.map(({ name, count }) => (
                                <span key={name} style={{
                                    fontFamily: 'Share Tech Mono, monospace', fontSize: 9,
                                    color: '#ff9966', background: 'rgba(255,153,102,0.08)',
                                    border: '1px solid rgba(255,153,102,0.25)',
                                    padding: '1px 6px', borderRadius: 2, whiteSpace: 'nowrap',
                                }}>
                                    {name} <span style={{ color: 'var(--text-muted)' }}>×{count}</span>
                                </span>
                            ))}
                        </div>
                    )}

                    {/* Pilot table toggle */}
                    <div>
                        <button
                            onClick={() => setShowPilots(v => !v)}
                            style={{
                                background: 'none', border: '1px solid var(--border-dim)',
                                color: 'var(--text-secondary)', cursor: 'pointer',
                                fontFamily: 'Orbitron, sans-serif', fontSize: 9,
                                padding: '3px 10px', letterSpacing: 1,
                            }}
                        >
                            {showPilots ? 'HIDE' : 'SHOW'} PILOTS ({pilots.length})
                        </button>
                    </div>

                    {showPilots && (
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--border-dim)' }}>
                                    {['PILOT', 'CORP / ALLIANCE', 'RISK', 'ROLES'].map(h => (
                                        <th key={h} style={{ padding: '4px 8px', textAlign: 'left', fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 2, color: 'var(--text-muted)', fontWeight: 500 }}>{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {pilots.map((p, i) => {
                                    const sc = STANDING_CONFIG[p.standing] || STANDING_CONFIG.unknown
                                    const rc = RISK_COLOR[p.risk_tier] ?? '#334455'
                                    return (
                                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)' }}>
                                            <td style={{ padding: '4px 8px', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                                                {p.character_id ? (
                                                    <a href={`https://zkillboard.com/character/${p.character_id}/`} target="_blank" rel="noopener noreferrer"
                                                        style={{ color: sc.color, textDecoration: 'none' }}>{p.name}</a>
                                                ) : <span style={{ color: sc.color }}>{p.name}</span>}
                                            </td>
                                            <td style={{ padding: '4px 8px', fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: 'var(--text-secondary)' }}>
                                                {p.corporation_name || ''}
                                                {p.corporation_name && p.alliance_name && <span style={{ color: 'var(--text-muted)' }}> · </span>}
                                                {p.alliance_name && <span style={{ color: p.standing === 'unknown' ? '#ff9966' : 'var(--text-secondary)' }}>{p.alliance_name}</span>}
                                                {!p.corporation_name && !p.alliance_name && <span style={{ color: 'var(--text-muted)' }}>—</span>}
                                            </td>
                                            <td style={{ padding: '4px 8px', whiteSpace: 'nowrap' }}>
                                                <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 9, fontWeight: 700, color: rc, letterSpacing: 1 }}>{p.risk_label}</span>
                                                {p.risk_tier !== 'nodata' && p.risk_tier !== 'newbie' && (
                                                    <div style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 8, color: '#6a8090' }}>
                                                        {p.kills >= 1000 ? `${(p.kills/1000).toFixed(1)}k` : p.kills} kills · {p.danger}% danger
                                                    </div>
                                                )}
                                            </td>
                                            <td style={{ padding: '4px 8px' }}>
                                                <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                                                    {p.roles.map(r => <RoleBadge key={r} role={r} count={0} colorMap={ROLE_COLOR} />)}
                                                    {p.fleet_roles.map(r => <RoleBadge key={r} role={r} count={0} colorMap={FLEET_ROLE_COLOR} />)}
                                                </div>
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    )}
                </div>
            )}
        </div>
    )
}

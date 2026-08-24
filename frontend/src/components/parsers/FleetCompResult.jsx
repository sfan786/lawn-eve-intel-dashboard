import React, { useState } from 'react'
import {
    CAPITAL_ROLES, FLEET_ROLE_COLOR, FLEET_STANDING_COLOR, formatKills,
    RISK_COLOR, RISK_ORDER, ROLE_COLOR,
} from '../../utils/intelStyles'

export function RoleBadge({ role, count, colorMap }) {
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

export function ThreatBar({ distribution, total }) {
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

/** Standings/caps breakdown as it appears in the panel header, live or shared. */
export function FleetCounts({ summary: s }) {
    if (!s) return null
    return (
        <>
            <span style={{ color: FLEET_STANDING_COLOR.unknown.color }}>{s.unknown} hostile</span>
            {s.friendly > 0 && <span style={{ color: 'var(--text-muted)' }}> · <span style={{ color: FLEET_STANDING_COLOR.friendly.color }}>{s.friendly} friendly</span></span>}
            {s.lawn > 0 && <span style={{ color: 'var(--text-muted)' }}> · <span style={{ color: FLEET_STANDING_COLOR.lawn.color }}>{s.lawn} lawn</span></span>}
            {s.capitals > 0 && <span style={{ color: 'var(--text-muted)' }}> · <span style={{ color: '#ff7744' }}>{s.capitals} caps</span></span>}
        </>
    )
}

/**
 * Presentational half of the Fleet Comp Analyzer.
 *
 * `result` is the {pilots, summary} body from POST /api/fleet/analyze, either
 * freshly fetched or replayed from a share. The show/hide pilot table is local
 * UI state and stays here — it is a view preference, not part of the snapshot.
 */
export default function FleetCompResult({ result }) {
    const [showPilots, setShowPilots] = useState(false)

    const s = result?.summary
    const pilots = result?.pilots || []
    if (!s) return null

    // Determine threat color from avg danger
    const threatColor = s.avg_danger >= 70 ? '#ff3355'
        : s.avg_danger >= 45 ? '#ffaa00'
        : '#00d4ff'

    const capitalRoles = Object.entries(s.role_counts || {}).filter(([r]) => CAPITAL_ROLES.has(r))
    const specialRoles = Object.entries(s.role_counts || {}).filter(([r]) => !CAPITAL_ROLES.has(r))
    const fleetRoles = Object.entries(s.fleet_role_counts || {})

    return (
        <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>

            {/* Threat overview row */}
            <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 60 }}>
                    <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 18, fontWeight: 700, color: threatColor, lineHeight: 1 }}>{s.avg_danger}%</span>
                    <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-muted)' }}>AVG DANGER</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 60 }}>
                    <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1 }}>
                        {formatKills(s.avg_kills)}
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
                            const sc = FLEET_STANDING_COLOR[p.standing] || FLEET_STANDING_COLOR.unknown
                            const rc = RISK_COLOR[p.risk_tier] ?? '#334455'
                            return (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)' }}>
                                    <td style={{ padding: '4px 8px', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                                        {p.character_id ? (
                                            <a href={`https://zkillboard.com/character/${Number(p.character_id)}/`} target="_blank" rel="noopener noreferrer"
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
                                                {formatKills(p.kills)} kills · {p.danger}% danger
                                            </div>
                                        )}
                                    </td>
                                    <td style={{ padding: '4px 8px' }}>
                                        <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                                            {(p.roles || []).map(r => <RoleBadge key={r} role={r} count={0} colorMap={ROLE_COLOR} />)}
                                            {(p.fleet_roles || []).map(r => <RoleBadge key={r} role={r} count={0} colorMap={FLEET_ROLE_COLOR} />)}
                                        </div>
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            )}
        </div>
    )
}

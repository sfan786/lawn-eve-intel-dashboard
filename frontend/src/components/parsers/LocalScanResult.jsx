import React from 'react'
import { formatKills, RISK_COLOR, ROLE_COLOR, STANDING_CONFIG } from '../../utils/intelStyles'

const TH = {
    padding: '4px 8px', fontFamily: 'Orbitron, sans-serif', fontSize: 9,
    letterSpacing: 2, color: 'var(--text-muted)', fontWeight: 500,
}

/** Risk tier + role badges + stat line for one pilot, or an em dash if unrated. */
function RiskCell({ risk }) {
    if (!risk) {
        return <span style={{ color: '#334455', fontFamily: 'Share Tech Mono, monospace', fontSize: 9 }}>—</span>
    }
    const rc = RISK_COLOR[risk.tier] ?? '#334455'
    const kills = formatKills(risk.kills)
    const roles = risk.roles || []
    return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 9, fontWeight: 700, letterSpacing: 1, color: rc }}>{risk.label}</span>
                {roles.map(role => (
                    <span key={role} style={{
                        fontFamily: 'Orbitron, sans-serif', fontSize: 7, fontWeight: 700,
                        letterSpacing: 1, color: ROLE_COLOR[role] ?? '#aaaaaa',
                        border: `1px solid ${ROLE_COLOR[role] ?? '#aaaaaa'}44`,
                        padding: '0 3px', borderRadius: 2,
                    }}>{role}</span>
                ))}
            </div>
            {risk.tier !== 'nodata' && risk.tier !== 'newbie' && (
                <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 8, color: '#6a8090' }}>
                    {kills} kills · {risk.isk_eff}% eff · {risk.danger}% danger
                </span>
            )}
            {risk.tier === 'newbie' && (
                <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 8, color: '#6a8090' }}>{kills} kills</span>
            )}
        </div>
    )
}

/** Pilots per standing, for the panel-header badge. */
export function localCounts(results) {
    if (!results) return null
    return {
        unknown: results.filter(r => r.standing === 'unknown').length,
        friendly: results.filter(r => r.standing === 'friendly').length,
        lawn: results.filter(r => r.standing === 'lawn').length,
        unresolved: results.filter(r => r.standing === 'unresolved').length,
    }
}

/** The standing breakdown as it appears in the panel header, live or shared. */
export function StandingCounts({ counts }) {
    if (!counts) return null
    return (
        <>
            {counts.unknown > 0 && <span style={{ color: STANDING_CONFIG.unknown.color }}>{counts.unknown} unknown</span>}
            {counts.unknown > 0 && (counts.friendly > 0 || counts.lawn > 0) && <span style={{ color: 'var(--text-muted)' }}> · </span>}
            {counts.friendly > 0 && <span style={{ color: STANDING_CONFIG.friendly.color }}>{counts.friendly} friendly</span>}
            {counts.friendly > 0 && counts.lawn > 0 && <span style={{ color: 'var(--text-muted)' }}> · </span>}
            {counts.lawn > 0 && <span style={{ color: STANDING_CONFIG.lawn.color }}>{counts.lawn} lawn</span>}
            {counts.unresolved > 0 && <span style={{ color: 'var(--text-muted)' }}> · </span>}
            {counts.unresolved > 0 && <span style={{ color: STANDING_CONFIG.unresolved.color }}>{counts.unresolved} unresolved</span>}
        </>
    )
}

/**
 * Presentational half of the Local Scanner: the resolved pilot table.
 * Rendered both live and from a frozen share, so it takes results as data and
 * does no fetching of its own.
 */
export default function LocalScanResult({ results, riskMap = {} }) {
    if (!results) return null

    if (results.length === 0) {
        return (
            <div style={{ padding: '8px 0', color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                No pilots resolved.
            </div>
        )
    }

    return (
        <div style={{ marginTop: 10 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-dim)' }}>
                        <th style={{ ...TH, textAlign: 'left' }}>PILOT</th>
                        <th style={{ ...TH, textAlign: 'left' }}>CORP / ALLIANCE</th>
                        <th style={{ ...TH, textAlign: 'right' }}>STANDING</th>
                        <th style={{ ...TH, textAlign: 'right' }}>RISK</th>
                    </tr>
                </thead>
                <tbody>
                    {results.map((r, i) => {
                        const cfg = STANDING_CONFIG[r.standing] || STANDING_CONFIG.unknown
                        return (
                            <tr key={i} style={{ borderBottom: '1px solid var(--border-dim)', background: cfg.bg }}>
                                <td style={{ padding: '5px 8px', fontFamily: 'Share Tech Mono, monospace', fontSize: 11, color: 'var(--text-primary)' }}>
                                    {r.character_id ? (
                                        <a
                                            href={`https://zkillboard.com/character/${Number(r.character_id)}/`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            style={{ color: cfg.color, textDecoration: 'none' }}
                                        >
                                            {r.name}
                                        </a>
                                    ) : r.name}
                                </td>
                                <td style={{ padding: '5px 8px', fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: 'var(--text-secondary)' }}>
                                    {r.corporation_name && <span>{r.corporation_name}</span>}
                                    {r.corporation_name && r.alliance_name && <span style={{ color: 'var(--text-muted)' }}> · </span>}
                                    {r.alliance_name && <span style={{ color: r.standing === 'unknown' ? '#ff9966' : 'var(--text-secondary)' }}>{r.alliance_name}</span>}
                                    {!r.corporation_name && !r.alliance_name && (
                                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                                    )}
                                </td>
                                <td style={{ padding: '5px 8px', textAlign: 'right' }}>
                                    <span style={{
                                        fontFamily: 'Orbitron, sans-serif', fontSize: 9,
                                        fontWeight: 600, letterSpacing: 2, color: cfg.color,
                                    }}>{cfg.label}</span>
                                </td>
                                <td style={{ padding: '5px 8px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                                    <RiskCell risk={r.character_id ? riskMap[String(r.character_id)] : null} />
                                </td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}

import React, { useState } from 'react'
import { formatIsk, timeAgo } from '../utils/formatters'
import CornerBrackets from './common/CornerBrackets'

export default function KillFeed({ kills, config }) {
    const [filter, setFilter] = useState("all")  // "all" | "primary" | "pvp"
    const [minIsk, setMinIsk] = useState(0)
    const [expandedKillId, setExpandedKillId] = useState(null)

    const allianceName = config?.alliance?.name || ""
    const allianceShort = config?.alliance?.short_name || config?.alliance?.ticker || "PRIMARY"
    const inPrimary = (k) => k.in_primary ?? k.in_lawn

    const visible = (kills || []).filter(k => {
        if (minIsk > 0 && (k.total_value || 0) < minIsk) return false
        if (filter === "primary") return inPrimary(k) && !k.is_npc
        if (filter === "pvp") return !k.is_npc
        return true
    })

    // Stats always computed from full kill set
    const allKills = kills || []
    const { primaryPvpKills, iskKilled, ourLosses, iskLost } = allKills.reduce((acc, k) => {
        const isNpc = k.is_npc
        if (!isNpc) {
            if (inPrimary(k)) {
                acc.primaryPvpKills.push(k)
                acc.iskKilled += (k.total_value || 0)
            }
            if (allianceName && k.victim?.alliance_name === allianceName) {
                acc.ourLosses.push(k)
                acc.iskLost += (k.total_value || 0)
            }
        }
        return acc
    }, { primaryPvpKills: [], iskKilled: 0, ourLosses: [], iskLost: 0 })

    const roamers = {}
    primaryPvpKills.forEach(k => {
        const fb = k.final_blow
        if (!fb) return
        const a = fb.alliance_name || fb.corporation_name
        if (a && a !== allianceName) roamers[a] = (roamers[a] || 0) + 1
    })

    const repeatPilots = {}
    allKills.forEach(k => {
        if (k.is_npc) return
        const fb = k.final_blow
        if (!fb) return
        const char = fb.character_name
        const a = fb.alliance_name || fb.corporation_name
        if (char && a !== allianceName) {
            repeatPilots[char] = (repeatPilots[char] || 0) + 1
        }
    })
    const topRoamers = Object.entries(roamers).sort((a, b) => b[1] - a[1]).slice(0, 3)

    const primaryKillsCount = visible.filter(k => inPrimary(k)).length

    let subcapCount = 0
    let capCount = 0
    let superCount = 0

    for (const kill of visible) {
        if (!kill.is_npc) {
            const sc = kill.victim?.ship_class
            if (sc === 'subcap') subcapCount++
            else if (sc === 'capital') capCount++
            else if (sc === 'super') superCount++
        }
    }

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">Kill Feed</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div className="map-mode-toggle">
                        <button className={`map-mode-btn ${minIsk === 0 ? 'active' : ''}`} onClick={() => setMinIsk(0)}>All ISK</button>
                        <button className={`map-mode-btn ${minIsk === 100000000 ? 'active' : ''}`} onClick={() => setMinIsk(100000000)}>&gt;100M</button>
                        <button className={`map-mode-btn ${minIsk === 1000000000 ? 'active' : ''}`} onClick={() => setMinIsk(1000000000)}>&gt;1B</button>
                    </div>
                    <div className="map-mode-toggle">
                        <button className={`map-mode-btn ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>All</button>
                        <button className={`map-mode-btn ${filter === 'primary' ? 'active' : ''}`} onClick={() => setFilter('primary')}>{allianceShort}</button>
                        <button className={`map-mode-btn ${filter === 'pvp' ? 'active' : ''}`} onClick={() => setFilter('pvp')}>PVP</button>
                    </div>
                    <span className="panel-badge">
                        {visible.length} kills{primaryKillsCount > 0 ? ` — ${primaryKillsCount} in ${allianceShort}` : ''}
                    </span>
                </div>
            </div>
            {allKills.length > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 8px', background: 'rgba(0,0,0,0.2)', borderBottom: '1px solid var(--border-dim)', fontSize: 10, fontFamily: 'Share Tech Mono, monospace' }}>
                    <div>
                        {primaryPvpKills.length > 0 ? (
                            <>
                                <span style={{ color: 'var(--green)' }}>↑ {formatIsk(iskKilled)} killed</span>
                                <span style={{ color: 'var(--text-muted)' }}> · </span>
                                <span style={{ color: 'var(--red)' }}>↓ {formatIsk(iskLost)} lost</span>
                            </>
                        ) : (
                            <span style={{ color: 'var(--text-muted)' }}>No {allianceShort} PVP kills</span>
                        )}
                    </div>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                        {topRoamers.length > 0 && (
                            <span style={{ color: 'var(--text-muted)' }}>
                                Roaming: {topRoamers.map(([name, count]) => `${name} (${count})`).join(', ')}
                            </span>
                        )}
                        <span style={{ color: 'var(--text-muted)', borderLeft: '1px solid var(--border-dim)', paddingLeft: 10 }}>
                            Sub: <span style={{ color: subcapCount > 0 ? 'var(--text)' : 'var(--text-muted)' }}>{subcapCount}</span>
                            <span style={{ margin: '0 4px', color: 'var(--border-dim)' }}>·</span>
                            Cap: <span style={{ color: capCount > 0 ? 'var(--amber)' : 'var(--text-muted)' }}>{capCount}</span>
                            <span style={{ margin: '0 4px', color: 'var(--border-dim)' }}>·</span>
                            Super: <span style={{ color: superCount > 0 ? 'var(--red)' : 'var(--text-muted)' }}>{superCount}</span>
                        </span>
                    </div>
                </div>
            )}
            <div className="kill-feed">
                {visible.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: 10, color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                        {allKills.length === 0 ? 'No recent kills in region' : 'No kills match current filter'}
                    </div>
                ) : visible.map(kill => {
                    const iskClass = kill.total_value >= 1e9 ? "high" : kill.total_value >= 100e6 ? "medium" : "low"
                    const victim = kill.victim || {}
                    const fb = kill.final_blow || {}
                    const isExpanded = kill.killmail_id === expandedKillId

                    return (
                        <div key={kill.killmail_id}>
                            <div
                                className={`kill-entry${inPrimary(kill) ? ' in-lawn' : ''}`}
                                style={{ cursor: 'pointer' }}
                                onClick={() => setExpandedKillId(isExpanded ? null : kill.killmail_id)}
                            >
                                <div className="kill-time">
                                    <div>{timeAgo(kill.time)} ago</div>
                                    <div className={`kill-system ${inPrimary(kill) ? 'lawn' : 'region'}`}>{kill.system_name}</div>
                                </div>
                                <div className="kill-details">
                                    <div className="kill-ship">
                                        {victim.ship_type || "Unknown Ship"}
                                        {kill.is_npc && <span className="kill-npc-tag">NPC</span>}
                                        {victim.ship_class === 'capital' && <span style={{ color: 'var(--amber)', fontSize: 9, marginLeft: 6, padding: '0 4px', border: '1px solid var(--amber)', borderRadius: 2, background: 'rgba(255,170,0,0.1)' }}>CAP</span>}
                                        {victim.ship_class === 'super' && <span style={{ color: 'var(--red)', fontSize: 9, marginLeft: 6, padding: '0 4px', border: '1px solid var(--red)', borderRadius: 2, background: 'rgba(255,51,85,0.15)' }}>SUPER</span>}
                                    </div>
                                    <div className="kill-parties">
                                        <span style={{ color: 'var(--red)' }}>{victim.character_name || victim.corporation_name || "Unknown"}</span>
                                        {victim.alliance_name && <span style={{ color: 'var(--text-muted)' }}> [{victim.alliance_name}]</span>}
                                        <span style={{ color: 'var(--text-muted)' }}> killed by </span>
                                        <span style={{ color: 'var(--green)' }}>{fb.character_name || fb.corporation_name || "Unknown"}</span>
                                        {fb.character_name && repeatPilots[fb.character_name] > 1 && (
                                            <span style={{ color: 'var(--amber)', fontSize: 9, marginLeft: 6, padding: '0 4px', border: '1px solid var(--amber)', borderRadius: 2, background: 'rgba(255, 170, 0, 0.1)' }} title={`${repeatPilots[fb.character_name]} kills recently`}>REPEAT OFFENDER</span>
                                        )}
                                        {kill.attacker_count > 1 && <span style={{ color: 'var(--text-muted)' }}> +{kill.attacker_count - 1}</span>}
                                    </div>
                                </div>
                                <div className={`kill-value ${iskClass}`}>{formatIsk(kill.total_value)}</div>
                            </div>
                            {isExpanded && (
                                <div style={{
                                    background: 'rgba(0,212,255,0.03)',
                                    border: '1px solid rgba(0,212,255,0.15)',
                                    borderTop: 'none',
                                    padding: '7px 12px',
                                    fontFamily: 'Share Tech Mono, monospace',
                                    fontSize: 11,
                                }}>
                                    <div style={{ display: 'flex', gap: 16, marginBottom: 5 }}>
                                        <span style={{ color: 'var(--text-muted)' }}>
                                            Total: <span style={{ color: 'var(--text)' }}>{formatIsk(kill.total_value)}</span>
                                        </span>
                                        {(kill.fitted_value || 0) > 0 && (
                                            <span style={{ color: 'var(--text-muted)' }}>
                                                Fitted: <span style={{ color: 'var(--cyan)' }}>{formatIsk(kill.fitted_value)}</span>
                                            </span>
                                        )}
                                    </div>
                                    {kill.top_attackers && kill.top_attackers.length > 0 && (
                                        <div style={{ marginBottom: 5 }}>
                                            <div style={{ color: 'var(--text-muted)', marginBottom: 3 }}>
                                                Attackers ({kill.attacker_count}):
                                            </div>
                                            {kill.top_attackers.map((att, i) => (
                                                <div key={i} style={{ display: 'flex', gap: 8, padding: '1px 0', alignItems: 'center' }}>
                                                    <span style={{ color: 'var(--green)', minWidth: 130, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                        {att.character_name || 'Unknown'}
                                                    </span>
                                                    <span style={{ color: 'var(--text-muted)', minWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                        {att.ship_type || ''}
                                                    </span>
                                                    <span style={{ color: '#6a8090' }}>
                                                        {att.damage_done.toLocaleString()} dmg
                                                    </span>
                                                    {att.is_final_blow && (
                                                        <span style={{ color: 'var(--amber)', fontSize: 9, padding: '0 4px', border: '1px solid var(--amber)', borderRadius: 2, background: 'rgba(255,170,0,0.1)', flexShrink: 0 }}>FINAL BLOW</span>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    <div style={{ textAlign: 'right' }}>
                                        <a
                                            href={`https://zkillboard.com/kill/${kill.killmail_id}/`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            style={{ color: 'var(--cyan)', fontSize: 11, textDecoration: 'none' }}
                                            onClick={e => e.stopPropagation()}
                                        >
                                            View on zKillboard →
                                        </a>
                                    </div>
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

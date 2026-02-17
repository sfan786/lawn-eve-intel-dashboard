import React, { useState } from 'react'
import { formatIsk, timeAgo } from '../utils/formatters'
import CornerBrackets from './common/CornerBrackets'

export default function KillFeed({ kills }) {
    const [filter, setFilter] = useState("all")  // "all" | "lawn" | "pvp"

    if (!kills || kills.length === 0) {
        return (
            <div className="panel panel-wide">
                <CornerBrackets />
                <div className="panel-header">
                    <span className="panel-title">Kill Feed</span>
                    <span className="panel-badge">Kalevala Expanse</span>
                </div>
                <div style={{ textAlign: 'center', padding: 10, color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                    No recent kills in region
                </div>
            </div>
        )
    }

    const visible = kills.filter(k => {
        if (filter === "lawn") return k.in_lawn && !k.is_npc
        if (filter === "pvp")  return !k.is_npc
        return true
    })

    // Stats always computed from full kill set
    const lawnPvpKills = kills.filter(k => k.in_lawn && !k.is_npc)
    const iskKilled    = lawnPvpKills.reduce((s, k) => s + (k.total_value || 0), 0)
    const lawnLosses   = kills.filter(k => (k.victim?.alliance_name === "Get Off My Lawn") && !k.is_npc)
    const iskLost      = lawnLosses.reduce((s, k) => s + (k.total_value || 0), 0)

    const roamers = {}
    lawnPvpKills.forEach(k => {
        const a = k.final_blow?.alliance_name || k.final_blow?.corporation_name
        if (a && a !== "Get Off My Lawn") roamers[a] = (roamers[a] || 0) + 1
    })
    const topRoamers = Object.entries(roamers).sort((a, b) => b[1] - a[1]).slice(0, 3)

    const lawnKills = kills.filter(k => k.in_lawn).length

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">Kill Feed</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div className="map-mode-toggle">
                        <button className={`map-mode-btn ${filter === 'all'  ? 'active' : ''}`} onClick={() => setFilter('all')}>All</button>
                        <button className={`map-mode-btn ${filter === 'lawn' ? 'active' : ''}`} onClick={() => setFilter('lawn')}>LAWN</button>
                        <button className={`map-mode-btn ${filter === 'pvp'  ? 'active' : ''}`} onClick={() => setFilter('pvp')}>PVP</button>
                    </div>
                    <span className="panel-badge">
                        {visible.length} kills{lawnKills > 0 ? ` — ${lawnKills} in LAWN` : ''}
                    </span>
                </div>
            </div>
            {lawnPvpKills.length > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 8px', background: 'rgba(0,0,0,0.2)', borderBottom: '1px solid var(--border-dim)', fontSize: 10, fontFamily: 'Share Tech Mono, monospace' }}>
                    <div>
                        <span style={{ color: 'var(--green)' }}>↑ {formatIsk(iskKilled)} killed</span>
                        <span style={{ color: 'var(--text-muted)' }}> · </span>
                        <span style={{ color: 'var(--red)' }}>↓ {formatIsk(iskLost)} lost</span>
                    </div>
                    {topRoamers.length > 0 && (
                        <div style={{ color: 'var(--text-muted)' }}>
                            Roaming: {topRoamers.map(([name, count]) => `${name} (${count})`).join(', ')}
                        </div>
                    )}
                </div>
            )}
            <div className="kill-feed">
                {visible.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: 10, color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                        No kills match current filter
                    </div>
                ) : visible.map(kill => {
                    const iskClass = kill.total_value >= 1e9 ? "high" : kill.total_value >= 100e6 ? "medium" : "low"
                    const victim = kill.victim || {}
                    const fb = kill.final_blow || {}

                    return (
                        <a
                            key={kill.killmail_id}
                            href={`https://zkillboard.com/kill/${kill.killmail_id}/`}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ textDecoration: 'none', color: 'inherit' }}
                        >
                            <div className={`kill-entry${kill.in_lawn ? ' in-lawn' : ''}`}>
                                <div className="kill-time">
                                    <div>{timeAgo(kill.time)} ago</div>
                                    <div className={`kill-system ${kill.in_lawn ? 'lawn' : 'region'}`}>{kill.system_name}</div>
                                </div>
                                <div className="kill-details">
                                    <div className="kill-ship">
                                        {victim.ship_type || "Unknown Ship"}
                                        {kill.is_npc && <span className="kill-npc-tag">NPC</span>}
                                    </div>
                                    <div className="kill-parties">
                                        <span style={{ color: 'var(--red)' }}>{victim.character_name || victim.corporation_name || "Unknown"}</span>
                                        {victim.alliance_name && <span style={{ color: 'var(--text-muted)' }}> [{victim.alliance_name}]</span>}
                                        <span style={{ color: 'var(--text-muted)' }}> killed by </span>
                                        <span style={{ color: 'var(--green)' }}>{fb.character_name || fb.corporation_name || "Unknown"}</span>
                                        {kill.attacker_count > 1 && <span style={{ color: 'var(--text-muted)' }}> +{kill.attacker_count - 1}</span>}
                                    </div>
                                </div>
                                <div className={`kill-value ${iskClass}`}>{formatIsk(kill.total_value)}</div>
                            </div>
                        </a>
                    )
                })}
            </div>
        </div>
    )
}

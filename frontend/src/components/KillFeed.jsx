import React from 'react'
import { formatIsk, timeAgo } from '../utils/formatters'
import CornerBrackets from './common/CornerBrackets'

export default function KillFeed({ kills }) {
    if (!kills || kills.length === 0) {
        return (
            <div className="panel panel-wide">
                <CornerBrackets />
                <div className="panel-header">
                    <span className="panel-title">Kill Feed</span>
                    <span className="panel-badge">Kalevala Expanse</span>
                </div>
                <div style={{ textAlign: 'center', padding: 20, color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                    No recent kills in region
                </div>
            </div>
        )
    }

    const lawnKills = kills.filter(k => k.in_lawn).length

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">Kill Feed</span>
                <span className="panel-badge">
                    {kills.length} kills{lawnKills > 0 ? ` — ${lawnKills} in LAWN` : ''}
                </span>
            </div>
            <div className="kill-feed">
                {kills.map(kill => {
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

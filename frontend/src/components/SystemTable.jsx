import React from 'react'
import { getAdmColor } from '../utils/admHelpers'
import { classifyKills } from '../utils/formatters'
import { getSystemUpgrades } from '../utils/upgradeHelpers'
import UpgradeBadges from './common/UpgradeBadges'

function ActivityBar({ value, max, type = "npc" }) {
    const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
    return (
        <div className="activity-bar">
            <div className={`activity-bar-fill ${type}`} style={{ width: `${pct}%` }} />
        </div>
    )
}

export default function SystemTable({ systems, sovereignty, activity, selectedSystem, onSelectSystem, lawnSystemIds, config, annotations = {} }) {
    const sorted = [...systems].sort((a, b) => {
        const sovA = sovereignty[a.system_id] || {}, sovB = sovereignty[b.system_id] || {}
        const actA = activity[a.system_id] || {}, actB = activity[b.system_id] || {}
        if (!sovA.is_friendly && sovB.is_friendly) return -1
        if (sovA.is_friendly && !sovB.is_friendly) return 1
        const pvpA = (actA.ship_kills || 0) + (actA.pod_kills || 0)
        const pvpB = (actB.ship_kills || 0) + (actB.pod_kills || 0)
        if (pvpB !== pvpA) return pvpB - pvpA
        return (actB.jumps || 0) - (actA.jumps || 0)
    })
    const maxNPC = Math.max(...systems.map(s => (activity[s.system_id] || {}).npc_kills || 0), 1)
    const maxJumps = Math.max(...systems.map(s => (activity[s.system_id] || {}).jumps || 0), 1)

    return (
        <div className="table-scroll-wrapper">
        <table className="sys-table">
            <thead>
                <tr>
                    <th>System</th>
                    <th>Sec</th>
                    <th>Sov Holder</th>
                    <th style={{ textAlign: 'right' }}>ADM</th>
                    <th>Status</th>
                    <th>Upgrades</th>
                    <th style={{ textAlign: 'right' }}>PVP</th>
                    <th style={{ textAlign: 'right' }}>Pods</th>
                    <th>NPC Kills</th>
                    <th>Traffic</th>
                    <th style={{ textAlign: 'right' }}>Jumps</th>
                    <th>Note</th>
                </tr>
            </thead>
            <tbody>
                {sorted.map(sys => {
                    const sov = sovereignty[sys.system_id] || {}
                    const act = activity[sys.system_id] || {}
                    const pvp = act.ship_kills || 0, pods = act.pod_kills || 0, npc = act.npc_kills || 0, jumps = act.jumps || 0
                    const adm = sov.adm || 0
                    const sc = sov.is_friendly ? "friendly" : sov.alliance_name ? "hostile" : "neutral"
                    const isSel = String(sys.system_id) === String(selectedSystem)
                    return (
                        <tr key={sys.system_id} className={isSel ? 'selected' : ''} onClick={() => onSelectSystem(String(sys.system_id))}>
                            <td><span className={`sys-name ${sc}`}>{sys.name}</span></td>
                            <td className="sec-status">{sys.security_status}</td>
                            <td><span className={`sov-holder ${sc}`}>{sov.alliance_name || "—"}</span></td>
                            <td className="stat-num" style={{ color: adm > 0 ? getAdmColor(adm) : 'var(--text-muted)' }}>{adm > 0 ? adm.toFixed(1) : "—"}</td>
                            <td>
                                {lawnSystemIds && lawnSystemIds.has(String(sys.system_id)) && sov.is_friendly && adm > 0 && adm < 2 && (
                                    <span style={{
                                        background: '#ff335530',
                                        border: '1px solid #ff3355',
                                        color: '#ff3355',
                                        padding: '2px 6px',
                                        borderRadius: 3,
                                        fontSize: 9,
                                        fontWeight: 'bold'
                                    }}>
                                        ⚠ CRITICAL
                                    </span>
                                )}
                                {lawnSystemIds && lawnSystemIds.has(String(sys.system_id)) && sov.is_friendly && adm >= 2 && adm < 4 && (
                                    <span style={{
                                        background: '#ffaa0020',
                                        border: '1px solid #ffaa00',
                                        color: '#ffaa00',
                                        padding: '2px 6px',
                                        borderRadius: 3,
                                        fontSize: 9,
                                        fontWeight: 'bold'
                                    }}>
                                        ⚠ GRIND
                                    </span>
                                )}
                            </td>
                            <td>
                                {lawnSystemIds && lawnSystemIds.has(String(sys.system_id)) && (() => {
                                    const upgrades = getSystemUpgrades(sys.name, config)
                                    if (upgrades.length === 0) return (
                                        <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>—</span>
                                    )
                                    return <UpgradeBadges upgrades={upgrades} config={config} compact={true} />
                                })()}
                            </td>
                            <td className={`stat-num ${classifyKills(pvp)}`}>{pvp}</td>
                            <td className={`stat-num ${classifyKills(pods, [2, 5])}`}>{pods}</td>
                            <td>
                                <div className="activity-bar-container">
                                    <ActivityBar value={npc} max={maxNPC} type="npc" />
                                    <span className={`stat-num ${classifyKills(npc, [100, 500])}`} style={{ fontSize: '11px', minWidth: '36px', textAlign: 'right' }}>{npc}</span>
                                </div>
                            </td>
                            <td>
                                <div className="activity-bar-container">
                                    <ActivityBar value={jumps} max={maxJumps} type="jumps" />
                                </div>
                            </td>
                            <td className={`stat-num ${classifyKills(jumps, [20, 100])}`}>{jumps}</td>
                            <td style={{
                                maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap', fontSize: 10,
                                color: '#ffaa00', fontStyle: 'italic',
                            }}>{annotations[sys.name]?.note || ''}</td>
                        </tr>
                    )
                })}
            </tbody>
        </table>
        </div>
    )
}

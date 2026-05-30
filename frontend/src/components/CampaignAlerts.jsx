import React from 'react'
import { getCampaignPhase, formatCountdown, formatEveTime } from '../utils/campaignHelpers'
import CornerBrackets from './common/CornerBrackets'

export default function CampaignAlerts({ campaigns, config }) {
    const allianceShort = config?.alliance?.short_name || config?.alliance?.ticker || 'PRIMARY'
    const isPrimaryCampaign = (c) => (c.is_primary ?? c.is_lawn) !== false
    if (!campaigns || campaigns.length === 0) {
        return (
            <div className="panel panel-wide">
                <CornerBrackets />
                <div className="panel-header">
                    <span className="panel-title">⚠ Sovereignty Campaigns</span>
                    <span className="panel-badge" style={{ color: 'var(--green)' }}>ALL CLEAR</span>
                </div>
                <div style={{ padding: 10, textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-muted)', fontSize: 11, fontStyle: 'italic' }}>No active sovereignty campaigns. Secure the lawn.</div>
                </div>
            </div>
        )
    }

    const enrichedCampaigns = campaigns.map(c => ({
        ...c,
        phaseInfo: getCampaignPhase(c)
    })).sort((a, b) => {
        const aPrimary = isPrimaryCampaign(a)
        const bPrimary = isPrimaryCampaign(b)
        if (aPrimary !== bPrimary) return aPrimary ? -1 : 1

        if (a.phaseInfo.phase !== b.phaseInfo.phase) {
            return a.phaseInfo.phase === 'nodes' ? -1 : 1
        }
        return 0
    })

    const activeCount = enrichedCampaigns.filter(c => c.phaseInfo.phase === 'nodes').length
    const reffedCount = enrichedCampaigns.filter(c => c.phaseInfo.phase === 'reinforced').length

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">⚠ Sovereignty Campaigns</span>
                <div className="panel-badge">
                    {activeCount > 0 && <span style={{ color: '#ff3355', marginRight: 8 }}>{activeCount} ACTIVE</span>}
                    {reffedCount > 0 && <span style={{ color: '#ffaa00' }}>{reffedCount} REINFORCED</span>}
                </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {enrichedCampaigns.map((c, i) => {
                    const phase = c.phaseInfo
                    const isNodesActive = phase.phase === "nodes"
                    const isPrimary = isPrimaryCampaign(c)

                    return (
                        <div key={i} className={`campaign-entry-compact ${isPrimary ? 'lawn' : ''} ${isNodesActive ? 'active' : ''}`}>
                            <div style={{ width: 100, flexShrink: 0 }}>
                                {isPrimary ? (
                                    c.defender_is_friendly ? (
                                        <span className={isNodesActive ? "campaign-badge-red" : "campaign-badge-lawn"}>
                                            {allianceShort} DEFENSE
                                        </span>
                                    ) : (
                                        <span className={isNodesActive ? "campaign-badge-red" : "campaign-badge-lawn"} style={{ color: '#ffaa00' }}>
                                            RECONQUEST
                                        </span>
                                    )
                                ) : (
                                    <span style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: 1 }}>REGIONAL</span>
                                )}
                            </div>
                            <div style={{ width: 90, flexShrink: 0, fontSize: 13, fontWeight: 'bold', color: isPrimary ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                                {c.system_name}
                            </div>
                            <div style={{ flex: 1, minWidth: 200 }}>
                                {isNodesActive ? (
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                        <div style={{ flex: 1, height: 4, background: 'rgba(255,255,255,0.05)', borderRadius: 2, overflow: 'hidden', display: 'flex' }}>
                                            <div style={{ width: `${(c.attackers_score || 0) * 100}%`, background: '#ff3355' }} />
                                            <div style={{ width: `${(c.defender_score || 0) * 100}%`, background: '#00ff88' }} />
                                        </div>
                                        <div style={{ fontSize: 10, whiteSpace: 'nowrap', minWidth: 80, textAlign: 'right' }}>
                                            <span style={{ color: '#ff3355' }}>{((c.attackers_score || 0) * 100).toFixed(0)}%</span>
                                            <span style={{ color: 'var(--text-muted)', margin: '0 4px' }}>vs</span>
                                            <span style={{ color: '#00ff88' }}>{((c.defender_score || 0) * 100).toFixed(0)}%</span>
                                        </div>
                                    </div>
                                ) : (
                                    <div style={{ fontSize: 11, color: isPrimary ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                                        <span style={{ opacity: 0.7 }}>Reinforced — Nodes spawn in </span>
                                        <span style={{ color: 'var(--amber)', fontWeight: 'bold' }}>{formatCountdown(phase.nodesSpawnTime)}</span>
                                        <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 8 }}>({formatEveTime(phase.nodesSpawnTime.toISOString())})</span>
                                    </div>
                                )}
                            </div>
                            {isPrimary && isNodesActive && (
                                <div style={{
                                    width: 8, height: 8, borderRadius: '50%', background: 'var(--red)',
                                    boxShadow: '0 0 10px var(--red)', animation: 'pulse-dot 1.5s infinite'
                                }} />
                            )}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

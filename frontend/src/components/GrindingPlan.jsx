import React from 'react'
import { getAdmColor } from '../utils/admHelpers'
import { getSystemUpgrades, getUpgradeSummary } from '../utils/upgradeHelpers'
import CornerBrackets from './common/CornerBrackets'
import UpgradeBadges from './common/UpgradeBadges'

export default function GrindingPlan({ config, sovereignty, activity, admHistory }) {
    const lawnSystems = []
    const lawnConstIds = new Set((config && config.lawn_constellation_ids || []).map(String))
    if (config && config.constellations) {
        Object.entries(config.constellations).forEach(([cid, c]) => {
            if (c.is_lawn || lawnConstIds.has(String(cid))) {
                Object.values(c.systems).forEach(sys => {
                    lawnSystems.push({
                        ...sys,
                        system_id: String(sys.system_id)
                    })
                })
            }
        })
    }

    const strategicSystems = new Set(["UDVW-O", "N-JK02", "F48K-D", "FB5U-I"])

    const plannedSystems = lawnSystems.map(sys => {
        const sysId = sys.system_id
        const sov = sovereignty[sysId] || {}
        const adm = sov.adm || 0
        const histData = admHistory && admHistory[sysId] ? admHistory[sysId].history : []

        let change24h = 0
        if (histData.length >= 2) {
            const cutoff = Date.now() - 24 * 60 * 60 * 1000
            let oldPoint = histData[0]
            for (let i = 0; i < histData.length; i++) {
                if (new Date(histData[i].timestamp).getTime() >= cutoff) {
                    oldPoint = histData[Math.max(0, i - 1)]
                    break
                }
            }
            change24h = adm - oldPoint.adm
        }

        let score = 0
        if (adm > 0 && adm < 2.0) score += 1000
        else if (adm >= 2.0 && adm < 4.0) score += 200

        if (strategicSystems.has(sys.name)) score += 500

        if (adm > 0) score += (6.0 - adm) * 50

        if (change24h < -0.1) score += 100

        return {
            ...sys,
            adm,
            change24h,
            score,
            isStrategic: strategicSystems.has(sys.name)
        }
    })

    const targets = plannedSystems
        .filter(s => s.adm > 0 && s.adm < 4.5)
        .sort((a, b) => b.score - a.score)
        .slice(0, 6)

    if (targets.length === 0) return null

    return (
        <div className="panel panel-wide" style={{ borderColor: 'var(--amber-dim)' }}>
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title" style={{ color: 'var(--amber)' }}>⚠ Daily Grinding Targets</span>
                <span className="panel-badge">Top Priorities</span>
            </div>
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: 10
            }}>
                {targets.map((sys, i) => {
                    const upgrades = getSystemUpgrades(sys.name, config)
                    const summary = getUpgradeSummary(sys.name, config)
                    const hasMilitary = summary.military > 0
                    const hasIndustry = summary.industry > 0
                    const hasStrategic = summary.strategic > 0
                    return (
                        <div key={sys.system_id} style={{
                            background: 'rgba(255,170,0,0.05)',
                            border: '1px solid rgba(255,170,0,0.2)',
                            padding: 10,
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 4,
                            position: 'relative'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{
                                    fontFamily: 'Orbitron, sans-serif',
                                    fontWeight: 'bold',
                                    color: sys.adm < 2.0 ? 'var(--red)' : 'var(--text-primary)'
                                }}>
                                    {sys.name}
                                </span>
                                <span style={{
                                    fontFamily: 'Share Tech Mono, monospace',
                                    color: getAdmColor(sys.adm),
                                    fontWeight: 'bold'
                                }}>
                                    {sys.adm.toFixed(1)}
                                </span>
                            </div>
                            <div style={{ display: 'flex', gap: 6, fontSize: 10, color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
                                {sys.isStrategic && (
                                    <span style={{ color: 'var(--cyan)', border: '1px solid rgba(0,212,255,0.3)', padding: '0 4px', borderRadius: 2 }}>STRATEGIC</span>
                                )}
                                {sys.change24h < -0.05 && (
                                    <span style={{ color: 'var(--red)' }}>DROPPING ({sys.change24h.toFixed(1)})</span>
                                )}
                            </div>
                            <div style={{ display: 'flex', gap: 4, marginTop: 2 }}>
                                <span style={{ fontSize: 8, padding: '0 3px', borderRadius: 2, background: hasMilitary ? 'rgba(255,102,119,0.15)' : 'rgba(255,51,85,0.05)', border: `1px solid ${hasMilitary ? 'rgba(255,102,119,0.4)' : 'rgba(255,51,85,0.15)'}`, color: hasMilitary ? '#ff6677' : '#552233' }} title={hasMilitary ? `${summary.military} military upgrade(s)` : 'No military upgrades installed'}>MIL {hasMilitary ? summary.military : '—'}</span>
                                <span style={{ fontSize: 8, padding: '0 3px', borderRadius: 2, background: hasIndustry ? 'rgba(0,255,136,0.1)' : 'rgba(0,255,136,0.03)', border: `1px solid ${hasIndustry ? 'rgba(0,255,136,0.3)' : 'rgba(0,255,136,0.1)'}`, color: hasIndustry ? '#00ff88' : '#224433' }} title={hasIndustry ? `${summary.industry} industry upgrade(s)` : 'No industry upgrades installed'}>IND {hasIndustry ? summary.industry : '—'}</span>
                                <span style={{ fontSize: 8, padding: '0 3px', borderRadius: 2, background: hasStrategic ? 'rgba(0,212,255,0.1)' : 'rgba(0,212,255,0.03)', border: `1px solid ${hasStrategic ? 'rgba(0,212,255,0.3)' : 'rgba(0,212,255,0.1)'}`, color: hasStrategic ? '#00d4ff' : '#223344' }} title={hasStrategic ? `${summary.strategic} strategic upgrade(s)` : 'No strategic upgrades'}>STR {hasStrategic ? summary.strategic : '—'}</span>
                            </div>
                            {upgrades.length > 0 && (
                                <div style={{ marginTop: 2 }}>
                                    <UpgradeBadges upgrades={upgrades} config={config} compact={true} />
                                </div>
                            )}
                            <div style={{
                                fontSize: 9,
                                color: 'var(--text-muted)',
                                fontStyle: 'italic',
                                marginTop: 2
                            }}>
                                {sys.adm < 2.0 ? "CRITICAL VULNERABILITY" : "Raise to 4.0+"}
                            </div>
                            <div style={{
                                position: 'absolute',
                                top: 0, right: 0,
                                width: 16, height: 16,
                                background: 'rgba(255,170,0,0.1)',
                                color: 'var(--amber)',
                                fontSize: 10,
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                fontFamily: 'Orbitron, sans-serif'
                            }}>
                                {i + 1}
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

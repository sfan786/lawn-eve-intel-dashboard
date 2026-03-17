import React, { useState } from 'react'
import { getAdmColor, computeGrindingRate, compute24hChange } from '../utils/admHelpers'
import { getSystemUpgrades, getUpgradeSummary } from '../utils/upgradeHelpers'
import CornerBrackets from './common/CornerBrackets'
import UpgradeBadges from './common/UpgradeBadges'

const SYSTEM_TIERS = {
    border: new Set(["UDVW-O", "N-JK02"]),
    crossConst: new Set(["F48K-D", "FB5U-I"]),
    hub: new Set(["1-KCSA", "BZ-BCK", "O5-YNW", "IUU3-L"]),
    deadEnd: new Set(["JT2I-7", "J-OAH2", "86L-9F", "5-VFC6", "S-LHPJ"]),
}

function getTierBonus(name) {
    if (SYSTEM_TIERS.border.has(name)) return { bonus: 500, label: "BORDER" }
    if (SYSTEM_TIERS.crossConst.has(name)) return { bonus: 300, label: "CROSS" }
    if (SYSTEM_TIERS.hub.has(name)) return { bonus: 100, label: "HUB" }
    if (SYSTEM_TIERS.deadEnd.has(name)) return { bonus: -50, label: "DEAD-END" }
    return { bonus: 0, label: "—" }
}

function RateDisplay({ rate }) {
    if (rate === null) {
        return <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>No data</span>
    }
    const abs = Math.abs(rate)
    if (abs < 0.05) {
        return <span style={{ color: 'var(--text-muted)' }}>Flat</span>
    }
    const sign = rate > 0 ? '+' : ''
    const color = rate > 0 ? '#00ff88' : '#ff3355'
    return <span style={{ color }}>{sign}{rate.toFixed(1)}/day</span>
}

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

    const plannedSystems = lawnSystems.map(sys => {
        const sysId = sys.system_id
        const sov = sovereignty[sysId] || {}
        const adm = sov.adm || 0
        const histData = admHistory && admHistory[sysId] ? admHistory[sysId].history : []

        const change24h = compute24hChange(histData, adm)
        const rate = computeGrindingRate(histData)
        const tier = getTierBonus(sys.name)

        let score = 0
        if (adm > 0 && adm < 2.0) score += 1000
        else if (adm >= 2.0 && adm < 4.0) score += 200

        score += tier.bonus

        if (adm > 0) score += (6.0 - adm) * 50

        if (change24h < -0.1) score += 100

        return {
            ...sys,
            adm,
            change24h,
            rate,
            score,
            tierLabel: tier.label,
        }
    })

    const targets = plannedSystems
        .filter(s => s.adm > 0 && s.adm < 4.5)
        .sort((a, b) => b.score - a.score)
        .slice(0, 6)

    const allSorted = [...plannedSystems].sort((a, b) => b.score - a.score)
    const [showTable, setShowTable] = useState(false)
    const [targetAdms, setTargetAdms] = useState(() => {
        try { return JSON.parse(localStorage.getItem('adm_targets')) || {} }
        catch (e) { return {} }
    })

    const handleSetTarget = (sysId, currentTarget) => {
        const val = prompt("Set target ADM (e.g. 4.5, max 6.0):", currentTarget)
        if (val !== null) {
            const num = Math.min(Math.max(parseFloat(val) || 4.5, 1.0), 6.0)
            const newTargets = { ...targetAdms, [sysId]: num }
            setTargetAdms(newTargets)
            localStorage.setItem('adm_targets', JSON.stringify(newTargets))
        }
    }

    if (targets.length === 0) return null

    return (
        <div className="panel panel-wide" style={{ borderColor: 'var(--amber-dim)' }}>
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title" style={{ color: 'var(--amber)' }}>⚠ Daily Grinding Targets</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button
                        onClick={() => setShowTable(v => !v)}
                        style={{
                            background: 'none',
                            border: '1px solid rgba(255,255,255,0.1)',
                            color: 'var(--text-muted)',
                            fontFamily: 'Share Tech Mono, monospace',
                            fontSize: 10,
                            padding: '2px 8px',
                            cursor: 'pointer',
                            borderRadius: 2,
                            letterSpacing: '0.05em',
                        }}
                    >
                        {showTable ? '▴ All systems' : '▾ All systems'}
                    </button>
                    <span className="panel-badge">Top Priorities</span>
                </div>
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
                            <div style={{ fontSize: 10, fontFamily: 'Share Tech Mono, monospace' }}>
                                <RateDisplay rate={sys.rate} />
                            </div>
                            <div style={{ display: 'flex', gap: 6, fontSize: 10, color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
                                {sys.tierLabel !== '—' && sys.tierLabel !== 'DEAD-END' && (
                                    <span style={{ color: 'var(--cyan)', border: '1px solid rgba(0,212,255,0.3)', padding: '0 4px', borderRadius: 2 }}>{sys.tierLabel}</span>
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
                            <div
                                style={{ marginTop: 6, cursor: 'pointer' }}
                                onClick={() => handleSetTarget(sys.system_id, targetAdms[sys.system_id] || 4.5)}
                                title="Click to set Target ADM"
                            >
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, fontFamily: 'Share Tech Mono, monospace', color: 'var(--text-muted)', marginBottom: 2 }}>
                                    <span style={{ color: sys.adm < 2.0 ? 'var(--red)' : 'var(--text-muted)' }}>
                                        {sys.adm < 2.0 ? "CRITICAL VULN" : `TARGET: ${targetAdms[sys.system_id] || 4.5}`}
                                    </span>
                                    <span>{Math.round(Math.min((sys.adm / (targetAdms[sys.system_id] || 4.5)) * 100, 100))}%</span>
                                </div>
                                <div style={{ height: 4, background: 'rgba(255,255,255,0.1)', borderRadius: 2, overflow: 'hidden' }}>
                                    <div style={{ height: '100%', width: `${Math.min((sys.adm / (targetAdms[sys.system_id] || 4.5)) * 100, 100)}%`, background: getAdmColor(sys.adm), transition: 'width 0.5s ease-out' }} />
                                </div>
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

            {/* Full system table — collapsible */}
            {showTable && (
                <div style={{ marginTop: 10 }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, fontFamily: 'Share Tech Mono, monospace' }}>
                        <thead>
                            <tr style={{ color: 'var(--text-muted)', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                                <th style={{ textAlign: 'left', padding: '3px 6px', fontWeight: 'normal' }}>System</th>
                                <th style={{ textAlign: 'right', padding: '3px 6px', fontWeight: 'normal' }}>ADM</th>
                                <th style={{ textAlign: 'right', padding: '3px 6px', fontWeight: 'normal' }}>Rate/day</th>
                                <th style={{ textAlign: 'right', padding: '3px 6px', fontWeight: 'normal' }}>Tier</th>
                            </tr>
                        </thead>
                        <tbody>
                            {allSorted.map(sys => {
                                const rowColor = sys.adm < 2 ? '#ff3355' : sys.adm < 4 ? '#ffaa00' : '#00d4ff'
                                return (
                                    <tr key={sys.system_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                        <td style={{ padding: '3px 6px', color: rowColor }}>{sys.name}</td>
                                        <td style={{ padding: '3px 6px', textAlign: 'right', color: getAdmColor(sys.adm) }}>
                                            {sys.adm > 0 ? sys.adm.toFixed(1) : '—'}
                                        </td>
                                        <td style={{ padding: '3px 6px', textAlign: 'right' }}>
                                            <RateDisplay rate={sys.rate} />
                                        </td>
                                        <td style={{ padding: '3px 6px', textAlign: 'right', color: 'var(--text-muted)' }}>
                                            {sys.tierLabel}
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    )
}

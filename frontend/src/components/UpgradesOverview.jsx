import React, { useMemo } from 'react'
import { UPGRADE_CATEGORY_COLORS } from '../utils/upgradeHelpers'
import CornerBrackets from './common/CornerBrackets'
import UpgradeBadges from './common/UpgradeBadges'

export default function UpgradesOverview({ config }) {
    if (!config || !config.system_upgrades || !config.upgrade_types) return null

    const upgradeTypes = config.upgrade_types
    const systemUpgrades = config.system_upgrades

    const primarySystems = useMemo(() => config.primary_systems || [], [config])

    // Map system name → constellation name so each card can show which
    // constellation it belongs to. Derived from config so it stays correct
    // for any deployment.
    const systemConstellation = useMemo(() => {
        const lookup = {}
        if (config.constellations) {
            Object.values(config.constellations).forEach(c => {
                Object.values(c.systems || {}).forEach(s => {
                    lookup[s.name] = c.name
                })
            })
        }
        return lookup
    }, [config])

    let totalUpgrades = 0
    let systemsWithUpgrades = 0
    const categoryCounts = { military: 0, industry: 0, strategic: 0 }
    primarySystems.forEach(name => {
        const ups = systemUpgrades[name] || []
        if (ups.length > 0) systemsWithUpgrades++
        totalUpgrades += ups.length
        ups.forEach(u => {
            const meta = upgradeTypes[u.type] || {}
            if (categoryCounts[meta.category] !== undefined) categoryCounts[meta.category]++
        })
    })

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">Sovereignty Upgrades</span>
                <span className="panel-badge">{totalUpgrades} upgrades across {systemsWithUpgrades}/{primarySystems.length} systems</span>
            </div>
            <div style={{ display: 'flex', gap: 16, marginBottom: 8, fontSize: 11, fontFamily: 'Share Tech Mono, monospace' }}>
                <span style={{ color: '#ff6677' }}>Military: {categoryCounts.military}</span>
                <span style={{ color: '#00ff88' }}>Industry: {categoryCounts.industry}</span>
                <span style={{ color: '#00d4ff' }}>Strategic: {categoryCounts.strategic}</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 6 }}>
                {primarySystems.map(name => {
                    const ups = systemUpgrades[name] || []
                    const isEmpty = ups.length === 0
                    const constellation = systemConstellation[name] || ''
                    return (
                        <div key={name} style={{
                            background: isEmpty ? 'rgba(255,51,85,0.03)' : 'rgba(0,212,255,0.03)',
                            border: `1px solid ${isEmpty ? 'rgba(255,51,85,0.15)' : 'rgba(0,212,255,0.12)'}`,
                            padding: '6px 8px',
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                                <span style={{
                                    fontFamily: 'Orbitron, sans-serif',
                                    fontSize: 10,
                                    fontWeight: 'bold',
                                    color: isEmpty ? 'var(--text-muted)' : 'var(--text-primary)',
                                    letterSpacing: 1
                                }}>{name}</span>
                                <span style={{ fontSize: 8, color: 'var(--text-muted)' }}>{constellation}</span>
                            </div>
                            {ups.length > 0 ? (
                                <UpgradeBadges upgrades={ups} config={config} compact={true} />
                            ) : (
                                <span style={{ fontSize: 9, color: '#663344', fontStyle: 'italic' }}>No upgrades installed</span>
                            )}
                        </div>
                    )
                })}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 10, paddingTop: 8, borderTop: '1px solid var(--border-dim)', fontSize: 9, color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace' }}>
                {Object.entries(upgradeTypes).map(([code, meta]) => (
                    <span key={code} style={{ color: UPGRADE_CATEGORY_COLORS[meta.category] || '#6a8090' }}>
                        {code} = {meta.name}
                    </span>
                ))}
            </div>
        </div>
    )
}

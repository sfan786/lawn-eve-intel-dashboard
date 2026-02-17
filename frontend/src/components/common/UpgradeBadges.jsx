import React from 'react'
import { getUpgradeTypeMeta, UPGRADE_CATEGORY_COLORS } from '../../utils/upgradeHelpers'

export default function UpgradeBadges({ upgrades, config, compact }) {
    if (!upgrades || upgrades.length === 0) return null
    return (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: compact ? 2 : 3 }}>
            {upgrades.map((u, i) => {
                const meta = getUpgradeTypeMeta(u.type, config)
                const color = UPGRADE_CATEGORY_COLORS[meta.category] || "#6a8090"
                return (
                    <span
                        key={i}
                        className={`upgrade-badge ${meta.category}`}
                        title={`${meta.name} ${u.level}`}
                        style={compact ? { fontSize: 8, padding: '0 3px' } : {}}
                    >
                        {u.type} {u.level}
                    </span>
                )
            })}
        </div>
    )
}

import React from 'react'

// A sov-holding deployment gets the full board. A rootless one has no map, no
// system table and no PI, so those tabs would open onto nothing — it gets the
// three that carry content without a home region.
export const SOV_TABS = [
    { id: 0, icon: '🗺', label: 'Map' },
    { id: 1, icon: '📋', label: 'Systems' },
    { id: 2, icon: '💀', label: 'Kills' },
    { id: 3, icon: '📡', label: 'Intel' },
    { id: 4, icon: '⏱', label: 'Timers' },
    { id: 5, icon: '🏭', label: 'Industry' },
]

export const ROOTLESS_TABS = [
    { id: 3, icon: '📡', label: 'Intel' },
    { id: 2, icon: '💀', label: 'Kills' },
    { id: 4, icon: '⏱', label: 'Timers' },
]

export default function MobileNav({ activeTab, onTabChange, tabs = SOV_TABS }) {
    return (
        <nav className="mobile-nav">
            {tabs.map(tab => (
                <button
                    key={tab.id}
                    className={`mobile-nav-tab ${activeTab === tab.id ? 'active' : ''}`}
                    onClick={() => onTabChange(tab.id)}
                >
                    <span className="mobile-nav-icon">{tab.icon}</span>
                    <span className="mobile-nav-label">{tab.label}</span>
                </button>
            ))}
        </nav>
    )
}

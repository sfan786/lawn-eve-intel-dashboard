import React from 'react'

const TABS = [
    { id: 0, icon: '🗺', label: 'Map' },
    { id: 1, icon: '📋', label: 'Systems' },
    { id: 2, icon: '💀', label: 'Kills' },
    { id: 3, icon: '📡', label: 'Intel' },
    { id: 4, icon: '⏱', label: 'Timers' },
    { id: 5, icon: '🏭', label: 'Industry' },
]

export default function MobileNav({ activeTab, onTabChange }) {
    return (
        <nav className="mobile-nav">
            {TABS.map(tab => (
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

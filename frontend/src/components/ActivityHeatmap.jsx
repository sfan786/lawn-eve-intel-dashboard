import React, { useState, useEffect } from 'react'
import CornerBrackets from './common/CornerBrackets'

export default function ActivityHeatmap({ config, sovereignty, lastUpdate }) {
    const [data, setData] = useState({})
    const [view, setView] = useState("npc")
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetch("/api/history/activity/heatmap")
            .then(r => r.json())
            .then(d => {
                setData(d)
                setLoading(false)
            })
    }, [lastUpdate])

    if (loading) return null

    const lawnSystems = []
    const lawnConstIds = new Set((config && config.lawn_constellation_ids || []).map(String))
    if (config && config.constellations) {
        Object.values(config.constellations).forEach(c => {
            if (c.is_lawn || lawnConstIds.has(String(c.constellation_id))) {
                Object.values(c.systems).forEach(sys => {
                    lawnSystems.push(sys)
                })
            }
        })
    }

    lawnSystems.sort((a, b) => a.name.localeCompare(b.name))

    const hours = Array.from({ length: 24 }, (_, i) => i)

    const getColor = (val, type) => {
        if (val === 0) return "rgba(255,255,255,0.02)"
        if (type === "npc") {
            const opacity = Math.min(0.1 + (val / 500), 0.9)
            return `rgba(0, 212, 255, ${opacity})`
        } else if (type === "pvp") {
            const opacity = Math.min(0.2 + (val / 5), 0.9)
            return `rgba(255, 51, 85, ${opacity})`
        } else {
            const opacity = Math.min(0.1 + (val / 100), 0.9)
            return `rgba(255, 170, 0, ${opacity})`
        }
    }

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">Time-Zone Activity Heatmap</span>
                <div style={{ display: 'flex', gap: 4 }}>
                    <button className={`const-tab ${view === 'npc' ? 'active' : ''}`} onClick={() => setView('npc')} style={{ fontSize: 9, padding: '2px 8px' }}>NPC KILLS</button>
                    <button className={`const-tab ${view === 'pvp' ? 'active' : ''}`} onClick={() => setView('pvp')} style={{ fontSize: 9, padding: '2px 8px' }}>PVP KILLS</button>
                    <button className={`const-tab ${view === 'jumps' ? 'active' : ''}`} onClick={() => setView('jumps')} style={{ fontSize: 9, padding: '2px 8px' }}>JUMPS</button>
                </div>
            </div>
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'Share Tech Mono' }}>
                    <thead>
                        <tr>
                            <th style={{ textAlign: 'left', fontSize: 9, color: 'var(--text-muted)', padding: 4 }}>SYSTEM</th>
                            {hours.map(h => (
                                <th key={h} style={{ fontSize: 8, color: 'var(--text-muted)', width: 20 }}>{h.toString().padStart(2, '0')}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {lawnSystems.map(sys => {
                            const sysData = data[String(sys.system_id)] || {}
                            return (
                                <tr key={sys.system_id}>
                                    <td style={{ fontSize: 10, padding: '2px 4px', whiteSpace: 'nowrap', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>{sys.name}</td>
                                    {hours.map(h => {
                                        const val = sysData[h] ? sysData[h][view] : 0
                                        return (
                                            <td
                                                key={h}
                                                title={`${sys.name} @ ${h}:00 - ${val} ${view}`}
                                                style={{
                                                    height: 14,
                                                    background: getColor(val, view),
                                                    border: '0.5px solid rgba(0,0,0,0.2)'
                                                }}
                                            />
                                        )
                                    })}
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

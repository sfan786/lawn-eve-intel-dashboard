import React from 'react'
import { getAdmColor, compute24hChange } from '../utils/admHelpers'
import CornerBrackets from './common/CornerBrackets'
import Sparkline from './Sparkline'

export default function AdmTrends({ admHistory, config, sovereignty }) {
    const lawnSystems = []
    const lawnConstIds = new Set((config && config.lawn_constellation_ids || []).map(String))
    if (config && config.constellations) {
        Object.entries(config.constellations).forEach(([cid, c]) => {
            if (c.is_lawn || lawnConstIds.has(String(cid))) {
                Object.values(c.systems).forEach(sys => {
                    lawnSystems.push({ system_id: sys.system_id, name: sys.name })
                })
            }
        })
    }

    lawnSystems.sort((a, b) => {
        const admA = (sovereignty[a.system_id] || {}).adm || 0
        const admB = (sovereignty[b.system_id] || {}).adm || 0
        return admA - admB
    })

    const hasData = admHistory && Object.keys(admHistory).length > 0

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">ADM Trends</span>
                <span className="panel-badge">7 day history</span>
            </div>
            {!hasData ? (
                <div style={{ textAlign: 'center', padding: 20, color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                    Collecting data... trends will appear after first snapshot
                </div>
            ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 6 }}>
                    {lawnSystems.map(sys => {
                        const histData = admHistory[String(sys.system_id)] || {}
                        const history = histData.history || []
                        const sov = sovereignty[sys.system_id] || {}
                        const currentAdm = sov.adm || 0

                        const change24h = history.length >= 2 ? compute24hChange(history, currentAdm) : null

                        return (
                            <div key={sys.system_id} style={{
                                display: 'flex', alignItems: 'center', gap: 8,
                                padding: '5px 10px',
                                background: 'rgba(0,5,10,0.4)',
                                border: '1px solid var(--border-dim)',
                            }}>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 56 }}>
                                    <span style={{
                                        fontFamily: 'Share Tech Mono, monospace',
                                        fontSize: 11, color: '#c8d8e8',
                                    }}>{sys.name}</span>
                                    {sov.is_friendly && currentAdm > 0 && currentAdm < 4 && (
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                                            <div style={{
                                                width: 4, height: 4, borderRadius: '50%',
                                                background: currentAdm < 2 ? '#ff3355' : '#ffaa00',
                                                boxShadow: `0 0 4px ${currentAdm < 2 ? '#ff3355' : '#ffaa00'}`
                                            }} />
                                            <span style={{ fontSize: 9, color: currentAdm < 2 ? '#ff3355' : '#ffaa00', opacity: 0.8 }}>
                                                {currentAdm < 2 ? 'CRIT' : 'LOW'}
                                            </span>
                                        </div>
                                    )}
                                </div>
                                <span style={{
                                    fontFamily: 'Share Tech Mono, monospace',
                                    fontSize: 13, fontWeight: 'bold',
                                    color: currentAdm > 0 ? getAdmColor(currentAdm) : '#3a5060',
                                    minWidth: 30, textAlign: 'right',
                                }}>{currentAdm > 0 ? currentAdm.toFixed(1) : '\u2014'}</span>
                                {change24h !== null && (
                                    <span style={{
                                        fontFamily: 'Share Tech Mono, monospace',
                                        fontSize: 10,
                                        color: change24h > 0.01 ? '#00ff88' : change24h < -0.01 ? '#ff3355' : '#3a5060',
                                        minWidth: 38,
                                    }}>
                                        {change24h > 0.01 ? '\u2191' : change24h < -0.01 ? '\u2193' : '\u2014'}{Math.abs(change24h).toFixed(1)}
                                    </span>
                                )}
                                <div style={{ flex: 1, minWidth: 80 }}>
                                    <Sparkline history={history} />
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    )
}

import React, { useState } from 'react'
import CornerBrackets from './common/CornerBrackets'

const STANDING_CONFIG = {
    unknown:    { label: 'UNKNOWN',    color: '#6a8090', bg: 'rgba(106,128,144,0.08)' },
    friendly:   { label: 'FRIENDLY',   color: '#00d4ff', bg: 'rgba(0,212,255,0.08)' },
    lawn:       { label: 'LAWN',       color: '#00ff88', bg: 'rgba(0,255,136,0.08)' },
    unresolved: { label: '?',          color: '#ffaa00', bg: 'rgba(255,170,0,0.08)' },
}

const STANDING_ORDER = { unknown: 0, friendly: 1, lawn: 2, unresolved: 3 }

function parseNames(raw) {
    if (!raw.trim()) return []
    const names = raw.includes('\n')
        ? raw.split('\n').map(s => s.trim()).filter(Boolean)
        : raw.split(/[\s,]+/).map(s => s.trim()).filter(Boolean)
    return [...new Set(names)] // deduplicate
}

export default function LocalScanner() {
    const [rawInput, setRawInput] = useState('')
    const [results, setResults] = useState(null)
    const [scanning, setScanning] = useState(false)
    const [error, setError] = useState(null)

    const names = parseNames(rawInput)

    async function handleScan() {
        if (!names.length) return
        setScanning(true)
        setError(null)
        try {
            const resp = await fetch('/api/local/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ names }),
            })
            if (!resp.ok) throw new Error(`Server error: ${resp.status}`)
            const data = await resp.json()
            // Sort: unknown first, then friendly, then lawn, then unresolved
            data.sort((a, b) => (STANDING_ORDER[a.standing] ?? 99) - (STANDING_ORDER[b.standing] ?? 99))
            setResults(data)
        } catch (e) {
            setError(e.message)
        } finally {
            setScanning(false)
        }
    }

    function handleClear() {
        setRawInput('')
        setResults(null)
        setError(null)
    }

    const counts = results ? {
        unknown: results.filter(r => r.standing === 'unknown').length,
        friendly: results.filter(r => r.standing === 'friendly').length,
        lawn: results.filter(r => r.standing === 'lawn').length,
        unresolved: results.filter(r => r.standing === 'unresolved').length,
    } : null

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">LOCAL SCANNER</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {results && (
                        <span className="panel-badge">
                            {counts.unknown > 0 && <span style={{ color: STANDING_CONFIG.unknown.color }}>{counts.unknown} unknown</span>}
                            {counts.unknown > 0 && (counts.friendly > 0 || counts.lawn > 0) && <span style={{ color: 'var(--text-muted)' }}> · </span>}
                            {counts.friendly > 0 && <span style={{ color: STANDING_CONFIG.friendly.color }}>{counts.friendly} friendly</span>}
                            {counts.friendly > 0 && counts.lawn > 0 && <span style={{ color: 'var(--text-muted)' }}> · </span>}
                            {counts.lawn > 0 && <span style={{ color: STANDING_CONFIG.lawn.color }}>{counts.lawn} lawn</span>}
                            {counts.unresolved > 0 && <span style={{ color: 'var(--text-muted)' }}> · </span>}
                            {counts.unresolved > 0 && <span style={{ color: STANDING_CONFIG.unresolved.color }}>{counts.unresolved} unresolved</span>}
                        </span>
                    )}
                    {(rawInput || results) && (
                        <button
                            onClick={handleClear}
                            style={{
                                background: 'none', border: '1px solid var(--border-dim)',
                                color: 'var(--text-secondary)', cursor: 'pointer',
                                fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                                padding: '2px 8px', letterSpacing: 1,
                            }}
                        >CLEAR</button>
                    )}
                </div>
            </div>

            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <textarea
                    value={rawInput}
                    onChange={e => setRawInput(e.target.value)}
                    placeholder="Paste pilot names from local chat (one per line or comma-separated)..."
                    style={{
                        flex: 1, minHeight: 72, background: 'rgba(0,0,0,0.3)',
                        border: '1px solid var(--border-dim)', color: 'var(--text-primary)',
                        fontFamily: 'Share Tech Mono, monospace', fontSize: 11,
                        padding: '8px 10px', resize: 'vertical', outline: 'none',
                    }}
                />
                <button
                    onClick={handleScan}
                    disabled={!names.length || scanning}
                    style={{
                        background: names.length && !scanning ? 'rgba(0,212,255,0.1)' : 'rgba(0,0,0,0.2)',
                        border: `1px solid ${names.length && !scanning ? 'var(--cyan-dim)' : 'var(--border-dim)'}`,
                        color: names.length && !scanning ? 'var(--cyan)' : 'var(--text-muted)',
                        cursor: names.length && !scanning ? 'pointer' : 'default',
                        fontFamily: 'Orbitron, sans-serif', fontSize: 10,
                        fontWeight: 600, letterSpacing: 2,
                        padding: '0 16px', height: 72, whiteSpace: 'nowrap',
                        transition: 'all 0.2s',
                    }}
                >
                    {scanning ? 'SCANNING...' : 'SCAN\nLOCAL'}
                </button>
            </div>

            {error && (
                <div style={{
                    marginTop: 8, padding: '6px 10px',
                    background: 'rgba(255,51,85,0.1)', border: '1px solid var(--red)',
                    fontFamily: 'Share Tech Mono, monospace', fontSize: 11, color: 'var(--red)',
                }}>
                    ERROR: {error}
                </div>
            )}

            {results && results.length > 0 && (
                <div style={{ marginTop: 10 }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border-dim)' }}>
                                <th style={{ padding: '4px 8px', textAlign: 'left', fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 2, color: 'var(--text-muted)', fontWeight: 500 }}>PILOT</th>
                                <th style={{ padding: '4px 8px', textAlign: 'left', fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 2, color: 'var(--text-muted)', fontWeight: 500 }}>CORP / ALLIANCE</th>
                                <th style={{ padding: '4px 8px', textAlign: 'right', fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 2, color: 'var(--text-muted)', fontWeight: 500 }}>STANDING</th>
                            </tr>
                        </thead>
                        <tbody>
                            {results.map((r, i) => {
                                const cfg = STANDING_CONFIG[r.standing] || STANDING_CONFIG.unknown
                                return (
                                    <tr key={i} style={{ borderBottom: '1px solid var(--border-dim)', background: cfg.bg }}>
                                        <td style={{ padding: '5px 8px', fontFamily: 'Share Tech Mono, monospace', fontSize: 11, color: 'var(--text-primary)' }}>
                                            {r.character_id ? (
                                                <a
                                                    href={`https://zkillboard.com/character/${r.character_id}/`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    style={{ color: cfg.color, textDecoration: 'none' }}
                                                >
                                                    {r.name}
                                                </a>
                                            ) : r.name}
                                        </td>
                                        <td style={{ padding: '5px 8px', fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: 'var(--text-secondary)' }}>
                                            {r.corporation_name && <span>{r.corporation_name}</span>}
                                            {r.corporation_name && r.alliance_name && <span style={{ color: 'var(--text-muted)' }}> · </span>}
                                            {r.alliance_name && <span style={{ color: r.standing === 'unknown' ? '#ff9966' : 'var(--text-secondary)' }}>{r.alliance_name}</span>}
                                            {!r.corporation_name && !r.alliance_name && (
                                                <span style={{ color: 'var(--text-muted)' }}>—</span>
                                            )}
                                        </td>
                                        <td style={{ padding: '5px 8px', textAlign: 'right' }}>
                                            <span style={{
                                                fontFamily: 'Orbitron, sans-serif', fontSize: 9,
                                                fontWeight: 600, letterSpacing: 2, color: cfg.color,
                                            }}>{cfg.label}</span>
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {results && results.length === 0 && (
                <div style={{ padding: '8px 0', color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                    No pilots resolved.
                </div>
            )}
        </div>
    )
}

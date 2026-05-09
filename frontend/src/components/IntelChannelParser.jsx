import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react'
import CornerBrackets from './common/CornerBrackets'

const EXPIRE_OPTIONS = [5, 10, 15, 30, 60]
const DEFAULT_EXPIRE_MIN = 15

// EVE chat log line format: [ YYYY.MM.DD HH:MM:SS ] CharName > message
const EVE_LINE_RE = /^\[\s*(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s*\]\s*(.+?)\s*>\s*(.+)$/

const CLEAR_RE = /\b(clear|clr|cleared|safe)\b/i

// Common shorthand → display label; checked case-insensitively as substrings
const SHIP_HINTS = [
    ['gate camp', 'Gate Camp'], ['bubble', 'Bubble'],
    ['hic', 'HIC'], ['devoter', 'HIC'], ['onyx', 'HIC'], ['phobos', 'HIC'], ['broadsword', 'HIC'],
    ['dictor', 'Dictor'], ['sabre', 'Sabre'], ['interdictor', 'Dictor'],
    ['fax', 'FAX'], ['titan', 'Titan'], ['super', 'Super'],
    ['dread', 'Dread'], ['naglfar', 'Dread'], ['moros', 'Dread'], ['revelation', 'Dread'], ['phoenix', 'Dread'],
    ['carrier', 'Carrier'],
    ['logi', 'Logi'], ['scimi', 'Scimitar'], ['scimitar', 'Scimitar'],
    ['recon', 'Recon'], ['arazu', 'Recon'], ['huginn', 'Recon'], ['rapier', 'Recon'],
    ['hac', 'HAC'], ['muninn', 'HAC'], ['cerb', 'HAC'], ['ishtar', 'HAC'], ['vagabond', 'HAC'],
    ['t3', 'T3'], ['tengu', 'T3'], ['loki', 'T3'], ['legion', 'T3'], ['proteus', 'T3'],
    ['bomber', 'Bomber'], ['covops', 'CovOps'], ['cov ops', 'CovOps'],
    ['inty', 'Interceptor'], ['interceptor', 'Interceptor'], ['stiletto', 'Interceptor'],
    ['bc', 'BC'], ['bs', 'BS'],
]

function parseEveTimestamp(str) {
    const m = str.match(/(\d{4})\.(\d{2})\.(\d{2})\s+(\d{2}):(\d{2}):(\d{2})/)
    if (!m) return null
    return new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]))
}

function buildSystemLookup(config) {
    const map = new Map() // lowercased name → { name, isPrimary, systemId }
    if (!config?.constellations) return map
    Object.values(config.constellations).forEach(c => {
        const isPrimary = c.is_primary ?? c.is_lawn ?? false
        Object.values(c.systems || {}).forEach(s => {
            map.set(s.name.toLowerCase(), { name: s.name, isPrimary, systemId: s.system_id })
        })
    })
    Object.values(config.neighbor_systems || {}).forEach(s => {
        map.set(s.name.toLowerCase(), { name: s.name, isPrimary: false, systemId: null })
    })
    return map
}

function findSystem(message, lookup) {
    const tokens = message.split(/\s+/)
    for (const tok of tokens) {
        const clean = tok.replace(/^[^a-zA-Z0-9-]+|[^a-zA-Z0-9-]+$/g, '').toLowerCase()
        if (clean && lookup.has(clean)) return lookup.get(clean)
    }
    return null
}

function extractCount(msg) {
    let m
    m = msg.match(/[+]?(\d+)\s*(?:neut|neutral|red|hostile|unk)\w*/i)
    if (m) return parseInt(m[1])
    m = msg.match(/(?:neut|neutral|red|hostile)s?\s+(\d+)/i)
    if (m) return parseInt(m[1])
    // Leading number e.g. "5 in J9A" or "+3"
    m = msg.match(/^[+]?(\d+)\b/)
    if (m) return parseInt(m[1])
    return null
}

function extractShips(msg) {
    const lower = msg.toLowerCase()
    const found = new Set()
    for (const [hint, label] of SHIP_HINTS) {
        if (lower.includes(hint)) found.add(label)
    }
    return [...found].slice(0, 3)
}

function parseIntelText(text, lookup, now) {
    const lines = text.replace(/\r/g, '').split('\n').map(l => l.trim()).filter(Boolean)
    const entries = []

    for (const line of lines) {
        let ts = now
        let reporter = ''
        let msg = line

        const m = line.match(EVE_LINE_RE)
        if (m) {
            const parsed = parseEveTimestamp(m[1])
            if (parsed) ts = parsed
            reporter = m[2].trim()
            msg = m[3].trim()
        }

        const sys = findSystem(msg, lookup)
        if (!sys) continue

        entries.push({
            system: sys.name,
            systemId: sys.systemId,
            isPrimary: sys.isPrimary,
            count: extractCount(msg),
            isClear: CLEAR_RE.test(msg),
            ships: extractShips(msg),
            reporter,
            timestamp: ts,
            raw: msg,
        })
    }

    return entries
}

function formatAge(ms) {
    const s = Math.floor(ms / 1000)
    if (s < 60) return `${s}s`
    const m = Math.floor(s / 60)
    if (m < 60) return `${m}m`
    return `${Math.floor(m / 60)}h${m % 60}m`
}

export default function IntelChannelParser({ config }) {
    const [lastPasted, setLastPasted] = useState('')
    const [expireMin, setExpireMin] = useState(DEFAULT_EXPIRE_MIN)
    const [board, setBoard] = useState(new Map()) // system_name → entry
    const [now, setNow] = useState(() => new Date())
    const tickRef = useRef(null)

    useEffect(() => {
        tickRef.current = setInterval(() => setNow(new Date()), 30_000)
        return () => clearInterval(tickRef.current)
    }, [])

    const lookup = useMemo(() => buildSystemLookup(config), [config])

    const applyEntries = useCallback((entries) => {
        if (!entries.length) return
        setBoard(prev => {
            const next = new Map(prev)
            for (const e of entries) {
                const existing = next.get(e.system)
                if (!existing || e.timestamp >= existing.timestamp) {
                    next.set(e.system, e)
                }
            }
            return next
        })
    }, [])

    const handlePaste = useCallback((ev) => {
        ev.preventDefault()
        const text = ev.clipboardData.getData('text')
        if (!text.trim()) return
        setLastPasted(text)
        applyEntries(parseIntelText(text, lookup, new Date()))
    }, [lookup, applyEntries])

    const clearAll = () => { setBoard(new Map()); setLastPasted('') }

    const expireMs = expireMin * 60 * 1000

    const rows = useMemo(() => {
        const arr = []
        for (const [, e] of board) {
            const age = now - e.timestamp
            arr.push({ ...e, age, expired: age > expireMs })
        }
        arr.sort((a, b) => {
            if (a.isPrimary !== b.isPrimary) return b.isPrimary - a.isPrimary
            if (a.expired !== b.expired) return a.expired - b.expired
            return b.timestamp - a.timestamp
        })
        return arr
    }, [board, now, expireMs])

    const primaryAlerts = rows.filter(r => !r.expired && r.isPrimary && !r.isClear && (r.count ?? 0) > 0).length
    const activeCount = rows.filter(r => !r.expired && !r.isClear).length

    function rowBg(r) {
        if (r.expired) return 'transparent'
        if (r.isClear) return r.isPrimary ? 'rgba(0,255,136,0.07)' : 'rgba(0,255,136,0.04)'
        if ((r.count ?? 0) > 0) return r.isPrimary ? 'rgba(255,51,85,0.13)' : 'rgba(255,170,0,0.08)'
        return 'rgba(255,170,0,0.05)'
    }

    function countColor(r) {
        if (r.expired) return '#445566'
        if (r.isClear) return '#00ff88'
        if ((r.count ?? 0) > 0) return r.isPrimary ? '#ff3355' : '#ffaa00'
        return '#6a8090'
    }

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">INTEL CHANNEL</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {primaryAlerts > 0 && (
                        <span className="panel-badge" style={{ background: 'rgba(255,51,85,0.2)', borderColor: '#ff3355', color: '#ff3355' }}>
                            {primaryAlerts} PRIMARY{primaryAlerts > 1 ? '' : ''}
                        </span>
                    )}
                    {activeCount > 0 && <span className="panel-badge">{activeCount} active</span>}
                    <select
                        value={expireMin}
                        onChange={e => setExpireMin(Number(e.target.value))}
                        style={{
                            background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border-dim)',
                            color: 'var(--text-secondary)', fontFamily: 'Share Tech Mono, monospace',
                            fontSize: 10, padding: '2px 6px', cursor: 'pointer',
                        }}
                    >
                        {EXPIRE_OPTIONS.map(m => (
                            <option key={m} value={m}>EXPIRE {m}m</option>
                        ))}
                    </select>
                    {board.size > 0 && (
                        <button onClick={clearAll} style={{
                            background: 'none', border: '1px solid var(--border-dim)',
                            color: 'var(--text-secondary)', cursor: 'pointer',
                            fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                            padding: '2px 8px', letterSpacing: 1,
                        }}>CLEAR</button>
                    )}
                </div>
            </div>

            <div
                onPaste={handlePaste}
                tabIndex={0}
                style={{
                    width: '100%', minHeight: 48, background: 'rgba(0,0,0,0.3)',
                    border: '1px solid var(--border-dim)', color: 'var(--text-muted)',
                    fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                    padding: '8px 10px', boxSizing: 'border-box', outline: 'none',
                    cursor: 'text', whiteSpace: 'pre-wrap', overflowY: 'auto', maxHeight: 80,
                }}
                title="Click here then Ctrl+V to paste intel"
            >
                {lastPasted
                    ? <span style={{ color: 'var(--text-secondary)' }}>{lastPasted.slice(0, 300)}{lastPasted.length > 300 ? '…' : ''}</span>
                    : <span>Click here and paste (Ctrl+V) EVE intel channel text — supports timestamps: [ 2026.05.09 14:23:17 ] CharName {'>'} J9A-BH 3 neuts</span>
                }
            </div>

            {rows.length > 0 ? (
                <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 8 }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--border-dim)' }}>
                            {['SYSTEM', 'STATUS', 'SHIPS / NOTES', 'REPORTER', 'AGE'].map(h => (
                                <th key={h} style={{
                                    padding: '3px 8px', textAlign: 'left',
                                    fontFamily: 'Orbitron, sans-serif', fontSize: 8,
                                    letterSpacing: 2, color: 'var(--text-muted)', fontWeight: 600,
                                }}>{h}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map(r => (
                            <tr key={r.system} style={{
                                background: rowBg(r),
                                borderBottom: '1px solid rgba(0,212,255,0.05)',
                                opacity: r.expired ? 0.3 : 1,
                            }}>
                                <td style={{ padding: '5px 8px' }}>
                                    <span style={{
                                        fontFamily: 'Share Tech Mono, monospace', fontSize: 11,
                                        color: r.isPrimary ? '#00ff88' : 'var(--text-primary)',
                                        fontWeight: r.isPrimary ? 700 : 400,
                                    }}>{r.system}</span>
                                    {r.isPrimary && (
                                        <span style={{
                                            marginLeft: 5, fontSize: 7,
                                            fontFamily: 'Orbitron, sans-serif', letterSpacing: 1,
                                            color: '#00ff8866',
                                        }}>PRIMARY</span>
                                    )}
                                </td>
                                <td style={{ padding: '5px 8px', whiteSpace: 'nowrap' }}>
                                    {r.isClear ? (
                                        <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 2, color: '#00ff88' }}>CLEAR</span>
                                    ) : r.count != null ? (
                                        <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 13, fontWeight: 700, color: countColor(r) }}>
                                            {r.count} neut{r.count !== 1 ? 's' : ''}
                                        </span>
                                    ) : (
                                        <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: '#ffaa00' }}>sighted</span>
                                    )}
                                </td>
                                <td style={{ padding: '5px 8px' }}>
                                    <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-secondary)' }}>
                                        {r.ships.length ? r.ships.join(', ') : '—'}
                                    </span>
                                </td>
                                <td style={{ padding: '5px 8px' }}>
                                    <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-muted)' }}>
                                        {r.reporter || '—'}
                                    </span>
                                </td>
                                <td style={{ padding: '5px 8px', whiteSpace: 'nowrap' }}>
                                    <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: r.expired ? '#445566' : 'var(--text-secondary)' }}>
                                        {formatAge(r.age)}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            ) : (
                <div style={{ padding: '8px 0', color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                    No intel yet. Paste from EVE intel channel above — system names are auto-detected.
                </div>
            )}
        </div>
    )
}

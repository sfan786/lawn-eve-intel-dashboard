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
        if (!clean) continue
        // Exact match
        if (lookup.has(clean)) return lookup.get(clean)
        // Prefix match: "j9a" → "j9a-bh", "5t" → "5t-a3d"
        const prefix = clean + '-'
        let found = null
        let ambiguous = false
        for (const [key, val] of lookup) {
            if (key.startsWith(prefix)) {
                if (found) { ambiguous = true; break }
                found = val
            }
        }
        if (found && !ambiguous) return found
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

// EVE "Reporter > message" format without timestamp
const EVE_NOTIMESTAMP_RE = /^(.+?)\s*>\s*(.+)$/

function stripEveLinks(s) {
    return s.replace(/<url=[^>]*>([^<]*)<\/url>/gi, '$1')
}

// EVE showinfo type IDs that are NOT characters (corp=2, alliance=3, region=4, system=5)
const NON_CHAR_TYPES = new Set([2, 3, 4, 5])

// Extract {name, charId} for character links in a raw EVE line
function extractLinkedChars(rawLine) {
    const chars = []
    const re = /<url=showinfo:(\d+)\/[/]?(\d+)>([^<]+)<\/url>/gi
    let m
    while ((m = re.exec(rawLine)) !== null) {
        if (!NON_CHAR_TYPES.has(parseInt(m[1]))) {
            chars.push({ name: m[3].trim(), charId: m[2] })
        }
    }
    return chars
}

function parseIntelText(text, lookup, now) {
    const rawLines = text.replace(/\r/g, '').split('\n').map(l => l.trim()).filter(Boolean)
    const entries = []

    for (const rawLine of rawLines) {
        // Extract character links before stripping (type 5 = solar system, excluded)
        const chars = extractLinkedChars(rawLine)

        const line = stripEveLinks(rawLine).trim()
        if (!line) continue

        let ts = now
        let reporter = ''
        let msg = line

        const m = line.match(EVE_LINE_RE)
        if (m) {
            const parsed = parseEveTimestamp(m[1])
            if (parsed) ts = parsed
            reporter = m[2].trim()
            msg = m[3].trim()
        } else {
            // Fallback: "Reporter > message" without timestamp bracket
            const m2 = line.match(EVE_NOTIMESTAMP_RE)
            if (m2) {
                reporter = m2[1].trim()
                msg = m2[2].trim()
            }
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
            chars,
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

const STANDING_COLOR = {
    unknown:    '#ffaa00',
    friendly:   '#00d4ff',
    lawn:       '#00ff88',
    unresolved: '#445566',
}

const RISK_COLOR = {
    very_dangerous: '#ff2244',
    dangerous:      '#ff3355',
    moderate:       '#ffaa00',
    snuggly:        '#00d4ff',
    newbie:         '#6a8090',
    nodata:         '#334455',
}

const ROLE_COLOR = {
    TITAN:   '#ff2244',
    SUPER:   '#ff5500',
    DREAD:   '#ff7744',
    CARRIER: '#ffaa44',
    FAX:     '#ffdd00',
    BLOPS:   '#cc44ff',
    RECON:   '#aa55ff',
    BOMBER:  '#8855dd',
    T3C:     '#7755cc',
    COVOPS:  '#6644aa',
}

export default function IntelChannelParser({ config }) {
    const [lastPasted, setLastPasted] = useState('')
    const [expireMin, setExpireMin] = useState(DEFAULT_EXPIRE_MIN)
    const [board, setBoard] = useState(new Map()) // system_name → entry
    const [now, setNow] = useState(() => new Date())
    const [copied, setCopied] = useState(false)
    const [charInfoMap, setCharInfoMap] = useState({}) // name → {charId, standing, corp, alliance}
    const [charRiskMap, setCharRiskMap] = useState({}) // charId → risk tier data
    const charInfoRef = useRef({})
    const charRiskRef = useRef({})
    const tickRef = useRef(null)
    const textareaRef = useRef(null)

    useEffect(() => {
        tickRef.current = setInterval(() => setNow(new Date()), 30_000)
        return () => clearInterval(tickRef.current)
    }, [])

    const lookup = useMemo(() => buildSystemLookup(config), [config])
    const borderSet = useMemo(() => new Set((config?.border_systems || []).map(s => s.toLowerCase())), [config])

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

    const lookupChars = useCallback(async (chars) => {
        const toFetch = chars.filter(c => !(c.name in charInfoRef.current))
        if (!toFetch.length) return
        toFetch.forEach(c => { charInfoRef.current[c.name] = { charId: c.charId, standing: null } })
        try {
            const resp = await fetch('/api/local/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ names: toFetch.map(c => c.name) }),
            })
            if (!resp.ok) return
            const data = await resp.json()
            data.forEach(r => {
                charInfoRef.current[r.name] = {
                    charId: r.character_id || charInfoRef.current[r.name]?.charId,
                    standing: r.standing,
                    corp: r.corporation_name,
                    alliance: r.alliance_name,
                }
            })
            setCharInfoMap({ ...charInfoRef.current })
        } catch (e) {
            console.warn('Char lookup failed:', e)
        }
    }, [])

    const analyzeChars = useCallback(async (chars) => {
        const toFetch = chars.filter(c => c.charId && !(c.charId in charRiskRef.current))
        if (!toFetch.length) return
        toFetch.forEach(c => { charRiskRef.current[c.charId] = null })
        try {
            const resp = await fetch('/api/chars/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ char_ids: toFetch.map(c => c.charId) }),
            })
            if (!resp.ok) return
            const data = await resp.json()
            Object.assign(charRiskRef.current, data)
            setCharRiskMap({ ...charRiskRef.current })
        } catch (e) {
            console.warn('Char analyze failed:', e)
        }
    }, [])

    const handlePaste = useCallback((ev) => {
        ev.preventDefault()
        const text = ev.clipboardData.getData('text')
        if (!text.trim()) return
        setLastPasted(text)
        if (textareaRef.current) {
            textareaRef.current.value = text.slice(0, 300) + (text.length > 300 ? '…' : '')
        }
        const entries = parseIntelText(text, lookup, new Date())
        applyEntries(entries)
        const allChars = entries.flatMap(e => e.chars || [])
        if (allChars.length) {
            lookupChars(allChars)
            analyzeChars(allChars)
        }
    }, [lookup, applyEntries, lookupChars, analyzeChars])

    const clearAll = () => {
        setBoard(new Map())
        setLastPasted('')
        charInfoRef.current = {}
        charRiskRef.current = {}
        setCharInfoMap({})
        setCharRiskMap({})
        if (textareaRef.current) textareaRef.current.value = ''
    }

    const expireMs = expireMin * 60 * 1000

    const rows = useMemo(() => {
        const arr = []
        for (const [, e] of board) {
            const age = now - e.timestamp
            const isBorder = borderSet.has(e.system.toLowerCase())
            arr.push({ ...e, age, expired: age > expireMs, isBorder })
        }
        arr.sort((a, b) => {
            // border+primary first, then other primaries, then non-primary
            const rankA = a.isPrimary ? (a.isBorder ? 2 : 1) : 0
            const rankB = b.isPrimary ? (b.isBorder ? 2 : 1) : 0
            if (rankA !== rankB) return rankB - rankA
            if (a.expired !== b.expired) return a.expired - b.expired
            return b.timestamp - a.timestamp
        })
        return arr
    }, [board, now, expireMs, borderSet])

    const primaryAlerts = rows.filter(r => !r.expired && r.isPrimary && !r.isClear && (r.count ?? 0) > 0).length
    const activeCount = rows.filter(r => !r.expired && !r.isClear).length

    const copyBoard = useCallback(async () => {
        const lines = rows
            .filter(r => !r.expired)
            .map(r => {
                const tags = [r.isBorder && 'GATE', r.isPrimary && !r.isBorder && 'PRIMARY'].filter(Boolean).join('/')
                const prefix = tags ? `[${tags}] ` : ''
                const status = r.isClear ? 'CLEAR' : r.count != null ? `${r.count} neuts` : 'sighted'
                const detail = r.ships.length ? r.ships.join(', ') : r.chars?.length ? r.chars.map(c => c.name).join(', ') : ''
                const detailStr = detail ? ` (${detail})` : ''
                return `${prefix}${r.system}: ${status}${detailStr} — ${formatAge(r.age)} ago`
            })
        const text = lines.join('\n')
        try { await navigator.clipboard.writeText(text) } catch {
            const el = document.createElement('textarea')
            el.value = text; document.body.appendChild(el); el.select()
            document.execCommand('copy'); document.body.removeChild(el)
        }
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }, [rows])

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
                    {rows.some(r => !r.expired) && (
                        <button onClick={copyBoard} style={{
                            background: 'none',
                            border: `1px solid ${copied ? '#00ff8866' : 'var(--border-dim)'}`,
                            color: copied ? '#00ff88' : 'var(--text-secondary)', cursor: 'pointer',
                            fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                            padding: '2px 8px', letterSpacing: 1,
                            transition: 'color 0.2s, border-color 0.2s',
                        }}>{copied ? 'COPIED!' : 'COPY'}</button>
                    )}
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

            <textarea
                ref={textareaRef}
                onPaste={handlePaste}
                defaultValue=""
                placeholder="Click here and paste (Ctrl+V) EVE intel channel text — e.g. [ 2026.05.09 14:23:17 ] CharName > J9A-BH 3 neuts"
                style={{
                    width: '100%', minHeight: 48, maxHeight: 80, background: 'rgba(0,0,0,0.3)',
                    border: '1px solid var(--border-dim)', color: 'var(--text-secondary)',
                    fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                    padding: '8px 10px', boxSizing: 'border-box', outline: 'none',
                    resize: 'none', overflowY: 'auto',
                }}
            />

            {lastPasted && rows.length === 0 && (
                <div style={{ padding: '6px 0', color: '#ffaa00', fontFamily: 'Share Tech Mono, monospace', fontSize: 10 }}>
                    Paste captured — no recognized system names found. System must be in Perrigen Falls or a listed neighbor system.
                </div>
            )}

            {rows.length > 0 ? (
                <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 8 }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--border-dim)' }}>
                            {['SYSTEM', 'STATUS', 'SHIPS / CHARS', 'REPORTER', 'AGE'].map(h => (
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
                                        color: r.isBorder ? '#ffcc44' : r.isPrimary ? '#00ff88' : 'var(--text-primary)',
                                        fontWeight: r.isPrimary ? 700 : 400,
                                    }}>{r.system}</span>
                                    {r.isBorder && (
                                        <span style={{
                                            marginLeft: 5, fontSize: 7,
                                            fontFamily: 'Orbitron, sans-serif', letterSpacing: 1,
                                            color: '#ffcc4499',
                                        }}>GATE</span>
                                    )}
                                    {r.isPrimary && !r.isBorder && (
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
                                    {r.chars?.length ? (
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                                            {r.chars.map(c => {
                                                const info = charInfoMap[c.name]
                                                const nameColor = STANDING_COLOR[info?.standing] ?? '#6a8090'
                                                const risk = c.charId ? charRiskMap[c.charId] : null
                                                const riskColor = RISK_COLOR[risk?.tier] ?? '#334455'
                                                const affil = info?.alliance || info?.corp
                                                const href = c.charId ? `https://zkillboard.com/character/${c.charId}/` : null
                                                return (
                                                    <div key={c.name} style={{ display: 'flex', alignItems: 'center', gap: 5, flexWrap: 'wrap' }}>
                                                        {href
                                                            ? <a href={href} target="_blank" rel="noopener noreferrer"
                                                                style={{ color: nameColor, textDecoration: 'none', fontFamily: 'Share Tech Mono, monospace', fontSize: 9 }}>
                                                                {c.name}
                                                              </a>
                                                            : <span style={{ color: nameColor, fontFamily: 'Share Tech Mono, monospace', fontSize: 9 }}>{c.name}</span>
                                                        }
                                                        {affil && <span style={{ fontSize: 8, color: '#445566', fontFamily: 'Share Tech Mono, monospace' }}>[{affil}]</span>}
                                                        {risk && risk.tier !== 'nodata' && (
                                                            <>
                                                                <span style={{
                                                                    fontSize: 8, fontFamily: 'Orbitron, sans-serif', letterSpacing: 1,
                                                                    color: riskColor, whiteSpace: 'nowrap',
                                                                }}>
                                                                    {risk.label} · {risk.kills >= 1000 ? `${(risk.kills/1000).toFixed(1)}k` : risk.kills} kills · {risk.isk_eff}%
                                                                </span>
                                                                {(risk.roles || []).map(role => (
                                                                    <span key={role} style={{
                                                                        fontSize: 7, fontFamily: 'Orbitron, sans-serif', letterSpacing: 1, fontWeight: 700,
                                                                        color: ROLE_COLOR[role] ?? '#aaaaaa',
                                                                        border: `1px solid ${ROLE_COLOR[role] ?? '#aaaaaa'}44`,
                                                                        padding: '0 3px', borderRadius: 2, whiteSpace: 'nowrap',
                                                                    }}>{role}</span>
                                                                ))}
                                                            </>
                                                        )}
                                                    </div>
                                                )
                                            })}
                                        </div>
                                    ) : (
                                        <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-secondary)' }}>
                                            {r.ships.length ? r.ships.join(', ') : '—'}
                                        </span>
                                    )}
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

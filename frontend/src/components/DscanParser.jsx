import React, { useState, useMemo } from 'react'
import CornerBrackets from './common/CornerBrackets'

// Lowercase-keyed version built at module load for case-insensitive matching
const GROUP_CATEGORIES_LOWER = {}

const GROUP_CATEGORIES = {
    'Titan': 'SUPER', 'Supercarrier': 'SUPER',
    'Dreadnought': 'CAPITAL', 'Carrier': 'CAPITAL', 'Force Auxiliary': 'CAPITAL',
    'Black Ops': 'CAPITAL',
    'Battleship': 'BATTLESHIP', 'Marauder': 'BATTLESHIP',
    'Battlecruiser': 'BATTLECRUISER', 'Command Ship': 'BATTLECRUISER',
    'Attack Battlecruiser': 'BATTLECRUISER',
    'Strategic Cruiser': 'DOCTRINE', 'Heavy Assault Cruiser': 'DOCTRINE',
    'Force Recon Ship': 'RECON', 'Combat Recon Ship': 'RECON',
    'Logistics Cruiser': 'SUPPORT', 'Logistics Frigate': 'SUPPORT',
    'Interceptor': 'TACKLE', 'Interdictor': 'TACKLE', 'Heavy Interdictor': 'TACKLE',
    'Cruiser': 'CRUISER', 'Electronic Attack Ship': 'EWAR',
    'Covert Ops': 'COVOPS', 'Stealth Bomber': 'BOMBER',
    'Destroyer': 'DESTROYER', 'Assault Frigate': 'FRIGATE', 'Frigate': 'FRIGATE',
    'Capsule': 'POD',
    // Upwell structure groups
    'Citadel': 'STRUCTURE', 'Engineering Complex': 'STRUCTURE', 'Refinery': 'STRUCTURE',
    'Jump Gate': 'STRUCTURE',             // Ansiblex Jump Gate
    'Orbital Infrastructure': 'STRUCTURE', // Player-owned Customs Office (POCO)
    'Control Tower': 'STRUCTURE',          // POS towers
    'Moon Drill': 'STRUCTURE',             // Metenox Moon Harvester
    'Starbase Defense': 'STRUCTURE',       // POS guns/batteries
    'Cynosural Beacon': 'STRUCTURE',       // Upwell Cyno Beacon
    // Upwell type-name fallbacks (for when Group column is missing/blank)
    'Astrahus': 'STRUCTURE', 'Fortizar': 'STRUCTURE', 'Keepstar': 'STRUCTURE',
    'Raitaru': 'STRUCTURE', 'Azbel': 'STRUCTURE', 'Sotiyo': 'STRUCTURE',
    'Athanor': 'STRUCTURE', 'Tatara': 'STRUCTURE',
    'Ansiblex Jump Gate': 'STRUCTURE', 'Metenox Moon Harvester': 'STRUCTURE',
    'Customs Office': 'STRUCTURE',
    // Deployables
    'Mobile Depot': 'DEPLOYABLE', 'Mobile Cynosural Inhibitor': 'DEPLOYABLE',
    'Mobile Cyno Inhibitor': 'DEPLOYABLE',
    'Mobile Large Warp Disruptor': 'BUBBLE', 'Mobile Medium Warp Disruptor': 'BUBBLE',
    'Mobile Small Warp Disruptor': 'BUBBLE',
    'Scanner Probe': 'PROBE', 'Survey Probe': 'PROBE', 'Combat Scanner Probe': 'PROBE',
    'Sovereignty Blockade Unit': 'SOV', 'Infrastructure Hub': 'SOV',
}

// Populate lowercase map after GROUP_CATEGORIES is defined
Object.entries(GROUP_CATEGORIES).forEach(([k, v]) => { GROUP_CATEGORIES_LOWER[k.toLowerCase()] = v })

// Regex to detect distance-like fields so we skip them during column scanning
const DISTANCE_RE = /^[\d,.*-]|km$|au$| m$/i

const CATEGORY_ORDER = [
    'SUPER', 'CAPITAL', 'BATTLESHIP', 'BATTLECRUISER', 'DOCTRINE', 'RECON',
    'SUPPORT', 'TACKLE', 'CRUISER', 'EWAR', 'BOMBER', 'COVOPS',
    'DESTROYER', 'FRIGATE', 'POD',
    'STRUCTURE', 'DEPLOYABLE', 'BUBBLE', 'SOV', 'PROBE',
]

const CATEGORY_LABELS = {
    SUPER: 'Supercapital', CAPITAL: 'Capital', BATTLESHIP: 'Battleship',
    BATTLECRUISER: 'Battlecruiser', DOCTRINE: 'T3/HAC', RECON: 'Recon',
    SUPPORT: 'Logistics', TACKLE: 'Tackle/Dictor', CRUISER: 'Cruiser',
    EWAR: 'EWAR', BOMBER: 'Bomber', COVOPS: 'Covert Ops',
    DESTROYER: 'Destroyer', FRIGATE: 'Frigate', POD: 'Pod',
    STRUCTURE: 'Structure', DEPLOYABLE: 'Deployable', BUBBLE: 'Warp Bubble',
    SOV: 'Sov Object', PROBE: 'Probe',
}

const CATEGORY_COLORS = {
    SUPER: '#ff3355', CAPITAL: '#ff6677', BATTLESHIP: '#ffaa00',
    BATTLECRUISER: '#ffcc44', DOCTRINE: '#ff8844', RECON: '#ff9966',
    SUPPORT: '#00d4ff', TACKLE: '#cc88ff', CRUISER: '#88aaff',
    EWAR: '#aa88ff', BOMBER: '#9966cc', COVOPS: '#7755aa',
    DESTROYER: '#6699aa', FRIGATE: '#4488aa', POD: '#336677',
    STRUCTURE: '#66aa88', DEPLOYABLE: '#558877', BUBBLE: '#ddaa44',
    SOV: '#aaaaaa', PROBE: '#445566',
}

const THREAT_TIERS = [
    { tier: 'CRITICAL', color: '#ff3355', bg: 'rgba(255,51,85,0.15)', test: cats => cats.has('SUPER') },
    { tier: 'HIGH',     color: '#ff6677', bg: 'rgba(255,102,119,0.12)', test: cats => cats.has('CAPITAL') },
    { tier: 'MEDIUM',   color: '#ffaa00', bg: 'rgba(255,170,0,0.12)', test: cats => cats.has('DOCTRINE') || cats.has('RECON') },
    { tier: 'LOW',      color: '#ffcc44', bg: 'rgba(255,204,68,0.10)', test: cats => cats.has('BATTLESHIP') || cats.has('BATTLECRUISER') || cats.has('SUPPORT') || cats.has('TACKLE') },
    { tier: 'MINIMAL',  color: '#00ff88', bg: 'rgba(0,255,136,0.08)', test: () => true },
]

function parseDscan(raw) {
    if (!raw.trim()) return null

    // Normalise line endings (Windows \r\n → \n)
    const lines = raw.replace(/\r/g, '').trim().split('\n').map(l => l.trim()).filter(Boolean)
    const ships = []
    const structures = []
    let unrecognized = 0
    const unrecognizedSamples = []

    for (const line of lines) {
        const parts = line.split('\t')
        if (parts.length < 2) { unrecognized++; unrecognizedSamples.push(line); continue }

        // Scan every column for a GROUP_CATEGORIES match (case-insensitive).
        // Skip columns that look like distances ("1,234 km", "2.1 AU", "*", "-").
        // This handles any column order EVE might use.
        let cat = null
        let matchedField = ''
        for (const part of parts) {
            const val = part.trim()
            if (!val || DISTANCE_RE.test(val)) continue
            const found = GROUP_CATEGORIES[val] || GROUP_CATEGORIES_LOWER[val.toLowerCase()]
            if (found) { cat = found; matchedField = val; break }
        }

        if (!cat) { unrecognized++; if (unrecognizedSamples.length < 5) unrecognizedSamples.push(line); continue }

        // Name: first column that isn't a distance and isn't the matched type/group field
        const name = parts.find(p => {
            const v = p.trim()
            return v && !DISTANCE_RE.test(v) && v !== matchedField
        })?.trim() || matchedField

        const entry = { name, type: matchedField, category: cat }

        if (['STRUCTURE', 'DEPLOYABLE', 'BUBBLE', 'SOV'].includes(cat)) {
            structures.push(entry)
        } else if (cat === 'PROBE') {
            // skip probes
        } else {
            ships.push(entry)
        }
    }

    // Group ships by category
    const byCat = {}
    for (const s of ships) {
        if (!byCat[s.category]) byCat[s.category] = { count: 0, types: {} }
        byCat[s.category].count++
        byCat[s.category].types[s.type] = (byCat[s.category].types[s.type] || 0) + 1
    }

    const presentCats = new Set(Object.keys(byCat))
    const threat = ships.length === 0
        ? { tier: 'CLEAR', color: '#00ff88', bg: 'rgba(0,255,136,0.08)' }
        : (THREAT_TIERS.find(t => t.test(presentCats)) || THREAT_TIERS[THREAT_TIERS.length - 1])

    return { byCat, structures, ships: ships.length, total: lines.length, unrecognized, unrecognizedSamples, threat }
}

export default function DscanParser() {
    const [rawInput, setRawInput] = useState('')

    const result = useMemo(() => parseDscan(rawInput), [rawInput])

    const shipCatRows = result
        ? CATEGORY_ORDER.filter(cat => result.byCat[cat]).map(cat => ({
            cat,
            count: result.byCat[cat].count,
            types: result.byCat[cat].types,
        }))
        : []

    // Group structures by type
    const structureCounts = result?.structures.reduce((acc, s) => {
        acc[s.type] = (acc[s.type] || 0) + 1
        return acc
    }, {}) || {}

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">DSCAN PARSER</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {result && <span className="panel-badge">{result.ships} ships · {result.total} total</span>}
                    {rawInput && (
                        <button
                            onClick={() => setRawInput('')}
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

            <textarea
                value={rawInput}
                onChange={e => setRawInput(e.target.value)}
                placeholder="Paste EVE directional scan output here..."
                style={{
                    width: '100%', minHeight: 80, background: 'rgba(0,0,0,0.3)',
                    border: '1px solid var(--border-dim)', color: 'var(--text-primary)',
                    fontFamily: 'Share Tech Mono, monospace', fontSize: 11,
                    padding: '8px 10px', resize: 'vertical', outline: 'none',
                    boxSizing: 'border-box',
                }}
            />

            {result && (
                <>
                    {/* Threat Banner */}
                    <div style={{
                        marginTop: 10, padding: '7px 12px',
                        background: result.threat.bg,
                        border: `1px solid ${result.threat.color}`,
                        display: 'flex', alignItems: 'center', gap: 12,
                    }}>
                        <span style={{
                            fontFamily: 'Orbitron, sans-serif', fontSize: 11,
                            fontWeight: 700, letterSpacing: 3,
                            color: result.threat.color,
                        }}>THREAT: {result.threat.tier}</span>
                        <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: 'var(--text-secondary)' }}>
                            {result.ships} combat ships · {result.structures.length} structures
                            {result.unrecognized > 0 && ` · ${result.unrecognized} unrecognized`}
                        </span>
                    </div>

                    {/* Ship Groups */}
                    {shipCatRows.length > 0 && (
                        <div style={{ marginTop: 10 }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <tbody>
                                    {shipCatRows.map(({ cat, count, types }) => (
                                        <tr key={cat} style={{ borderBottom: '1px solid var(--border-dim)' }}>
                                            <td style={{ padding: '5px 8px', width: 120 }}>
                                                <span style={{
                                                    fontFamily: 'Orbitron, sans-serif', fontSize: 9,
                                                    fontWeight: 600, letterSpacing: 2,
                                                    color: CATEGORY_COLORS[cat],
                                                }}>{CATEGORY_LABELS[cat]}</span>
                                            </td>
                                            <td style={{ padding: '5px 8px', width: 40, textAlign: 'right' }}>
                                                <span style={{
                                                    fontFamily: 'Share Tech Mono, monospace', fontSize: 12,
                                                    color: CATEGORY_COLORS[cat], fontWeight: 700,
                                                }}>{count}</span>
                                            </td>
                                            <td style={{ padding: '5px 8px' }}>
                                                <span style={{
                                                    fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                                                    color: 'var(--text-secondary)',
                                                }}>
                                                    {Object.entries(types)
                                                        .sort((a, b) => b[1] - a[1])
                                                        .map(([t, n]) => n > 1 ? `${t} ×${n}` : t)
                                                        .join(', ')}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Structures / Deployables */}
                    {result.structures.length > 0 && (
                        <div style={{ marginTop: 8, padding: '6px 8px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-dim)' }}>
                            <span style={{
                                fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 2,
                                color: 'var(--text-secondary)', marginRight: 10,
                            }}>OBJECTS</span>
                            {Object.entries(structureCounts).map(([type, n]) => (
                                <span key={type} style={{
                                    fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                                    color: 'var(--text-primary)', marginRight: 12,
                                }}>
                                    {type}{n > 1 ? ` ×${n}` : ''}
                                </span>
                            ))}
                        </div>
                    )}

                    {result.ships === 0 && result.structures.length === 0 && (
                        <div style={{ padding: '8px 0', color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                            No recognized ships or structures found.
                        </div>
                    )}

                    {/* Debug: show sample unrecognized lines so we can identify format issues */}
                    {result.unrecognized > 0 && result.unrecognizedSamples.length > 0 && (
                        <div style={{ marginTop: 8, padding: '6px 8px', background: 'rgba(255,170,0,0.05)', border: '1px solid var(--amber-dim)' }}>
                            <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 2, color: 'var(--amber)', marginRight: 8 }}>
                                UNRECOGNIZED ({result.unrecognized})
                            </span>
                            <div style={{ marginTop: 4 }}>
                                {result.unrecognizedSamples.map((l, i) => (
                                    <div key={i} style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-muted)', whiteSpace: 'pre' }}>
                                        {l.replace(/\t/g, ' → ')}
                                    </div>
                                ))}
                                {result.unrecognized > result.unrecognizedSamples.length && (
                                    <div style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-muted)' }}>
                                        …and {result.unrecognized - result.unrecognizedSamples.length} more
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </>
            )}

            {!rawInput && (
                <div style={{ padding: '8px 0', color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                    In EVE: open D-Scan, select all results (Ctrl+A), copy (Ctrl+C), paste above.
                </div>
            )}
        </div>
    )
}

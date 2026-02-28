import React, { useState, useEffect } from 'react'
import CornerBrackets from './common/CornerBrackets'

const PLANET_TYPES = {
    "Barren":    { color: "#a08060", short: "BAR" },
    "Temperate": { color: "#44bb55", short: "TMP" },
    "Gas":       { color: "#ccaa00", short: "GAS" },
    "Ice":       { color: "#88ccff", short: "ICE" },
    "Lava":      { color: "#dd4422", short: "LAV" },
    "Oceanic":   { color: "#2266dd", short: "OCE" },
    "Storm":     { color: "#9955cc", short: "STM" },
    "Plasma":    { color: "#ff7700", short: "PLS" },
}

const PRIORITY_PRODUCTS = [
    {
        name: "Fuel Blocks",
        short: "FB",
        priority: "critical",
        required: ["Temperate", "Ice", "Gas", "Lava"],
        note: "Temperate+Ice+Gas+Lava cover Robotics, Coolant, Oxygen, Mechanical Parts"
    },
    {
        name: "Battleship Components",
        short: "BSC",
        priority: "high",
        required: ["Lava", "Storm", "Plasma", "Barren", "Temperate"],
        note: "Heavy/Noble Metals + Non-CS Crystals for mechanical/electronic components"
    },
    {
        name: "P4 Advanced",
        short: "P4",
        priority: "high",
        required: ["Temperate", "Oceanic", "Gas", "Lava", "Storm", "Plasma"],
        note: "P4 chains need all specialty types — Temperate and Oceanic are rarest in nullsec"
    },
]

// Strategic importance per type: determined by highest-priority product that needs it
// PRIORITY_PRODUCTS is ordered critical-first, so first match wins
const STRATEGIC_IMPORTANCE = {}
for (const type of Object.keys(PLANET_TYPES)) {
    for (const product of PRIORITY_PRODUCTS) {
        if (product.required.includes(type)) {
            STRATEGIC_IMPORTANCE[type] = product.priority
            break
        }
    }
}
// critical types (Fuel Blocks): Temperate, Ice, Gas, Lava → amber ◆
// high-only types: Storm, Plasma, Barren, Oceanic → cyan ◆
const IMPORTANCE_COLOR = { critical: '#ffaa00', high: '#00d4ff' }

const LAWN_SYSTEMS_ORDER = [
    "UDVW-O", "UJXC-B", "F48K-D", "1-KCSA", "XTJ-5Q", "JT2I-7", "N-JK02",
    "FB5U-I", "BZ-BCK", "J-OAH2", "O5-YNW", "86L-9F", "5-VFC6", "IUU3-L", "S-LHPJ"
]
const CBBM_SYSTEMS = new Set(["UDVW-O", "UJXC-B", "F48K-D", "1-KCSA", "XTJ-5Q", "JT2I-7", "N-JK02"])
const TYPE_SORT_ORDER = ["Oceanic", "Storm", "Plasma", "Ice", "Lava", "Temperate", "Gas", "Barren"]

function extractType(typeStr) {
    const m = typeStr.match(/\(([^)]+)\)/)
    return m ? m[1] : typeStr
}

function TypeBadge({ type, count, selectedProduct }) {
    const meta = PLANET_TYPES[type]
    if (!meta) return null

    const isFiltering = !!selectedProduct
    const isHighlighted = isFiltering && selectedProduct.required.includes(type)
    const isDimmed = isFiltering && !isHighlighted
    const importance = STRATEGIC_IMPORTANCE[type]
    const importanceColor = importance ? IMPORTANCE_COLOR[importance] : null

    return (
        <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 2,
            background: isHighlighted ? `${meta.color}33` : `${meta.color}18`,
            border: `1px solid ${isHighlighted ? meta.color : `${meta.color}55`}`,
            boxShadow: isHighlighted ? `0 0 6px ${meta.color}66` : 'none',
            color: meta.color,
            fontFamily: 'Share Tech Mono, monospace',
            fontSize: 9,
            padding: '1px 4px',
            borderRadius: 2,
            whiteSpace: 'nowrap',
            opacity: isDimmed ? 0.18 : 1,
            transition: 'opacity 0.15s, box-shadow 0.15s, border-color 0.15s',
        }}>
            {meta.short}{count > 1 ? ` ×${count}` : ''}
            {importanceColor && (
                <span style={{
                    color: isFiltering ? (isHighlighted ? importanceColor : 'transparent') : importanceColor,
                    fontSize: 7,
                    lineHeight: 1,
                    transition: 'color 0.15s',
                }}>◆</span>
            )}
        </span>
    )
}

function SystemCard({ name, planets, selectedProduct }) {
    const constellation = CBBM_SYSTEMS.has(name) ? "6-CBBM" : "2Q-8WA"

    const typeCounts = {}
    planets.forEach(p => {
        const t = extractType(p.type)
        typeCounts[t] = (typeCounts[t] || 0) + 1
    })

    const sortedTypes = Object.entries(typeCounts).sort(([a], [b]) => {
        const ai = TYPE_SORT_ORDER.indexOf(a), bi = TYPE_SORT_ORDER.indexOf(b)
        if (ai === -1 && bi === -1) return a.localeCompare(b)
        if (ai === -1) return 1
        if (bi === -1) return -1
        return ai - bi
    })

    // When filtering, dim the whole card if it has none of the required types
    const hasRelevantType = !selectedProduct ||
        selectedProduct.required.some(t => typeCounts[t])
    const cardOpacity = selectedProduct && !hasRelevantType ? 0.3 : 1

    return (
        <div style={{
            background: hasRelevantType ? 'rgba(0,212,255,0.03)' : 'rgba(0,0,0,0)',
            border: `1px solid ${hasRelevantType ? 'rgba(0,212,255,0.12)' : 'rgba(255,255,255,0.04)'}`,
            padding: '6px 8px',
            opacity: cardOpacity,
            transition: 'opacity 0.15s, border-color 0.15s',
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
                <span style={{
                    fontFamily: 'Orbitron, sans-serif',
                    fontSize: 10,
                    fontWeight: 'bold',
                    color: 'var(--text-primary)',
                    letterSpacing: 1,
                }}>{name}</span>
                <span style={{ fontSize: 8, color: 'var(--text-muted)' }}>{constellation} · {planets.length}p</span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                {sortedTypes.map(([type, count]) => (
                    <TypeBadge key={type} type={type} count={count} selectedProduct={selectedProduct} />
                ))}
            </div>
        </div>
    )
}

function CoverageRow({ piData, selectedProduct, onSelect }) {
    const allTypes = new Set()
    Object.values(piData).forEach(planets =>
        planets.forEach(p => allTypes.add(extractType(p.type)))
    )

    return (
        <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 6,
            padding: '6px 8px',
            background: 'rgba(0,0,0,0.2)',
            border: '1px solid var(--border-dim)',
            marginBottom: 8,
            alignItems: 'center',
        }}>
            <span style={{ fontSize: 8, color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', marginRight: 2 }}>
                FILTER:
            </span>
            {PRIORITY_PRODUCTS.map(product => {
                const covered = product.required.filter(t => allTypes.has(t))
                const missing = product.required.filter(t => !allTypes.has(t))
                const isFullyCovered = missing.length === 0
                const isPartial = covered.length > 0 && missing.length > 0
                const coverIcon = isFullyCovered ? '✓' : isPartial ? '⚠' : '✗'
                const coverColor = isFullyCovered ? '#00ff88' : isPartial ? '#ffaa00' : '#ff3355'
                const isActive = selectedProduct?.name === product.name
                const priorityColor = product.priority === 'critical' ? '#ff3355' : '#ffaa00'

                return (
                    <button
                        key={product.name}
                        onClick={() => onSelect(isActive ? null : product)}
                        title={`${product.note}${missing.length ? `\nMissing: ${missing.join(', ')}` : '\nAll types covered'}`}
                        style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 4,
                            background: isActive ? `${priorityColor}22` : 'transparent',
                            border: `1px solid ${isActive ? priorityColor : 'rgba(255,255,255,0.1)'}`,
                            boxShadow: isActive ? `0 0 8px ${priorityColor}44` : 'none',
                            padding: '3px 7px',
                            cursor: 'pointer',
                            borderRadius: 2,
                            transition: 'all 0.15s',
                        }}
                    >
                        <span style={{ color: coverColor, fontFamily: 'Share Tech Mono, monospace', fontSize: 11, fontWeight: 'bold' }}>{coverIcon}</span>
                        <span style={{ color: priorityColor, fontFamily: 'Share Tech Mono, monospace', fontSize: 8, border: `1px solid ${priorityColor}44`, padding: '0 3px' }}>
                            {product.priority === 'critical' ? 'CRIT' : 'HIGH'}
                        </span>
                        <span style={{ color: isActive ? '#fff' : '#00d4ff', fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 0.5 }}>
                            {product.name}
                        </span>
                        {isActive && (
                            <span style={{ color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 8 }}>
                                [{product.required.map(t => PLANET_TYPES[t]?.short || t).join(' ')}]
                            </span>
                        )}
                    </button>
                )
            })}
            {selectedProduct && (
                <span style={{ fontSize: 8, color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', marginLeft: 4 }}>
                    click to clear
                </span>
            )}
        </div>
    )
}

function TypeSummary({ piData, selectedProduct }) {
    const counts = {}
    Object.values(piData).forEach(planets =>
        planets.forEach(p => {
            const t = extractType(p.type)
            counts[t] = (counts[t] || 0) + 1
        })
    )

    return (
        <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 8,
            paddingTop: 8,
            borderTop: '1px solid var(--border-dim)',
            fontFamily: 'Share Tech Mono, monospace',
            fontSize: 10,
        }}>
            {Object.entries(PLANET_TYPES).map(([type, meta]) => {
                const count = counts[type] || 0
                const isFiltering = !!selectedProduct
                const isHighlighted = isFiltering && selectedProduct.required.includes(type)
                const isDimmed = isFiltering && !isHighlighted
                const importance = STRATEGIC_IMPORTANCE[type]
                const importanceColor = importance ? IMPORTANCE_COLOR[importance] : null
                return (
                    <span key={type} style={{
                        color: count > 0 ? meta.color : '#333a40',
                        opacity: isDimmed ? 0.2 : 1,
                        transition: 'opacity 0.15s',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 2,
                    }}>
                        {meta.short}: <strong>{count}</strong>
                        {importanceColor && count > 0 && (
                            <span style={{ color: importanceColor, fontSize: 7 }}>◆</span>
                        )}
                    </span>
                )
            })}
        </div>
    )
}

function Legend({ selectedProduct }) {
    return (
        <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 8,
            paddingTop: 6,
            borderTop: '1px solid var(--border-dim)',
            marginTop: 4,
            fontFamily: 'Share Tech Mono, monospace',
            fontSize: 9,
        }}>
            {Object.entries(PLANET_TYPES).map(([type, meta]) => {
                const importance = STRATEGIC_IMPORTANCE[type]
                const importanceColor = importance ? IMPORTANCE_COLOR[importance] : null
                const isFiltering = !!selectedProduct
                const isHighlighted = isFiltering && selectedProduct.required.includes(type)
                const isDimmed = isFiltering && !isHighlighted
                return (
                    <span key={type} style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 3,
                        opacity: isDimmed ? 0.2 : 1,
                        transition: 'opacity 0.15s',
                    }}>
                        <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: meta.color }} />
                        <span style={{ color: meta.color }}>{meta.short}</span>
                        <span style={{ color: '#4a5a60' }}>{type}</span>
                        {importanceColor && <span style={{ color: importanceColor, fontSize: 7 }}>◆</span>}
                    </span>
                )
            })}
            <span style={{ color: '#4a5a60', marginLeft: 4 }}>
                ◆ <span style={{ color: '#ffaa00' }}>critical</span> / <span style={{ color: '#00d4ff' }}>high</span> priority chain
            </span>
        </div>
    )
}

export default function PlanetaryIntel() {
    const [piData, setPiData] = useState(null)
    const [error, setError] = useState(null)
    const [selectedProduct, setSelectedProduct] = useState(null)

    useEffect(() => {
        fetch('/api/pi_data')
            .then(r => {
                if (!r.ok) throw new Error(`PI data unavailable: ${r.status}`)
                return r.json()
            })
            .then(data => setPiData(data.pi_data))
            .catch(e => setError(e.message))
    }, [])

    if (error) return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header"><span className="panel-title">Planetary Interaction</span></div>
            <div style={{ padding: 10, color: '#ff3355', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>{error}</div>
        </div>
    )

    if (!piData) return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header"><span className="panel-title">Planetary Interaction</span></div>
            <div style={{ padding: 10, color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>Loading PI data...</div>
        </div>
    )

    const totalPlanets = Object.values(piData).reduce((s, p) => s + p.length, 0)
    const systemCount = Object.keys(piData).length
    const orderedSystems = [
        ...LAWN_SYSTEMS_ORDER.filter(s => piData[s]),
        ...Object.keys(piData).filter(s => !LAWN_SYSTEMS_ORDER.includes(s)).sort()
    ]

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">Planetary Interaction</span>
                <span className="panel-badge">{totalPlanets} planets · {systemCount} systems</span>
            </div>
            <CoverageRow piData={piData} selectedProduct={selectedProduct} onSelect={setSelectedProduct} />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 6, marginBottom: 8 }}>
                {orderedSystems.map(name => (
                    <SystemCard key={name} name={name} planets={piData[name]} selectedProduct={selectedProduct} />
                ))}
            </div>
            <TypeSummary piData={piData} selectedProduct={selectedProduct} />
            <Legend selectedProduct={selectedProduct} />
        </div>
    )
}

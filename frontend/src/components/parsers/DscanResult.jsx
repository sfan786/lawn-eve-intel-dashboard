import React from 'react'
import {
    CATEGORY_COLORS, CATEGORY_LABELS, formatTypes, shipCatRows, structureCounts,
} from '../../utils/dscanCategories'

/**
 * Presentational half of the D-scan parser: renders a parse result and nothing
 * else. No input, no fetching, no auth — that is what lets the live parser and
 * the shared read-only page draw the same thing from the same code.
 *
 * `bannerActions` is slotted into the right-hand side of the threat banner
 * (the live parser puts the AI button there; a share puts nothing), and
 * `summarySlot` renders directly beneath it.
 */
export default function DscanResult({ result, bannerActions = null, summarySlot = null }) {
    if (!result) return null

    const catRows = shipCatRows(result)
    const structures = structureCounts(result)

    return (
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
                {bannerActions && <>
                    <div style={{ flex: 1 }} />
                    {bannerActions}
                </>}
            </div>

            {summarySlot}

            {/* Ship Groups */}
            {catRows.length > 0 && (
                <div style={{ marginTop: 10 }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <tbody>
                            {catRows.map(({ cat, count, types }) => (
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
                                            {formatTypes(types)}
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
                    {Object.entries(structures).map(([type, n]) => (
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
    )
}

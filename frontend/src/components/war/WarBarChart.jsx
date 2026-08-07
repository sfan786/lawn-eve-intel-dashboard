import React from 'react'
import { formatIsk } from '../../utils/formatters'
import { periodLabel } from '../../utils/warHelpers'

/**
 * Two-sided time series: each period is a mirrored pair of bars, side A above
 * the axis and side B below.
 *
 * Mirrored rather than stacked or grouped because the question this chart
 * answers is "who was winning that week", and a shared baseline lets you read
 * the balance from the silhouette alone. A stacked bar would only show the
 * combined violence, which is not the question.
 */
export default function WarBarChart({ series, sideA, sideB, metric = 'kills', height = 150 }) {
    const aKey = metric === 'isk' ? 'a_isk' : 'a_kills'
    const bKey = metric === 'isk' ? 'b_isk' : 'b_kills'
    const fmt = metric === 'isk' ? formatIsk : (v) => (v || 0).toLocaleString()

    if (!series?.length) {
        return (
            <div style={{ fontFamily: 'Share Tech Mono', fontSize: 10, color: '#6a8090', padding: 10 }}>
                No kills recorded in this window
            </div>
        )
    }

    const max = Math.max(1, ...series.map(p => Math.max(p[aKey] || 0, p[bKey] || 0)))
    const half = height / 2
    // Past ~40 buckets the labels collide, so thin them rather than overlap.
    const labelEvery = Math.ceil(series.length / 12)

    return (
        <div style={{ padding: '4px 0' }}>
            <div style={{ display: 'flex', alignItems: 'stretch', gap: 1, height }}>
                {series.map((p, i) => {
                    const a = p[aKey] || 0
                    const b = p[bKey] || 0
                    const title = `${p.period}\n${sideA.short}: ${fmt(a)}\n${sideB.short}: ${fmt(b)}`
                    return (
                        <div key={p.period || i} title={title}
                            style={{ flex: 1, minWidth: 3, display: 'flex', flexDirection: 'column' }}>
                            <div style={{ height: half, display: 'flex', alignItems: 'flex-end' }}>
                                <div style={{
                                    width: '100%',
                                    height: `${Math.max(a ? 2 : 0, (a / max) * 100)}%`,
                                    background: sideA.color, opacity: 0.85,
                                }} />
                            </div>
                            <div style={{ height: 1, background: '#1a2a3a' }} />
                            <div style={{ height: half }}>
                                <div style={{
                                    width: '100%',
                                    height: `${Math.max(b ? 2 : 0, (b / max) * 100)}%`,
                                    background: sideB.color, opacity: 0.85,
                                }} />
                            </div>
                        </div>
                    )
                })}
            </div>
            <div style={{ display: 'flex', gap: 1, marginTop: 3 }}>
                {series.map((p, i) => (
                    <div key={p.period || i} style={{
                        flex: 1, minWidth: 3, textAlign: 'center',
                        fontFamily: 'Share Tech Mono', fontSize: 8, color: '#3a5060',
                        overflow: 'hidden', whiteSpace: 'nowrap',
                    }}>
                        {i % labelEvery === 0 ? periodLabel(p.period, p.bucket) : ''}
                    </div>
                ))}
            </div>
        </div>
    )
}

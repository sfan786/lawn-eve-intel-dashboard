import React from 'react'
import { getAdmColor } from '../utils/admHelpers'

export default function Sparkline({ history, width = 120, height = 24 }) {
    if (!history || history.length === 0) {
        return <svg width={width} height={height} />
    }

    const pad = 2
    const h = height - pad * 2
    const w = width - pad * 2

    if (history.length === 1) {
        const y = pad + h - (history[0].adm / 6) * h
        return (
            <svg width={width} height={height}>
                <circle cx={width / 2} cy={y} r="2" fill={getAdmColor(history[0].adm)} />
            </svg>
        )
    }

    const points = history.map((pt, i) => {
        const x = pad + (i / (history.length - 1)) * w
        const y = pad + h - (pt.adm / 6) * h
        return `${x.toFixed(1)},${y.toFixed(1)}`
    })

    const y2 = pad + h - (2 / 6) * h
    const y4 = pad + h - (4 / 6) * h

    const lastAdm = history[history.length - 1].adm
    const color = getAdmColor(lastAdm)

    const fillPoints = [
        `${pad},${pad + h}`,
        ...points,
        `${(width - pad).toFixed(1)},${pad + h}`,
    ].join(' ')

    return (
        <svg width={width} height={height}>
            <line x1={pad} y1={y2} x2={width - pad} y2={y2} stroke="#ff3355" strokeWidth="0.5" opacity="0.15" strokeDasharray="2 2" />
            <line x1={pad} y1={y4} x2={width - pad} y2={y4} stroke="#00d4ff" strokeWidth="0.5" opacity="0.15" strokeDasharray="2 2" />
            <polygon points={fillPoints} fill={color} opacity="0.08" />
            <polyline points={points.join(' ')} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    )
}

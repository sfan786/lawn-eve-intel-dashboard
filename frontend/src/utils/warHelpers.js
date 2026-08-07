import { formatIsk } from './formatters'

// Pure helpers for the war tracker. Kept out of WarPage.jsx so the arithmetic
// that decides who is "winning" is testable without rendering anything.

export const SIDES = ['a', 'b']

/**
 * Side metadata with a usable fallback, so a half-configured war still renders.
 *
 * A null/undefined key is expected, not an error: third parties fight in the
 * war zone constantly and their kills carry no side. They get a neutral
 * identity rather than being forced into A or B.
 */
export function sideMeta(war, key) {
    if (key !== 'a' && key !== 'b') {
        return { key: null, label: 'Unaligned', short: 'NEUTRAL', color: '#6a8090' }
    }
    const side = war?.sides?.[key]
    return {
        key,
        label: side?.label || (key === 'a' ? 'Side A' : 'Side B'),
        short: side?.short || side?.label || key.toUpperCase(),
        color: side?.color || (key === 'a' ? '#ff3355' : '#00ff88'),
    }
}

/** Share of a two-sided total, guarding the 0-0 case that would divide by zero. */
export function share(a, b) {
    const total = (a || 0) + (b || 0)
    if (!total) return 50
    return ((a || 0) / total) * 100
}

/**
 * Days elapsed since the war began. Whole days, floored — a war that started
 * this morning is on "day 0", not "day 1".
 */
export function warDuration(startDate) {
    if (!startDate) return 0
    const start = new Date(`${startDate}T00:00:00Z`)
    if (Number.isNaN(start.getTime())) return 0
    return Math.max(0, Math.floor((Date.now() - start.getTime()) / 86400000))
}

/**
 * How stale the ledger is, in minutes, or null when nothing has been ingested.
 * The page states this outright: the feed is assembled from a paginated source
 * behind a CDN cache, so "live" is a claim that has to be qualified.
 */
export function stalenessMinutes(lastKill) {
    if (!lastKill) return null
    const t = new Date(lastKill).getTime()
    if (Number.isNaN(t)) return null
    return Math.max(0, Math.round((Date.now() - t) / 60000))
}

/** Compact label for a series bucket: '2026-08-06' → '08/06'. */
export function periodLabel(period, bucket) {
    if (!period) return ''
    if (bucket === 'month') return period.slice(0, 7)
    const [, m, d] = period.split('-')
    return d ? `${m}/${d}` : period
}

/** Total ships and ISK lost by one side, across every hull class. */
export function hullTotals(shipClasses, sideKey) {
    const classes = shipClasses?.[sideKey] || {}
    return Object.values(classes).reduce(
        (acc, v) => ({ count: acc.count + (v.count || 0), isk: acc.isk + (v.isk || 0) }),
        { count: 0, isk: 0 },
    )
}

/**
 * Hull classes worth showing, biggest ISK first, with the classes that only
 * exist as noise (fighters, deployables) pushed to the end.
 */
export const HULL_ORDER = ['super', 'capital', 'structure', 'subcap', 'pod', 'fighter', 'deployable']

export function orderedHullClasses(shipClasses) {
    const seen = new Set()
    SIDES.forEach(s => Object.keys(shipClasses?.[s] || {}).forEach(c => seen.add(c)))
    return HULL_ORDER.filter(c => seen.has(c)).concat([...seen].filter(c => !HULL_ORDER.includes(c)))
}

/** Fleet-ping summary of the war's current state. */
export function buildWarCopyText(war, summary) {
    if (!war || !summary) return ''
    const a = sideMeta(war, 'a')
    const b = sideMeta(war, 'b')
    const t = summary.totals || {}
    const lines = [
        `${war.name.toUpperCase()} — day ${warDuration(war.start_date)}`,
        `${a.short}: ${t.a_kills || 0} kills / ${formatIsk(t.a_isk)} destroyed (${t.a_efficiency || 0}%)`,
        `${b.short}: ${t.b_kills || 0} kills / ${formatIsk(t.b_isk)} destroyed (${t.b_efficiency || 0}%)`,
    ]
    const hot = (summary.contested_systems || []).slice(0, 3)
    if (hot.length) {
        lines.push('')
        lines.push('MOST CONTESTED:')
        hot.forEach(s => {
            lines.push(`  ${s.system_name || s.system_id} — ${s.kills} kills, ${formatIsk(s.isk)} (${a.short} -${s.a_losses} / ${b.short} -${s.b_losses})`)
        })
    }
    return lines.join('\n')
}

/** Duration of a battle in human terms: '1h 20m', '45m', '<1m'. */
export function formatDuration(minutes) {
    if (!minutes || minutes < 1) return '<1m'
    if (minutes < 60) return `${Math.round(minutes)}m`
    const h = Math.floor(minutes / 60)
    const m = Math.round(minutes % 60)
    return m ? `${h}h ${m}m` : `${h}h`
}

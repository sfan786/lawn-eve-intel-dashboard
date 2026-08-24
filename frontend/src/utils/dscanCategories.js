/**
 * D-scan ship-category display constants.
 *
 * Split out of DscanParser so the result renderer, the copy-text builder and
 * the shared read-only page can all label a category the same way without
 * importing the parser component. The classification table itself
 * (GROUP_CATEGORIES) and parseDscan stay in DscanParser — nothing but the
 * parser needs them.
 */

export const CATEGORY_ORDER = [
    'SUPER', 'CAPITAL', 'BATTLESHIP', 'BATTLECRUISER', 'DOCTRINE', 'RECON',
    'SUPPORT', 'TACKLE', 'CRUISER', 'EWAR', 'BOMBER', 'COVOPS',
    'DESTROYER', 'FRIGATE', 'POD',
    'STRUCTURE', 'DEPLOYABLE', 'BUBBLE', 'SOV', 'PROBE',
]

export const CATEGORY_LABELS = {
    SUPER: 'Supercapital', CAPITAL: 'Capital', BATTLESHIP: 'Battleship',
    BATTLECRUISER: 'Battlecruiser', DOCTRINE: 'T3/HAC', RECON: 'Recon',
    SUPPORT: 'Logistics', TACKLE: 'Tackle/Dictor', CRUISER: 'Cruiser',
    EWAR: 'EWAR', BOMBER: 'Bomber', COVOPS: 'Covert Ops',
    DESTROYER: 'Destroyer', FRIGATE: 'Frigate', POD: 'Pod',
    STRUCTURE: 'Structure', DEPLOYABLE: 'Deployable', BUBBLE: 'Warp Bubble',
    SOV: 'Sov Object', PROBE: 'Probe',
}

export const CATEGORY_COLORS = {
    SUPER: '#ff3355', CAPITAL: '#ff6677', BATTLESHIP: '#ffaa00',
    BATTLECRUISER: '#ffcc44', DOCTRINE: '#ff8844', RECON: '#ff9966',
    SUPPORT: '#00d4ff', TACKLE: '#cc88ff', CRUISER: '#88aaff',
    EWAR: '#aa88ff', BOMBER: '#9966cc', COVOPS: '#7755aa',
    DESTROYER: '#6699aa', FRIGATE: '#4488aa', POD: '#336677',
    STRUCTURE: '#66aa88', DEPLOYABLE: '#558877', BUBBLE: '#ddaa44',
    SOV: '#aaaaaa', PROBE: '#445566',
}

/** Ship categories present in a parse result, in display order. */
export function shipCatRows(result) {
    if (!result) return []
    return CATEGORY_ORDER
        .filter(cat => result.byCat[cat])
        .map(cat => ({ cat, count: result.byCat[cat].count, types: result.byCat[cat].types }))
}

/** Structures in a parse result, collapsed to {type: count}. */
export function structureCounts(result) {
    return (result?.structures || []).reduce((acc, s) => {
        acc[s.type] = (acc[s.type] || 0) + 1
        return acc
    }, {})
}

/** "Sabre ×3, Loki" — type breakdown for one category, commonest first.
 *
 * `times` is a parameter because the on-screen table uses the multiplication
 * sign but copy-to-clipboard text uses a plain ASCII "x" — EVE chat and Discord
 * are not reliably kind to U+00D7.
 */
export function formatTypes(types, times = '×') {
    return Object.entries(types)
        .sort((a, b) => b[1] - a[1])
        .map(([t, n]) => n > 1 ? `${t} ${times}${n}` : t)
        .join(', ')
}

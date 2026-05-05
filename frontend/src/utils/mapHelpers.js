// Helpers shared by ConstellationMap. The dashboard ships one deployment at a
// time, but we don't want any LAWN/Kalevala/Perrigen names hard-coded into
// rendering — these utilities derive what the map needs from whatever config
// the active deployment exposes.

const REGION_PALETTE = [
    "#668844", "#667744", "#446688", "#445577", "#444466",
    "#554466", "#664455", "#553355", "#446655", "#665544",
    "#558877", "#776655", "#557788", "#665577", "#558866",
]

// Stable hash from constellation name → palette index. Same name always picks
// the same colour so things don't shimmer between renders.
function hashStr(s) {
    let h = 0
    for (let i = 0; i < s.length; i++) {
        h = ((h << 5) - h + s.charCodeAt(i)) | 0
    }
    return Math.abs(h)
}

export function constellationColor(name) {
    if (!name) return "#3a5060"
    return REGION_PALETTE[hashStr(name) % REGION_PALETTE.length]
}

// Bounding box for the cluster of LAWN/primary systems that share a constellation
// name. Used to draw the dashed outline + label around primary constellations
// in subway view.
export function constellationBounds(layout, constellationName) {
    const xs = []
    const ys = []
    Object.values(layout).forEach(p => {
        if (p.lawn && p.constellation === constellationName) {
            xs.push(p.x)
            ys.push(p.y)
        }
    })
    if (!xs.length) return null
    const pad = 30
    return {
        x: Math.min(...xs) - pad,
        y: Math.min(...ys) - pad,
        width: Math.max(...xs) - Math.min(...xs) + pad * 2,
        height: Math.max(...ys) - Math.min(...ys) + pad * 2,
    }
}

// Compute viewBox + dimensions that fit every node in a layout, with a margin.
// Falls back to the legacy LAWN viewBox if the layout is empty.
export function viewBoxFor(layout, mode) {
    const margin = mode === "subway" ? 40 : 30
    const points = Object.values(layout)
    if (!points.length) {
        return mode === "subway"
            ? { vb: "-10 -30 1180 1000", w: 1180, h: 1000 }
            : { vb: "-40 -20 1220 790", w: 1220, h: 790 }
    }
    const xs = points.map(p => p.x)
    const ys = points.map(p => p.y)
    const minX = Math.min(...xs) - margin
    const minY = Math.min(...ys) - margin
    const w = Math.max(...xs) - Math.min(...xs) + margin * 2
    const h = Math.max(...ys) - Math.min(...ys) + margin * 2
    return { vb: `${minX} ${minY} ${w} ${h}`, w, h }
}

// Group neighbour-system positions by region note (the label set during
// bootstrap). Used to drop region-name watermarks near each cluster.
export function neighbourRegionGroups(layout) {
    const groups = {}
    Object.values(layout).forEach(p => {
        if (p.constellation === "neighbor" && p.note) {
            ;(groups[p.note] = groups[p.note] || []).push(p)
        }
    })
    return groups
}

// For a primary system that has a regional/cross gate going out, return the
// neighbour region name on the other side of that gate. Used to label gateway
// systems (e.g. "→ Vale" arrows in subway view).
export function gatewayDestinations(layout, connections) {
    const dests = {}
    connections.forEach(([a, b, type]) => {
        if (type !== "regional" && type !== "cross") return
        const la = layout[a], lb = layout[b]
        if (!la || !lb) return
        if (la.lawn && !lb.lawn) {
            const note = lb.note || lb.constellation
            if (note && note !== "neighbor") dests[a] = note
        } else if (lb.lawn && !la.lawn) {
            const note = la.note || la.constellation
            if (note && note !== "neighbor") dests[b] = note
        }
    })
    return dests
}

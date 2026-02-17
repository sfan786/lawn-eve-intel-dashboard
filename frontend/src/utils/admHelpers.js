export function getAdmColor(adm) {
    if (adm >= 6) return "#00ff88";
    if (adm >= 4) return "#00d4ff";
    if (adm >= 2) return "#ffaa00";
    return "#ff3355";
}

export function getAdmStatus(adm) {
    if (adm >= 4) return { label: "Safe", color: "#00ff88", priority: 0 };
    if (adm >= 2) return { label: "Caution", color: "#ffaa00", priority: 1 };
    if (adm > 0) return { label: "Needs Grinding", color: "#ff3355", priority: 2 };
    return { label: "No Sov", color: "#3a5060", priority: 3 };
}

export function needsCriticalGrinding(name, activeLayout, nameToId, sovereignty) {
    const layout = activeLayout[name];
    if (!layout || !layout.lawn) return false;
    const sysId = nameToId[name];
    if (!sysId) return false;
    const sov = sovereignty[sysId] || {};
    const adm = sov.adm || 0;
    return adm > 0 && adm < 2;
}

export function needsCautionGrinding(name, activeLayout, nameToId, sovereignty) {
    const layout = activeLayout[name];
    if (!layout || !layout.lawn) return false;
    const sysId = nameToId[name];
    if (!sysId) return false;
    const sov = sovereignty[sysId] || {};
    const adm = sov.adm || 0;
    return adm >= 2 && adm < 4;
}

// Compute ADM change per day from history snapshots.
// Uses last 48h of data; falls back to full range if sparse.
// Returns null if < 2 points or time window < 1h.
export function computeGrindingRate(history) {
    if (!history || history.length < 2) return null
    const cutoff = Date.now() - 48 * 60 * 60 * 1000
    let points = history.filter(p => new Date(p.timestamp).getTime() >= cutoff)
    if (points.length < 2) points = history
    const first = points[0]
    const last = points[points.length - 1]
    const hours = (new Date(last.timestamp) - new Date(first.timestamp)) / (1000 * 60 * 60)
    if (hours < 1) return null
    return (last.adm - first.adm) / (hours / 24)
}

// Compute ADM change over the last 24 hours vs current value.
export function compute24hChange(history, currentAdm) {
    if (!history || history.length < 2) return 0
    const cutoff = Date.now() - 24 * 60 * 60 * 1000
    let oldPoint = history[0]
    for (let i = 0; i < history.length; i++) {
        if (new Date(history[i].timestamp).getTime() >= cutoff) {
            oldPoint = history[Math.max(0, i - 1)]
            break
        }
    }
    return currentAdm - oldPoint.adm
}

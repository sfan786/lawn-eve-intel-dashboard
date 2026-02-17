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

export const UPGRADE_CATEGORY_COLORS = {
    military: "#ff6677",
    industry: "#00ff88",
    strategic: "#00d4ff",
};

export function getSystemUpgrades(systemName, config) {
    if (!config || !config.system_upgrades) return [];
    return config.system_upgrades[systemName] || [];
}

export function getUpgradeTypeMeta(typeCode, config) {
    if (!config || !config.upgrade_types || !config.upgrade_types[typeCode]) {
        return { name: typeCode, category: "strategic" };
    }
    return config.upgrade_types[typeCode];
}

export function getUpgradeSummary(systemName, config) {
    const upgrades = getSystemUpgrades(systemName, config);
    const summary = { military: 0, industry: 0, strategic: 0 };
    upgrades.forEach(u => {
        const meta = getUpgradeTypeMeta(u.type, config);
        if (summary[meta.category] !== undefined) summary[meta.category]++;
    });
    return summary;
}

export function getUpgradeMaxLevels(systemName, config) {
    const upgrades = getSystemUpgrades(systemName, config);
    const levels = { military: 0, industry: 0, strategic: 0 };
    upgrades.forEach(u => {
        const meta = getUpgradeTypeMeta(u.type, config);
        if (u.level > levels[meta.category]) levels[meta.category] = u.level;
    });
    return levels;
}

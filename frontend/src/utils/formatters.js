export function formatIsk(value) {
    if (!value || value === 0) return "0";
    if (value >= 1e9) return (value / 1e9).toFixed(1) + "B";
    if (value >= 1e6) return (value / 1e6).toFixed(1) + "M";
    if (value >= 1e3) return (value / 1e3).toFixed(0) + "K";
    return value.toFixed(0);
}

export function timeAgo(isoTime) {
    if (!isoTime) return "";
    const diff = (Date.now() - new Date(isoTime).getTime()) / 1000;
    if (diff < 60) return Math.floor(diff) + "s";
    if (diff < 3600) return Math.floor(diff / 60) + "m";
    if (diff < 86400) return Math.floor(diff / 3600) + "h";
    return Math.floor(diff / 86400) + "d";
}

export function classifyKills(count, thresholds = [5, 20]) {
    if (count === 0) return "none";
    if (count < thresholds[0]) return "low";
    if (count < thresholds[1]) return "medium";
    return "high";
}

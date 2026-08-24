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

/**
 * Absolute wall-clock time in EVE time, which is UTC: "2026-08-24 19:42".
 *
 * Relative ages ("3h") are good for a glance but useless for the thing intel
 * actually gets compared against — a fleet ping, a timer, someone else's
 * report. Those are all quoted in EVE time, so anything claiming to be a
 * point in time should show it.
 *
 * Pass withSeconds for timestamps where the exact second matters.
 */
export function eveTime(isoTime, { withSeconds = false } = {}) {
    if (!isoTime) return "";
    const d = new Date(isoTime);
    if (Number.isNaN(d.getTime())) return "";
    const pad = (n) => String(n).padStart(2, "0");
    const hms = `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`
        + (withSeconds ? `:${pad(d.getUTCSeconds())}` : "");
    return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${hms}`;
}

export function classifyKills(count, thresholds = [5, 20]) {
    if (count === 0) return "none";
    if (count < thresholds[0]) return "low";
    if (count < thresholds[1]) return "medium";
    return "high";
}

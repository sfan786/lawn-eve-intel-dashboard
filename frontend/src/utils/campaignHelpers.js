export function getCampaignPhase(campaign) {
    const now = new Date();
    const startTime = new Date(campaign.start_time);

    // ESI start_time in /sovereignty/campaigns/ is the node spawn time.
    // If now >= startTime, nodes are out.
    const isNodesActive = (now >= startTime);

    return {
        phase: isNodesActive ? "nodes" : "reinforced",
        nodesSpawnTime: startTime,
    };
}

export function formatCountdown(targetDate) {
    const now = new Date();
    const diff = targetDate - now;

    if (diff <= 0) return "ACTIVE NOW";

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
}

export function formatEveTime(isoTimestamp) {
    const date = new Date(isoTimestamp);
    const month = (date.getUTCMonth() + 1).toString().padStart(2, '0');
    const day = date.getUTCDate().toString().padStart(2, '0');
    const hours = date.getUTCHours().toString().padStart(2, '0');
    const minutes = date.getUTCMinutes().toString().padStart(2, '0');

    return `${month}/${day} ${hours}:${minutes} EVE`;
}

export function formatVulnWindow(start, end) {
    if (!start || !end) return null;

    const startTime = new Date(start);
    const endTime = new Date(end);

    const startHour = startTime.getUTCHours().toString().padStart(2, '0');
    const startMin = startTime.getUTCMinutes().toString().padStart(2, '0');
    const endHour = endTime.getUTCHours().toString().padStart(2, '0');
    const endMin = endTime.getUTCMinutes().toString().padStart(2, '0');

    return `${startHour}:${startMin} - ${endHour}:${endMin} EVE`;
}

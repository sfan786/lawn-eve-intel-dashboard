export function getCampaignPhase(campaign) {
    const startTime = campaign?.start_time ? new Date(campaign.start_time) : null;

    // Guard against missing/malformed start_time from ESI
    if (!startTime || isNaN(startTime.getTime())) {
        return { phase: 'reinforced', nodesSpawnTime: null };
    }

    // ESI start_time in /sovereignty/campaigns/ is the node spawn time.
    // If now >= startTime, nodes are out.
    const now = new Date();
    return {
        phase: now >= startTime ? 'nodes' : 'reinforced',
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

export function formatEveTime(date) {
    if (!date || isNaN(date.getTime())) return '';
    const month = (date.getUTCMonth() + 1).toString().padStart(2, '0');
    const day = date.getUTCDate().toString().padStart(2, '0');
    const hours = date.getUTCHours().toString().padStart(2, '0');
    const minutes = date.getUTCMinutes().toString().padStart(2, '0');

    return `${month}/${day} ${hours}:${minutes} EVE`;
}

export function formatLocalTime(date) {
    if (!date || isNaN(date.getTime())) return '';
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    const rawHours = date.getHours();
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const ampm = rawHours >= 12 ? 'PM' : 'AM';
    const hours = (rawHours % 12 || 12).toString().padStart(2, '0');

    return `${month}/${day} ${hours}:${minutes} ${ampm}`;
}

export function buildCampaignCopyText(enrichedCampaigns, allianceShort, isPrimaryCampaign) {
    const lines = ['SOV CAMPAIGNS', '']
    for (const c of enrichedCampaigns) {
        const phase = c.phaseInfo
        const isPrimary = isPrimaryCampaign(c)
        const label = isPrimary
            ? (c.defender_is_friendly ? `${allianceShort} DEFENSE` : 'RECONQUEST')
            : 'REGIONAL'
        const type = c.campaign_type ? `${c.campaign_type} — ` : ''

        if (phase.phase === 'nodes') {
            const atk = ((c.attackers_score || 0) * 100).toFixed(0)
            const def = ((c.defender_score || 0) * 100).toFixed(0)
            lines.push(`${c.system_name} — ${type}${label} — NODES ACTIVE (${atk}% vs ${def}%)`)
        } else {
            lines.push(`${c.system_name} — ${type}${label} — Reinforced, nodes spawn in ${formatCountdown(phase.nodesSpawnTime)} (${formatEveTime(phase.nodesSpawnTime)})`)
        }
    }
    return lines.join('\n')
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

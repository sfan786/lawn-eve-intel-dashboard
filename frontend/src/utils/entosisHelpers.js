import { getCampaignPhase } from './campaignHelpers'

// Join command nodes to ESI sov campaigns by campaign_id.
// Returns { events: [{ campaign, nodes }], unlinked: [nodes] } with events
// sorted active ('nodes' phase) first, then upcoming by soonest node spawn.
// Nodes whose campaign_id is null or no longer matches a live campaign fall
// into unlinked (a resolved campaign disappears from ESI — its nodes surface
// there as "event ended").
export function groupNodesByEvent(nodes, campaigns) {
    const safeNodes = (Array.isArray(nodes) ? nodes : []).filter(n => n && typeof n === 'object')
    const safeCampaigns = (Array.isArray(campaigns) ? campaigns : []).filter(c => c && typeof c === 'object')

    const byId = new Map(safeCampaigns.map(c => [String(c.campaign_id), { campaign: c, nodes: [] }]))
    const unlinked = []
    for (const node of safeNodes) {
        const entry = node.campaign_id != null ? byId.get(String(node.campaign_id)) : null
        if (entry) entry.nodes.push(node)
        else unlinked.push(node)
    }

    const events = [...byId.values()].sort((a, b) => {
        const pa = getCampaignPhase(a.campaign)
        const pb = getCampaignPhase(b.campaign)
        if (pa.phase !== pb.phase) return pa.phase === 'nodes' ? -1 : 1
        const ta = pa.nodesSpawnTime ? pa.nodesSpawnTime.getTime() : Infinity
        const tb = pb.nodesSpawnTime ? pb.nodesSpawnTime.getTime() : Infinity
        return ta - tb
    })

    return { events, unlinked }
}

// Bridge campaign.constellation_id (int) -> constellation name via
// config.constellations (JSON-serialized keys are strings).
export function constellationNamesForCampaigns(campaigns, config) {
    const names = new Set()
    if (!config?.constellations) return names
    for (const campaign of campaigns || []) {
        const c = config.constellations[String(campaign.constellation_id)]
        if (c?.name) names.add(c.name)
    }
    return names
}

// Shallow-copy config with both map layouts trimmed to systems whose
// constellation is in the set, and connections kept only when both endpoints
// survive. Everything else (constellations, neighbor_systems, ...) is left
// intact — ConstellationMap needs those for lookups/tooltips.
export function filterConfigToConstellations(config, constellationNames = new Set()) {
    if (!config) return config
    const filterLayout = (layout) => Object.fromEntries(
        Object.entries(layout || {}).filter(([, pos]) => constellationNames.has(pos.constellation))
    )
    const mapLayout = filterLayout(config.map_layout)
    const mapLayoutSubway = filterLayout(config.map_layout_subway)
    const inBoth = (name) => (name in mapLayout) || (name in mapLayoutSubway)
    const connections = (config.map_connections || []).filter(
        ([a, b]) => inBoth(a) && inBoth(b)
    )
    return {
        ...config,
        map_layout: mapLayout,
        map_layout_subway: mapLayoutSubway,
        map_connections: connections,
    }
}

// Sorted system names for a constellation — used for the per-event add-node
// dropdown (command nodes spawn constellation-wide, not just in the target).
export function systemsForConstellation(config, constellationId) {
    const c = config?.constellations?.[String(constellationId)]
    if (!c?.systems) return []
    return Object.values(c.systems).map(s => s.name).sort()
}

// Set of String system ids across all campaign constellations — used to scope
// the op kill feed to systems where command nodes can spawn.
export function campaignSystemIds(campaigns, config) {
    const ids = new Set()
    if (!config?.constellations) return ids
    for (const campaign of campaigns || []) {
        const c = config.constellations[String(campaign.constellation_id)]
        if (!c?.systems) continue
        for (const s of Object.values(c.systems)) ids.add(String(s.system_id))
    }
    return ids
}

// Short badge label for an ESI campaign event_type.
export function eventTypeLabel(eventType) {
    if (typeof eventType !== 'string' || !eventType) return 'SOV'
    if (eventType.startsWith('ihub')) return 'IHUB'
    if (eventType.startsWith('tcu')) return 'TCU'
    if (eventType.startsWith('station')) return 'STATION'
    return eventType.replace('_defense', '').toUpperCase()
}

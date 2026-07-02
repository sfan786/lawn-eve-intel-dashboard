import { describe, it, expect } from 'vitest'
import {
    groupNodesByEvent,
    constellationNamesForCampaigns,
    filterConfigToConstellations,
    systemsForConstellation,
    campaignSystemIds,
    eventTypeLabel,
} from '../entosisHelpers'

const PAST = '2020-01-01T00:00:00Z'
const FUTURE = '2099-01-01T00:00:00Z'
const LATER_FUTURE = '2099-06-01T00:00:00Z'

const activeCampaign = { campaign_id: 1, system_name: 'A-1', constellation_id: 100, start_time: PAST }
const upcomingCampaign = { campaign_id: 2, system_name: 'B-2', constellation_id: 200, start_time: FUTURE }
const laterCampaign = { campaign_id: 3, system_name: 'C-3', constellation_id: 200, start_time: LATER_FUTURE }

const config = {
    constellations: {
        '100': { name: 'Const-A', systems: { '30001': { system_id: 30001, name: 'A-1' }, '30002': { system_id: 30002, name: 'A-2' } } },
        '200': { name: 'Const-B', systems: { '30003': { system_id: 30003, name: 'B-2' } } },
    },
    map_layout: {
        'A-1': { x: 0, y: 0, constellation: 'Const-A', lawn: true },
        'A-2': { x: 10, y: 10, constellation: 'Const-A', lawn: true },
        'B-2': { x: 50, y: 50, constellation: 'Const-B', lawn: true },
        'N-1': { x: 90, y: 90, constellation: 'neighbor' },
    },
    map_layout_subway: {
        'A-1': { x: 0, y: 0, constellation: 'Const-A', lawn: true },
        'B-2': { x: 50, y: 50, constellation: 'Const-B', lawn: true },
    },
    map_connections: [
        ['A-1', 'A-2', 'internal'],
        ['A-1', 'B-2', 'cross'],
        ['B-2', 'N-1', 'regional'],
    ],
}

// ---------------------------------------------------------------------------
// groupNodesByEvent
// ---------------------------------------------------------------------------

describe('groupNodesByEvent', () => {
    it('groups nodes under their campaign by campaign_id', () => {
        const nodes = [
            { id: 1, system_name: 'A-2', campaign_id: 1 },
            { id: 2, system_name: 'A-1', campaign_id: 1 },
        ]
        const { events, unlinked } = groupNodesByEvent(nodes, [activeCampaign])
        expect(events).toHaveLength(1)
        expect(events[0].nodes.map(n => n.id)).toEqual([1, 2])
        expect(unlinked).toEqual([])
    })

    it('puts nodes with null campaign_id in unlinked', () => {
        const nodes = [{ id: 1, system_name: 'A-1', campaign_id: null }]
        const { events, unlinked } = groupNodesByEvent(nodes, [activeCampaign])
        expect(events[0].nodes).toEqual([])
        expect(unlinked).toHaveLength(1)
    })

    it('puts nodes with a stale campaign_id (campaign gone from ESI) in unlinked', () => {
        const nodes = [{ id: 1, system_name: 'A-1', campaign_id: 999 }]
        const { unlinked } = groupNodesByEvent(nodes, [activeCampaign])
        expect(unlinked).toHaveLength(1)
    })

    it('sorts active (nodes phase) events before upcoming ones', () => {
        const { events } = groupNodesByEvent([], [upcomingCampaign, activeCampaign])
        expect(events.map(e => e.campaign.campaign_id)).toEqual([1, 2])
    })

    it('sorts upcoming events by soonest node spawn', () => {
        const { events } = groupNodesByEvent([], [laterCampaign, upcomingCampaign])
        expect(events.map(e => e.campaign.campaign_id)).toEqual([2, 3])
    })

    it('handles campaigns with every node unassigned and non-array inputs', () => {
        expect(groupNodesByEvent(null, undefined)).toEqual({ events: [], unlinked: [] })
    })
})

// ---------------------------------------------------------------------------
// constellationNamesForCampaigns
// ---------------------------------------------------------------------------

describe('constellationNamesForCampaigns', () => {
    it('bridges int constellation_id to string config keys', () => {
        const names = constellationNamesForCampaigns([activeCampaign], config)
        expect([...names]).toEqual(['Const-A'])
    })

    it('collects multiple constellations without duplicates', () => {
        const names = constellationNamesForCampaigns([activeCampaign, upcomingCampaign, laterCampaign], config)
        expect(names.size).toBe(2)
        expect(names.has('Const-B')).toBe(true)
    })

    it('ignores campaigns in unknown constellations and missing config', () => {
        expect(constellationNamesForCampaigns([{ constellation_id: 999 }], config).size).toBe(0)
        expect(constellationNamesForCampaigns([activeCampaign], null).size).toBe(0)
    })
})

// ---------------------------------------------------------------------------
// filterConfigToConstellations
// ---------------------------------------------------------------------------

describe('filterConfigToConstellations', () => {
    it('trims layouts to the given constellations', () => {
        const filtered = filterConfigToConstellations(config, new Set(['Const-A']))
        expect(Object.keys(filtered.map_layout).sort()).toEqual(['A-1', 'A-2'])
        expect(Object.keys(filtered.map_layout_subway)).toEqual(['A-1'])
    })

    it('drops connections when either endpoint is filtered out', () => {
        const filtered = filterConfigToConstellations(config, new Set(['Const-A']))
        expect(filtered.map_connections).toEqual([['A-1', 'A-2', 'internal']])
    })

    it('keeps cross-constellation connections when both survive', () => {
        const filtered = filterConfigToConstellations(config, new Set(['Const-A', 'Const-B']))
        expect(filtered.map_connections).toContainEqual(['A-1', 'B-2', 'cross'])
        expect(filtered.map_connections).not.toContainEqual(['B-2', 'N-1', 'regional'])
    })

    it('does not mutate the original config', () => {
        const before = Object.keys(config.map_layout).length
        filterConfigToConstellations(config, new Set())
        expect(Object.keys(config.map_layout)).toHaveLength(before)
    })

    it('returns empty layouts for an empty constellation set', () => {
        const filtered = filterConfigToConstellations(config, new Set())
        expect(filtered.map_layout).toEqual({})
        expect(filtered.map_connections).toEqual([])
    })

    it('leaves constellations and other config keys intact', () => {
        const filtered = filterConfigToConstellations(config, new Set(['Const-A']))
        expect(filtered.constellations).toBe(config.constellations)
    })
})

// ---------------------------------------------------------------------------
// systemsForConstellation
// ---------------------------------------------------------------------------

describe('systemsForConstellation', () => {
    it('returns sorted system names for an int constellation id', () => {
        expect(systemsForConstellation(config, 100)).toEqual(['A-1', 'A-2'])
    })

    it('returns empty list for unknown constellation or missing config', () => {
        expect(systemsForConstellation(config, 999)).toEqual([])
        expect(systemsForConstellation(null, 100)).toEqual([])
    })
})

// ---------------------------------------------------------------------------
// campaignSystemIds
// ---------------------------------------------------------------------------

describe('campaignSystemIds', () => {
    it('collects string ids for every system in campaign constellations', () => {
        const ids = campaignSystemIds([activeCampaign], config)
        expect([...ids].sort()).toEqual(['30001', '30002'])
    })

    it('merges systems across multiple campaigns', () => {
        const ids = campaignSystemIds([activeCampaign, upcomingCampaign], config)
        expect(ids.size).toBe(3)
    })

    it('returns empty set for no campaigns, unknown constellations, or missing config', () => {
        expect(campaignSystemIds([], config).size).toBe(0)
        expect(campaignSystemIds([{ constellation_id: 999 }], config).size).toBe(0)
        expect(campaignSystemIds([activeCampaign], null).size).toBe(0)
    })
})

// ---------------------------------------------------------------------------
// eventTypeLabel
// ---------------------------------------------------------------------------

describe('eventTypeLabel', () => {
    it('maps known ESI event types to short badges', () => {
        expect(eventTypeLabel('ihub_defense')).toBe('IHUB')
        expect(eventTypeLabel('tcu_defense')).toBe('TCU')
        expect(eventTypeLabel('station_defense')).toBe('STATION')
    })

    it('falls back gracefully for unknown/missing types', () => {
        expect(eventTypeLabel(undefined)).toBe('SOV')
        expect(eventTypeLabel('freeport')).toBe('FREEPORT')
    })
})

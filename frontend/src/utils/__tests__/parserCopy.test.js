import { describe, it, expect } from 'vitest'
import {
    buildDscanCopyText, buildFleetCopyText, buildLocalCopyText, buildShareCopyText,
} from '../parserCopy'

const dscanResult = {
    byCat: {
        CAPITAL: { count: 2, types: { Dreadnought: 2 } },
        TACKLE: { count: 3, types: { Sabre: 2, Stiletto: 1 } },
    },
    structures: [
        { name: 'Home', type: 'Astrahus' },
        { name: 'Bubble A', type: 'Mobile Small Warp Disruptor I' },
    ],
    ships: 5,
    total: 8,
    unrecognized: 0,
    unrecognizedSamples: [],
    threat: { tier: 'HIGH', color: '#ff6677', bg: 'rgba(255,102,119,0.12)' },
}

describe('buildDscanCopyText', () => {
    it('leads with the threat tier and the ship/structure counts', () => {
        const lines = buildDscanCopyText(dscanResult).split('\n')
        expect(lines[0]).toBe('THREAT: HIGH')
        expect(lines[1]).toBe('5 combat ships · 2 structures')
    })

    it('lists categories in CATEGORY_ORDER, not object order', () => {
        const text = buildDscanCopyText(dscanResult)
        expect(text.indexOf('Capital:')).toBeLessThan(text.indexOf('Tackle/Dictor:'))
    })

    it('sorts types within a category by count, commonest first', () => {
        expect(buildDscanCopyText(dscanResult)).toContain('Tackle/Dictor: 3  (Sabre x2, Stiletto)')
    })

    it('uses an ASCII x rather than the multiplication sign', () => {
        // The on-screen table uses ×; chat and Discord are happier with plain x.
        expect(buildDscanCopyText(dscanResult)).not.toContain('×')
    })

    it('collapses structures by type', () => {
        expect(buildDscanCopyText(dscanResult))
            .toContain('Objects: Astrahus, Mobile Small Warp Disruptor I')
    })

    it('omits the objects line when nothing was scanned', () => {
        const bare = { ...dscanResult, structures: [] }
        expect(buildDscanCopyText(bare)).not.toContain('Objects:')
    })

    it('returns an empty string for no result', () => {
        expect(buildDscanCopyText(null)).toBe('')
    })
})

const localResults = [
    { name: 'Hostile One', character_id: 11, standing: 'unknown', corporation_name: 'Bad Corp', alliance_name: 'Bad Alliance' },
    { name: 'Blue Two', character_id: 22, standing: 'friendly', corporation_name: 'Good Corp' },
    { name: 'Ghost', character_id: null, standing: 'unresolved' },
]
const riskMap = {
    11: { tier: 'dangerous', label: 'DANGEROUS', kills: 900, isk_eff: 88, danger: 71, roles: ['BLOPS', 'RECON'] },
}

describe('buildLocalCopyText', () => {
    it('heads with the pilot count and how many are unknown', () => {
        expect(buildLocalCopyText(localResults, riskMap).split('\n')[0])
            .toBe('LOCAL SCAN — 3 pilots, 1 unknown')
    })

    it('includes risk tier and roles when rated', () => {
        expect(buildLocalCopyText(localResults, riskMap))
            .toContain('Hostile One (Bad Corp / Bad Alliance) [UNKNOWN] DANGEROUS [BLOPS, RECON]')
    })

    it('omits the risk suffix for unrated pilots', () => {
        expect(buildLocalCopyText(localResults, riskMap))
            .toContain('Blue Two (Good Corp) [FRIENDLY]')
    })

    it('falls back to Unknown Corp when affiliation did not resolve', () => {
        expect(buildLocalCopyText(localResults, riskMap))
            .toContain('Ghost (Unknown Corp) [UNRESOLVED]')
    })

    it('tolerates a missing risk map', () => {
        expect(buildLocalCopyText(localResults)).toContain('Hostile One')
    })

    it('returns an empty string for no results', () => {
        expect(buildLocalCopyText(null)).toBe('')
    })
})

const fleetSummary = {
    unknown: 40, friendly: 5, lawn: 5, unresolved: 0,
    avg_danger: 72, avg_kills: 1500, capitals: 3,
    risk_distribution: { very_dangerous: 10, dangerous: 20, moderate: 15, snuggly: 5 },
    role_counts: { DREAD: 3, RECON: 4 },
    fleet_role_counts: { LOGI: 8 },
    top_alliances: [{ name: 'Alpha', count: 30 }, { name: 'Beta', count: 12 }],
}

describe('buildFleetCopyText', () => {
    it('totals pilots across every standing', () => {
        expect(buildFleetCopyText(fleetSummary).split('\n')[0]).toBe('FLEET ANALYSIS — 50 pilots')
    })

    it('reports average danger and capital count', () => {
        expect(buildFleetCopyText(fleetSummary)).toContain('Threat: 72% avg danger | Caps: 3')
    })

    it('lists only the risk tiers that are populated', () => {
        const text = buildFleetCopyText(fleetSummary)
        expect(text).toContain('Risk: 10 VERY DANGEROUS, 20 DANGEROUS, 15 MODERATE, 5 SNUGGLY')
        expect(text).not.toContain('NEWBIE')
    })

    it('includes both role breakdowns and the alliance split', () => {
        const text = buildFleetCopyText(fleetSummary)
        expect(text).toContain('Roles: DREAD ×3, RECON ×4')
        expect(text).toContain('Fleet roles: LOGI ×8')
        expect(text).toContain('Top alliances: Alpha (30), Beta (12)')
    })

    it('caps the alliance list at five', () => {
        const many = {
            ...fleetSummary,
            top_alliances: Array.from({ length: 9 }, (_, i) => ({ name: `A${i}`, count: 1 })),
        }
        expect(buildFleetCopyText(many).match(/A\d \(1\)/g)).toHaveLength(5)
    })

    it('survives a summary with nothing but zeroes', () => {
        expect(buildFleetCopyText({})).toContain('FLEET ANALYSIS — 0 pilots')
    })

    it('returns an empty string for no summary', () => {
        expect(buildFleetCopyText(null)).toBe('')
    })
})

describe('buildShareCopyText', () => {
    it('dispatches on kind so the share page copies like the live panel', () => {
        expect(buildShareCopyText('dscan', { result: dscanResult }))
            .toBe(buildDscanCopyText(dscanResult))
        expect(buildShareCopyText('local', { results: localResults, riskMap }))
            .toBe(buildLocalCopyText(localResults, riskMap))
        expect(buildShareCopyText('fleet', { result: { summary: fleetSummary } }))
            .toBe(buildFleetCopyText(fleetSummary))
    })

    it('returns an empty string for a kind it does not know', () => {
        expect(buildShareCopyText('intel', {})).toBe('')
    })
})

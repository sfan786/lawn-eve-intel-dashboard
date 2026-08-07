import { describe, it, expect, vi, afterEach } from 'vitest'
import {
    sideMeta, share, warDuration, stalenessMinutes, periodLabel,
    hullTotals, orderedHullClasses, buildWarCopyText, formatDuration,
} from '../warHelpers'

const WAR = {
    name: 'Drone Regions War',
    start_date: '2026-03-01',
    sides: {
        a: { label: 'B0SS / SkillU', short: 'B0SS', color: '#ff3355' },
        b: { label: 'RMC', short: 'RMC', color: '#00ff88' },
    },
}

afterEach(() => vi.useRealTimers())

describe('sideMeta', () => {
    it('reads a configured side', () => {
        expect(sideMeta(WAR, 'a')).toMatchObject({ label: 'B0SS / SkillU', short: 'B0SS' })
    })

    it('falls back when the war is missing or half-configured', () => {
        expect(sideMeta(null, 'a').label).toBe('Side A')
        expect(sideMeta({ sides: {} }, 'b').color).toBe('#00ff88')
    })

    it('treats a missing side as neutral rather than throwing', () => {
        // Third-party kills carry no side and are common in a war zone.
        expect(sideMeta(WAR, null)).toMatchObject({ key: null, short: 'NEUTRAL' })
        expect(sideMeta(WAR, undefined).label).toBe('Unaligned')
        expect(sideMeta(WAR, 'nonsense').short).toBe('NEUTRAL')
    })
})

describe('share', () => {
    it('splits proportionally', () => {
        expect(share(75, 25)).toBe(75)
    })

    it('returns an even split rather than dividing by zero', () => {
        expect(share(0, 0)).toBe(50)
    })

    it('tolerates nulls', () => {
        expect(share(null, 100)).toBe(0)
    })
})

describe('warDuration', () => {
    it('counts whole days since the start', () => {
        vi.useFakeTimers()
        vi.setSystemTime(new Date('2026-03-11T06:00:00Z'))
        expect(warDuration('2026-03-01')).toBe(10)
    })

    it('is 0 on the first day, not 1', () => {
        vi.useFakeTimers()
        vi.setSystemTime(new Date('2026-03-01T18:00:00Z'))
        expect(warDuration('2026-03-01')).toBe(0)
    })

    it('handles missing or malformed dates', () => {
        expect(warDuration(null)).toBe(0)
        expect(warDuration('not-a-date')).toBe(0)
    })
})

describe('stalenessMinutes', () => {
    it('measures how far behind the ledger is', () => {
        vi.useFakeTimers()
        vi.setSystemTime(new Date('2026-08-06T12:30:00Z'))
        expect(stalenessMinutes('2026-08-06T12:00:00Z')).toBe(30)
    })

    it('returns null when nothing has been ingested', () => {
        expect(stalenessMinutes(null)).toBeNull()
        expect(stalenessMinutes('nonsense')).toBeNull()
    })
})

describe('periodLabel', () => {
    it('shortens a day bucket', () => {
        expect(periodLabel('2026-08-06', 'day')).toBe('08/06')
    })

    it('keeps year-month for a month bucket', () => {
        expect(periodLabel('2026-08-06', 'month')).toBe('2026-08')
    })

    it('tolerates an empty period', () => {
        expect(periodLabel('', 'day')).toBe('')
    })
})

describe('hull helpers', () => {
    const classes = {
        a: { subcap: { count: 10, isk: 100 }, capital: { count: 2, isk: 900 } },
        b: { subcap: { count: 5, isk: 50 } },
    }

    it('totals a side across classes', () => {
        expect(hullTotals(classes, 'a')).toEqual({ count: 12, isk: 1000 })
    })

    it('is zero for a side with no losses', () => {
        expect(hullTotals(classes, 'nope')).toEqual({ count: 0, isk: 0 })
    })

    it('orders classes biggest-hull first and only includes present ones', () => {
        expect(orderedHullClasses(classes)).toEqual(['capital', 'subcap'])
    })

    it('appends unrecognised classes rather than dropping them', () => {
        const ordered = orderedHullClasses({ a: { mystery: { count: 1, isk: 1 } }, b: {} })
        expect(ordered).toContain('mystery')
    })
})

describe('buildWarCopyText', () => {
    const summary = {
        totals: { a_kills: 69, b_kills: 5, a_isk: 8.0e9, b_isk: 2.3e8, a_efficiency: 97.2, b_efficiency: 2.8 },
        contested_systems: [
            { system_name: '1-KCSA', kills: 40, isk: 3e9, a_losses: 8, b_losses: 20 },
        ],
    }

    it('summarises both sides for a fleet ping', () => {
        const text = buildWarCopyText(WAR, summary)
        expect(text).toContain('DRONE REGIONS WAR')
        expect(text).toContain('B0SS: 69 kills')
        expect(text).toContain('RMC: 5 kills')
        expect(text).toContain('1-KCSA')
    })

    it('returns empty string without data', () => {
        expect(buildWarCopyText(null, null)).toBe('')
    })

    it('omits the contested block when there is nothing to report', () => {
        expect(buildWarCopyText(WAR, { totals: {} })).not.toContain('MOST CONTESTED')
    })
})

describe('formatDuration', () => {
    it('formats sub-hour fights in minutes', () => {
        expect(formatDuration(45)).toBe('45m')
    })

    it('formats long fights in hours and minutes', () => {
        expect(formatDuration(95)).toBe('1h 35m')
        expect(formatDuration(120)).toBe('2h')
    })

    it('floors a flash engagement', () => {
        expect(formatDuration(0.4)).toBe('<1m')
        expect(formatDuration(0)).toBe('<1m')
    })
})

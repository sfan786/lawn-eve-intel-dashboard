import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import WarPage from '../WarPage'

vi.mock('../../components/common/CornerBrackets', () => ({ default: () => null }))
vi.mock('../../components/common/EveLoginButton', () => ({ default: () => null }))
vi.mock('../../utils/useAuth', () => ({
    useAuth: () => ({
        loaded: true, ssoEnabled: true, loggedIn: true, authorized: true,
        characterName: 'Test Pilot', login: vi.fn(), logout: vi.fn(), refresh: vi.fn(),
    }),
}))

const WAR = {
    key: 'dronelands',
    name: 'Drone Regions War',
    short_name: 'DRONELANDS',
    start_date: '2026-03-01',
    regions: [{ id: 10000066, name: 'Perrigen Falls' }],
    sides: {
        a: { key: 'a', label: 'B0SS / SkillU', short: 'B0SS', color: '#ff3355' },
        b: { key: 'b', label: 'RMC', short: 'RMC', color: '#00ff88' },
    },
    home_alliance_ids: [150097440],
}

const SUMMARY = {
    war_id: 'dronelands',
    days: 7,
    bucket: 'day',
    war: WAR,
    totals: { a_kills: 69, b_kills: 5, a_isk: 8.03e9, b_isk: 2.3e8, a_efficiency: 97.2, b_efficiency: 2.8 },
    coverage: { rows: 199, first_kill: '2026-08-05T23:00:43Z', last_kill: '2026-08-06T18:16:47Z' },
    series: [
        { period: '2026-08-05', a_kills: 14, a_isk: 6.2e8, b_kills: 0, b_isk: 0 },
        { period: '2026-08-06', a_kills: 55, a_isk: 7.4e9, b_kills: 5, b_isk: 2.3e8 },
    ],
    contested_systems: [
        {
            system_id: 30005093, system_name: 'V-3K7C', region_id: 10000066,
            kills: 11, war_kills: 9, isk: 6.1e9, last_kill: '2026-08-06T04:00:00Z',
            a_losses: 6, b_losses: 3, other_losses: 2, contest_score: 1.2,
        },
    ],
    ship_classes: {
        a: { subcap: { count: 33, isk: 1.7e10 } },
        b: { structure: { count: 11, isk: 9.2e9 }, subcap: { count: 66, isk: 3.9e9 } },
    },
    biggest_kills: [],
}

const BATTLES = [{
    system_id: 30005093, system_name: 'V-3K7C', region_id: 10000066,
    start_time: '2026-08-06T04:00:00Z', end_time: '2026-08-06T04:25:00Z',
    kills: 7, isk: 6.1e9, a_losses: 2, b_losses: 5, cap_losses: 1,
    structure_losses: 0, peak_attackers: 42, duration_minutes: 25.9,
    winner: 'a', related_url: 'https://zkillboard.com/related/30005093/202608060400/',
}]

const LEADERBOARD = {
    bleeders: [{ victim_side: 'a', alliance_id: 99007887, name: 'Brotherhood of Spacers', losses: 33, isk_lost: 1.79e10 }],
    killers: [{ alliance_id: 99009927, involved_kills: 7, isk_involved: 2.2e9 }],
}

const KILLS = {
    kills: [{
        killmail_id: 137522191, killmail_time: '2026-08-06T18:15:16Z',
        system_id: 30005093, system_name: 'V-3K7C', region_id: 10000066,
        victim_side: 'b', killer_side: 'a',
        victim_alliance_name: 'Legion of xXDEATHXx', victim_corp_name: 'Some Corp',
        victim_char_name: 'Test Pilot', ship_name: 'Metenox Moon Drill',
        ship_class: 'structure', isk_destroyed: 1.09e8, isk_value: 1.2e8,
        attacker_count: 12, pilot_count: 11, is_npc: 0,
    }, {
        // Third parties fight in the war zone constantly and carry no side.
        killmail_id: 137522192, killmail_time: '2026-08-06T18:10:00Z',
        system_id: 30005093, system_name: 'V-3K7C', region_id: 10000066,
        victim_side: null, killer_side: null,
        victim_alliance_name: 'Some Neutral', victim_corp_name: 'Neutral Corp',
        victim_char_name: 'Passer By', ship_name: 'Venture',
        ship_class: 'subcap', isk_destroyed: 5.0e6, isk_value: 6.0e6,
        attacker_count: 2, pilot_count: 2, is_npc: 0,
    }],
    next_before: '2026-08-06T18:10:00Z|137522192',
}

const UNCLASSIFIED = [{
    alliance_id: 99009927, name: 'Dawn\'s Light', involved_kills: 11,
    isk_involved: 2.2e9, last_seen: '2026-08-06T17:00:00Z',
    kills_vs_a: 2, kills_vs_b: 9, suggested_side: 'a',
}]

const STATUS = {
    war_id: 'dronelands',
    regions: [{ region_id: 10000066, region_name: 'Perrigen Falls', last_success_at: '2026-08-06T18:20:00Z', last_kill_time: '2026-08-06T18:16:47Z', new_kills: 4, saturated: false, last_error: null }],
    coverage_since: '2026-08-05T23:00:43Z',
    last_kill: '2026-08-06T18:16:47Z',
    rows: 199,
    any_gaps: false,
}

const ROSTER = {
    sides: WAR.sides,
    overrides: [],
    counts: { a: 2, b: 61, overrides: 0 },
}

const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })

function mockFetch(overrides = {}) {
    return vi.fn((url) => {
        const u = String(url)
        if (u === '/api/wars') return ok(overrides.wars ?? [WAR])
        if (u.includes('/roster')) return ok(overrides.roster ?? ROSTER)
        if (u.includes('/summary')) return ok(overrides.summary ?? SUMMARY)
        if (u.includes('/battles')) return ok(overrides.battles ?? BATTLES)
        if (u.includes('/leaderboard')) return ok(overrides.leaderboard ?? LEADERBOARD)
        if (u.includes('/kills')) return ok(overrides.kills ?? KILLS)
        if (u.includes('/participant')) return ok(overrides.participant ?? null)
        if (u.includes('/unclassified')) return ok(overrides.unclassified ?? UNCLASSIFIED)
        if (u.includes('/status')) return ok(overrides.status ?? STATUS)
        return ok({})
    })
}

const renderPage = () => render(<MemoryRouter><WarPage /></MemoryRouter>)

describe('WarPage', () => {
    beforeEach(() => {
        global.fetch = mockFetch()
    })
    afterEach(() => vi.restoreAllMocks())

    it('renders the war name and both sides on the scoreboard', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByText('DRONE REGIONS WAR')).toBeInTheDocument())
        // The title comes from /api/wars, which resolves before the summary —
        // wait for a value that only exists once the summary has landed.
        await waitFor(() => expect(screen.getByText('69')).toBeInTheDocument())
        expect(screen.getByText('B0SS / SkillU')).toBeInTheDocument()
        // 'RMC' is the side's short name and appears in several panels.
        expect(screen.getAllByText('RMC').length).toBeGreaterThan(0)
    })

    it('states how stale the ledger is rather than implying it is live', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByText(/KILLS LOGGED/)).toBeInTheDocument())
        expect(screen.getByText(/UPDATED \d+M AGO/)).toBeInTheDocument()
    })

    it('shows contested systems with both sides losses', async () => {
        renderPage()
        await waitFor(() => expect(screen.getAllByText('V-3K7C').length).toBeGreaterThan(0))
    })

    it('separates war kills from unrelated violence in the same system', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByText('War / all')).toBeInTheDocument())
        // 9 of the system's 11 kills involved a belligerent. Matched as one
        // cell — the bare numbers appear all over the other panels.
        const cell = screen.getByText(
            (_, el) => el?.tagName === 'TD' && el.textContent.replace(/\s+/g, ' ').trim() === '9 / 11',
        )
        expect(cell).toBeInTheDocument()
    })

    it('links each battle to its zKillboard report', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByText('BR ↗')).toBeInTheDocument())
        expect(screen.getByText('BR ↗').closest('a')).toHaveAttribute(
            'href', 'https://zkillboard.com/related/30005093/202608060400/')
    })

    it('renders the kill feed with the victim side marked', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByText('Metenox Moon Drill')).toBeInTheDocument())
        expect(screen.getByText(/RMC loss/)).toBeInTheDocument()
    })

    it('renders third-party kills, which carry no side', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByText('Venture')).toBeInTheDocument())
        // Neutral kills must not be attributed to either belligerent.
        expect(screen.queryByText(/Some Neutral.*loss/)).not.toBeInTheDocument()
    })

    it('labels the killer board as involvement, not credit', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByText('involvement, not credit')).toBeInTheDocument())
    })

    it('surfaces unaligned alliances for roster maintenance', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByText("Dawn's Light")).toBeInTheDocument())
    })

    it('refetches when the range changes', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByText('DRONE REGIONS WAR')).toBeInTheDocument())
        global.fetch.mockClear()
        fireEvent.click(screen.getByText('WAR'))
        await waitFor(() =>
            expect(global.fetch.mock.calls.some(c => String(c[0]).includes('days=all'))).toBe(true))
    })

    it('filters the feed by side without refetching the aggregates', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByText('Metenox Moon Drill')).toBeInTheDocument())
        global.fetch.mockClear()
        fireEvent.click(screen.getByRole('button', { name: 'B0SS' }))
        await waitFor(() =>
            expect(global.fetch.mock.calls.some(c => String(c[0]).includes('side=a'))).toBe(true))
        expect(global.fetch.mock.calls.every(c => !String(c[0]).includes('/summary'))).toBe(true)
    })

    it('explains itself when no war is configured', async () => {
        global.fetch = mockFetch({ wars: [] })
        renderPage()
        await waitFor(() => expect(screen.getByText(/No war is configured/)).toBeInTheDocument())
        expect(screen.getByText(/private\/wars\//)).toBeInTheDocument()
    })

    it('says so when we are not a belligerent', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByText('Not a belligerent in this war')).toBeInTheDocument())
    })

    it('shows our own record when we are one', async () => {
        global.fetch = mockFetch({
            participant: { kills: 412, losses: 198, isk_killed: 1.28e11, isk_lost: 6.1e10, efficiency: 67.7, top_systems: [{ system_name: 'V-3K7C', n: 64 }] },
        })
        renderPage()
        await waitFor(() => expect(screen.getByText('67.7% efficiency')).toBeInTheDocument())
        expect(screen.getByText('412')).toBeInTheDocument()
    })

    it('assigns an unaligned alliance to a side from the page', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByText("Dawn's Light")).toBeInTheDocument())
        fireEvent.click(screen.getByTitle('Add to RMC'))
        await waitFor(() => {
            const post = global.fetch.mock.calls.find(c => c[1]?.method === 'POST')
            expect(post).toBeTruthy()
            expect(String(post[0])).toContain('/roster')
            expect(JSON.parse(post[1].body)).toMatchObject({ entity_id: 99009927, side: 'b' })
        })
    })

    it('can rule an alliance out as not a belligerent', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByText("Dawn's Light")).toBeInTheDocument())
        fireEvent.click(screen.getByTitle('Not a belligerent — stop suggesting'))
        await waitFor(() => {
            const post = global.fetch.mock.calls.find(c => c[1]?.method === 'POST')
            expect(JSON.parse(post[1].body).side).toBeNull()
        })
    })

    it('reports an authorization failure instead of failing silently', async () => {
        const base = mockFetch()
        global.fetch = vi.fn((url, opts) => opts?.method === 'POST'
            ? Promise.resolve({ ok: false, status: 401, json: () => Promise.resolve({}) })
            : base(url, opts))
        renderPage()
        await waitFor(() => expect(screen.getByText("Dawn's Light")).toBeInTheDocument())
        fireEvent.click(screen.getByTitle('Add to RMC'))
        await waitFor(() => expect(screen.getByText(/Not authorized/)).toBeInTheDocument())
    })

    it('lists roster edits and can undo them', async () => {
        global.fetch = mockFetch({
            roster: {
                ...ROSTER,
                overrides: [{
                    entity_type: 'alliance', entity_id: 99009927, side: 'b',
                    name: "Dawn's Light", added_by: 'Test Pilot',
                    added_at: '2026-08-07T00:00:00Z',
                }],
                counts: { a: 2, b: 62, overrides: 1 },
            },
        })
        renderPage()
        await waitFor(() => expect(screen.getByText('Roster Edits')).toBeInTheDocument())
        fireEvent.click(screen.getByText('UNDO'))
        await waitFor(() => {
            const del = global.fetch.mock.calls.find(c => c[1]?.method === 'DELETE')
            expect(String(del[0])).toContain('/roster/99009927')
        })
    })

    it('survives an API failure without blanking the page', async () => {
        global.fetch = vi.fn((url) => String(url) === '/api/wars'
            ? ok([WAR])
            : Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) }))
        renderPage()
        await waitFor(() => expect(screen.getByText(/Could not load war data/)).toBeInTheDocument())
    })
})

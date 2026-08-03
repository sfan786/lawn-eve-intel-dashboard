import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import AnalyticsPage from '../AnalyticsPage'

vi.mock('../../utils/useAuth', () => ({
    useAuth: () => ({ loaded: true, ssoEnabled: false, loggedIn: false, authorized: false, login: vi.fn(), logout: vi.fn() }),
}))

vi.mock('../../components/common/CornerBrackets', () => ({ default: () => null }))
vi.mock('../../components/common/EveLoginButton', () => ({ default: () => null }))

const SUMMARY = {
    days: 30,
    totals: {
        page_views: 12, api_calls: 40, unique_visitors: 5, returning_visitors: 2,
        active_days: 3, bot_hits: 7, peak_daily_visitors: 4,
    },
    daily: [{ day: '2026-08-01', page_views: 12, api_calls: 40, visitors: 5 }],
    hourly: Array.from({ length: 24 }, (_, h) => ({ hour: h, views: h })),
    top_pages: [{ path: '/', views: 12 }],
    top_api: [{ path: '/api/config', views: 40 }],
    visitor_frequency: [{ days_seen: 5, visitors: 2 }],
    pilots: [],
}

const jsonResponse = (status, body) => Promise.resolve({
    ok: status === 200, status, json: () => Promise.resolve(body),
})

const renderPage = () => render(<MemoryRouter><AnalyticsPage /></MemoryRouter>)

const summaryCalls = () =>
    fetch.mock.calls.filter(([url]) => String(url).startsWith('/api/analytics/summary'))

describe('AnalyticsPage unlock flow', () => {
    beforeEach(() => {
        localStorage.clear()
        global.fetch = vi.fn((url) =>
            String(url).startsWith('/api/analytics/auth')
                ? jsonResponse(200, { configured: true, authorized: false, sso: false, password: true })
                : jsonResponse(401, { error: 'Unauthorized' }),
        )
    })

    it('does not send a request per keystroke while typing the password', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByPlaceholderText('Analytics password')).toBeInTheDocument())

        const before = summaryCalls().length
        const input = screen.getByPlaceholderText('Analytics password')
        for (const ch of 'hunter2') {
            fireEvent.change(input, { target: { value: input.value + ch } })
        }

        // Typing must cost nothing: the old bug keyed the fetch effect on the
        // input value and burned the rate limit before UNLOCK was ever clicked.
        expect(summaryCalls().length).toBe(before)
    })

    it('sends exactly one request when UNLOCK is clicked', async () => {
        renderPage()
        await waitFor(() => expect(screen.getByPlaceholderText('Analytics password')).toBeInTheDocument())

        global.fetch.mockImplementation((url, opts) =>
            String(url).startsWith('/api/analytics/summary') && opts?.headers?.['X-Analytics-Auth'] === 'hunter2'
                ? jsonResponse(200, SUMMARY)
                : jsonResponse(401, { error: 'Unauthorized' }),
        )

        const before = summaryCalls().length
        fireEvent.change(screen.getByPlaceholderText('Analytics password'), { target: { value: 'hunter2' } })
        fireEvent.click(screen.getByText('UNLOCK'))

        await waitFor(() => expect(screen.getByText('Is Anyone Using This?')).toBeInTheDocument())
        expect(summaryCalls().length).toBe(before + 1)
    })

    it('marks the browser as unlocked only after a successful load', async () => {
        global.fetch = vi.fn((url) =>
            String(url).startsWith('/api/analytics/summary')
                ? jsonResponse(200, SUMMARY)
                : jsonResponse(200, { configured: true, authorized: true, sso: false, password: false }))
        renderPage()
        await waitFor(() => expect(localStorage.getItem('analytics_seen')).toBe('1'))
    })

    it('clears the unlocked marker when access is refused', async () => {
        localStorage.setItem('analytics_seen', '1')
        renderPage()
        await waitFor(() => expect(localStorage.getItem('analytics_seen')).toBeNull())
    })

    it('still offers the password form when throttled, so the user can retry', async () => {
        global.fetch = vi.fn((url) =>
            String(url).startsWith('/api/analytics/summary')
                ? jsonResponse(429, { error: 'rate limited' })
                : jsonResponse(429, { error: 'rate limited' }))
        renderPage()

        await waitFor(() => expect(screen.getByText(/Too many attempts/)).toBeInTheDocument())
        expect(screen.getByPlaceholderText('Analytics password')).toBeInTheDocument()
        // A throttled page must not spend the other endpoint's budget probing.
        expect(fetch.mock.calls.filter(([u]) => String(u).startsWith('/api/analytics/auth'))).toHaveLength(0)
    })

    it('shows setup guidance instead of a login box when access is unconfigured', async () => {
        global.fetch = vi.fn((url) =>
            String(url).startsWith('/api/analytics/summary')
                ? jsonResponse(503, { error: 'Analytics access not configured', detail: 'Set ANALYTICS_PASSWORD to unlock.' })
                : jsonResponse(200, { configured: false, authorized: false, sso: false, password: false }))
        renderPage()

        await waitFor(() => expect(screen.getByText('Access Not Configured')).toBeInTheDocument())
        expect(screen.getByText(/Set ANALYTICS_PASSWORD to unlock/)).toBeInTheDocument()
    })
})

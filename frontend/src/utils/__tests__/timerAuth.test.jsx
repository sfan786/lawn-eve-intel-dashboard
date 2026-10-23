import React from 'react'
import { render, waitFor, screen, fireEvent } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { checkTimerPassword, TIMER_AUTH_MESSAGES } from '../useAuth'
import TimerBoard from '../../components/TimerBoard'
import JumpBridgeManager from '../../components/JumpBridgeManager'

vi.mock('../../components/common/CornerBrackets', () => ({ default: () => null }))

function mockFetch(handler) {
    globalThis.fetch = vi.fn(async (url, opts) => handler(String(url), opts))
}

const json = (status, body) => ({ ok: status < 300, status, json: async () => body })

describe('checkTimerPassword', () => {
    afterEach(() => { vi.restoreAllMocks() })

    it.each([
        [200, 'ok'],
        [401, 'invalid'],
        [429, 'locked'],
    ])('maps HTTP %i to %s', async (status, expected) => {
        mockFetch(() => json(status, {}))
        expect(await checkTimerPassword('pw')).toBe(expected)
    })

    it('reports network failure as error, not as a wrong password', async () => {
        globalThis.fetch = vi.fn(async () => { throw new Error('offline') })
        expect(await checkTimerPassword('pw')).toBe('error')
    })

    it('has a message for the lockout', () => {
        expect(TIMER_AUTH_MESSAGES.locked).toMatch(/too many/i)
    })
})

describe('TimerBoard password check', () => {
    beforeEach(() => { localStorage.clear() })
    afterEach(() => { vi.restoreAllMocks() })

    const authChecks = () => globalThis.fetch.mock.calls.filter(([u]) => String(u) === '/api/auth/check')

    it('verifies a remembered password exactly once on mount', async () => {
        // Each wrong check counts toward the server-side lockout, so a check
        // that re-fired on re-render or per keystroke would lock users out.
        localStorage.setItem('timer_auth', 'stale-password')
        mockFetch((url) => {
            if (url === '/api/auth/check') return json(401, {})
            if (url === '/api/auth/me') return json(200, { sso_enabled: false })
            return json(200, [])
        })
        const { rerender } = render(<TimerBoard />)
        await waitFor(() => expect(authChecks()).toHaveLength(1))
        rerender(<TimerBoard />)
        await new Promise(r => setTimeout(r, 20))
        expect(authChecks()).toHaveLength(1)
    })

    it('does not check per keystroke while a password is typed (JumpBridgeManager)', async () => {
        // Regression: the check used to be an effect keyed on the input, so
        // typing an 11-character password fired 11 wrong guesses and tripped
        // the lockout before LOGIN was ever pressed.
        mockFetch((url) => {
            if (url === '/api/auth/check') return json(401, {})
            if (url === '/api/auth/me') return json(200, { sso_enabled: false })
            return json(200, [])
        })
        render(<JumpBridgeManager jumpBridges={[]} />)
        fireEvent.click(await screen.findByText('LOGIN TO MANAGE'))
        const input = screen.getByPlaceholderText('Enter Password')
        for (const ch of 'hunter2hunter2') {
            fireEvent.change(input, { target: { value: input.value + ch } })
        }
        await new Promise(r => setTimeout(r, 20))
        expect(authChecks()).toHaveLength(0)

        fireEvent.submit(input.closest('form'))
        await waitFor(() => expect(authChecks()).toHaveLength(1))
        expect(await screen.findByText('Invalid password')).toBeTruthy()
    })

    it('does not call the check at all with no remembered password', async () => {
        mockFetch((url) => (url === '/api/auth/me' ? json(200, { sso_enabled: false }) : json(200, [])))
        render(<TimerBoard />)
        await new Promise(r => setTimeout(r, 20))
        expect(authChecks()).toHaveLength(0)
    })
})

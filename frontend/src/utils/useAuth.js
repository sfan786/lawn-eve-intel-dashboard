import { useState, useEffect, useCallback } from 'react'

// Shared identity/authorization state. Reads /api/auth/me to decide whether the
// "Log in with EVE" SSO flow is available and whether the current session may
// write. When SSO is disabled (sso_enabled=false), callers fall back to the
// legacy TIMER_PASSWORD UI.
export function useAuth() {
    const [auth, setAuth] = useState({
        ssoEnabled: false,
        loggedIn: false,
        authorized: false,
        characterName: null,
        loaded: false,
    })

    const refresh = useCallback(async () => {
        try {
            const res = await fetch('/api/auth/me')
            if (res.ok) {
                const d = await res.json()
                setAuth({
                    ssoEnabled: !!d.sso_enabled,
                    loggedIn: !!d.logged_in,
                    authorized: !!d.authorized,
                    characterName: d.character_name || null,
                    loaded: true,
                })
            } else {
                setAuth(a => ({ ...a, loaded: true }))
            }
        } catch {
            setAuth(a => ({ ...a, loaded: true }))
        }
    }, [])

    useEffect(() => { refresh() }, [refresh])

    const login = useCallback(() => {
        window.location = '/api/auth/sso/login?next=' + encodeURIComponent(window.location.pathname)
    }, [])

    const logout = useCallback(async () => {
        try { await fetch('/api/auth/logout', { method: 'POST' }) } catch { /* ignore */ }
        refresh()
    }, [refresh])

    return { ...auth, login, logout, refresh }
}

/**
 * Check a TIMER_PASSWORD against /api/auth/check.
 *
 * Resolves to 'ok', 'invalid', 'locked' (429 — too many failures from this
 * IP) or 'error' (network). Every wrong attempt counts toward a per-IP
 * lockout shared with all write endpoints, so call this on submit or once on
 * mount with a remembered password — never from an effect keyed on the input,
 * which would spend the allowance one keystroke at a time.
 */
export async function checkTimerPassword(password) {
    try {
        const res = await fetch('/api/auth/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password }),
        })
        if (res.ok) return 'ok'
        return res.status === 429 ? 'locked' : 'invalid'
    } catch {
        return 'error'
    }
}

export const TIMER_AUTH_MESSAGES = {
    invalid: 'Invalid password',
    locked: 'Too many attempts — wait a minute',
}

/**
 * What a panel needs to offer a write-gated action (AI summary, share).
 *
 * `canWrite` mirrors the backend's require_write_auth: an SSO session that is
 * authorized, or any caller at all when SSO is switched off (demo and
 * password-only deployments, where the header below carries the credential
 * instead). `writeHeaders` is empty under SSO because the session cookie
 * already carries it.
 *
 * This was copy-pasted verbatim into every panel that has such a button, which
 * meant the gate could drift apart between them.
 */
export function useWriteAuth() {
    const { authorized, ssoEnabled, ...rest } = useAuth()
    return {
        ...rest,
        authorized,
        ssoEnabled,
        canWrite: authorized || !ssoEnabled,
        writeHeaders: ssoEnabled ? {} : { 'X-Timer-Auth': localStorage.getItem('timer_auth') || '' },
    }
}

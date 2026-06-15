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

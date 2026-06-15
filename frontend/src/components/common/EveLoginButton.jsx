import React from 'react'

// Renders the EVE SSO control for a panel header. Returns null when SSO is not
// configured so callers can fall back to their legacy password UI.
//   - not logged in / unauthorized → "LOG IN WITH EVE" button
//   - authorized                   → character name + LOGOUT
const btnStyle = {
    background: 'transparent',
    border: '1px solid var(--cyan-dim)',
    color: 'var(--cyan)',
    fontFamily: 'Share Tech Mono',
    fontSize: 10,
    padding: '2px 8px',
    cursor: 'pointer',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
}

export default function EveLoginButton({ auth }) {
    if (!auth.ssoEnabled) return null

    if (auth.authorized) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 10, color: 'var(--green)', fontFamily: 'Share Tech Mono' }}>
                    ▣ {auth.characterName}
                </span>
                <button onClick={auth.logout} style={btnStyle}>LOGOUT</button>
            </div>
        )
    }

    // Logged in but not in an allowed alliance/allowlist.
    if (auth.loggedIn) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 10, color: 'var(--amber)', fontFamily: 'Share Tech Mono' }}>
                    {auth.characterName} — not authorized
                </span>
                <button onClick={auth.logout} style={btnStyle}>LOGOUT</button>
            </div>
        )
    }

    return <button onClick={auth.login} style={btnStyle}>⛛ Log in with EVE</button>
}

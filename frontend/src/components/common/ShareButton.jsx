import React, { useState } from 'react'
import CopyButton from './CopyButton'

const CTRL = {
    background: 'none', border: '1px solid var(--border-dim)',
    color: 'var(--text-secondary)', cursor: 'pointer',
    fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
    padding: '2px 8px', letterSpacing: 1,
}

/**
 * Publishes the current parser result as a read-only page and shows the link.
 *
 * The snapshot is frozen server-side: what the recipient sees is what the
 * sender saw, not a re-run of the lookups. Visibility is chosen per share —
 * `link` for anything that can go in a coalition channel, `alliance` when the
 * viewer should have to be logged in.
 *
 * `buildPayload` is called at click time so the button always publishes what is
 * currently on screen.
 */
export default function ShareButton({ kind, buildPayload, title, writeHeaders = {} }) {
    const [share, setShare] = useState(null)
    const [visibility, setVisibility] = useState('link')
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState(null)

    async function publish(vis) {
        setBusy(true)
        setError(null)
        try {
            const res = await fetch('/api/share', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...writeHeaders },
                body: JSON.stringify({ kind, visibility: vis, title, payload: buildPayload() }),
            })
            if (!res.ok) {
                const body = await res.json().catch(() => ({}))
                throw new Error(body.error || `Server error: ${res.status}`)
            }
            const data = await res.json()
            setShare(data)
            setVisibility(vis)
        } catch (e) {
            setError(e.message)
        } finally {
            setBusy(false)
        }
    }

    if (error && !share) {
        return (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--red)' }}>
                    SHARE FAILED: {error}
                </span>
                <button onClick={() => setError(null)} style={CTRL}>RETRY</button>
            </span>
        )
    }

    if (!share) {
        return (
            <button
                onClick={() => publish(visibility)}
                disabled={busy}
                style={{ ...CTRL, color: busy ? 'var(--text-muted)' : 'var(--text-secondary)', cursor: busy ? 'default' : 'pointer' }}
            >{busy ? 'SHARING…' : 'SHARE'}</button>
        )
    }

    const url = `${window.location.origin}${share.url}`

    return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <a
                href={share.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                    fontFamily: 'Share Tech Mono, monospace', fontSize: 9,
                    color: 'var(--cyan)', textDecoration: 'none',
                    maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}
                title={url}
            >{url}</a>
            <CopyButton text={url} label="COPY LINK" copiedLabel="COPIED" />
            {/* Re-publishing rather than mutating: a share is an immutable
                snapshot, so switching audience makes a new one with a new URL
                and leaves any already-pasted link exactly as it was. */}
            <button
                onClick={() => publish(visibility === 'link' ? 'alliance' : 'link')}
                disabled={busy}
                style={{ ...CTRL, fontSize: 9 }}
                title={visibility === 'link'
                    ? 'Anyone with the link can view. Switch to alliance-only.'
                    : 'Viewer must be logged in. Switch to link-only.'}
            >{visibility === 'link' ? 'LINK ONLY' : 'ALLIANCE ONLY'}</button>
            {error && (
                <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--red)' }}>{error}</span>
            )}
        </span>
    )
}

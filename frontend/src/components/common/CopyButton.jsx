import React, { useState } from 'react'

/**
 * Copy-to-clipboard button with the async-clipboard → execCommand fallback.
 *
 * The fallback matters: navigator.clipboard is unavailable on insecure origins,
 * which includes the plain-HTTP LAN address people reach the dashboard on.
 *
 * Pass `getText` (evaluated on click) or `text`. Colours are props rather than
 * fixed because the call sites genuinely differ — the D-scan panel uses a muted
 * button, the pilot panels a cyan one — and this is a refactor, not a restyle.
 */
export default function CopyButton({
    getText,
    text = '',
    label = 'COPY',
    copiedLabel = 'COPIED',
    color = 'var(--cyan)',
    copiedColor = 'var(--green)',
    borderColor = 'var(--border-dim)',
    copiedBorderColor = null,
    style = {},
}) {
    const [copied, setCopied] = useState(false)

    const copy = async () => {
        const value = getText ? getText() : text
        try {
            await navigator.clipboard.writeText(value)
        } catch {
            const el = document.createElement('textarea')
            el.value = value
            document.body.appendChild(el)
            el.select()
            try { document.execCommand('copy') } catch { /* nothing left to try */ }
            document.body.removeChild(el)
        }
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    const border = copied ? (copiedBorderColor || borderColor) : borderColor

    return (
        <button
            onClick={copy}
            style={{
                background: 'none',
                border: `1px solid ${border}`,
                color: copied ? copiedColor : color,
                cursor: 'pointer',
                fontFamily: 'Share Tech Mono, monospace',
                fontSize: 10, padding: '2px 8px', letterSpacing: 1,
                transition: 'color 0.2s, border-color 0.2s',
                ...style,
            }}
        >{copied ? copiedLabel : label}</button>
    )
}

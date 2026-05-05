import React, { useState, useEffect, useRef } from 'react'

const S = {
    wrap: { position: 'relative' },
    btn: (active) => ({
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: 10,
        letterSpacing: 1,
        padding: '4px 10px',
        background: 'transparent',
        border: `1px solid ${active ? 'var(--amber-dim)' : 'var(--border-dim)'}`,
        color: active ? 'var(--amber)' : 'var(--text-secondary)',
        cursor: 'pointer',
        transition: 'all 0.2s',
        display: 'flex',
        alignItems: 'center',
        gap: 4,
    }),
    dot: {
        width: 5,
        height: 5,
        borderRadius: '50%',
        background: 'var(--amber)',
        boxShadow: '0 0 6px var(--amber)',
        animation: 'pulse-dot 2s infinite',
    },
    dropdown: {
        position: 'absolute',
        right: 0,
        top: 'calc(100% + 4px)',
        background: 'var(--bg-panel)',
        border: '1px solid var(--border-active)',
        padding: 14,
        zIndex: 500,
        minWidth: 240,
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: 11,
        color: 'var(--text-primary)',
        boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
    },
    title: {
        fontFamily: "'Orbitron', sans-serif",
        fontSize: 9,
        letterSpacing: 3,
        color: 'var(--cyan)',
        textTransform: 'uppercase',
        marginBottom: 10,
        paddingBottom: 6,
        borderBottom: '1px solid var(--border-dim)',
    },
    permRow: {
        marginBottom: 10,
        paddingBottom: 10,
        borderBottom: '1px solid var(--border-dim)',
    },
    permStatus: (status) => ({
        fontSize: 10,
        color: status === 'granted' ? 'var(--green)' :
               status === 'denied' ? 'var(--red)' : 'var(--amber)',
        marginBottom: 4,
    }),
    permBtn: {
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: 10,
        letterSpacing: 1,
        padding: '3px 10px',
        background: 'rgba(0,212,255,0.08)',
        border: '1px solid var(--cyan-dim)',
        color: 'var(--cyan)',
        cursor: 'pointer',
        width: '100%',
        marginTop: 4,
    },
    row: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 8,
    },
    label: {
        color: 'var(--text-secondary)',
        fontSize: 11,
    },
    toggle: (on) => ({
        width: 32,
        height: 16,
        borderRadius: 8,
        background: on ? 'var(--cyan-dim)' : 'var(--border-dim)',
        border: `1px solid ${on ? 'var(--cyan)' : 'var(--border-active)'}`,
        cursor: 'pointer',
        position: 'relative',
        transition: 'all 0.2s',
        flexShrink: 0,
    }),
    toggleKnob: (on) => ({
        position: 'absolute',
        top: 2,
        left: on ? 16 : 2,
        width: 10,
        height: 10,
        borderRadius: '50%',
        background: on ? 'var(--cyan)' : 'var(--text-muted)',
        transition: 'left 0.2s',
    }),
    threshRow: {
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        marginTop: -4,
        marginBottom: 8,
        paddingLeft: 4,
    },
    threshLabel: {
        color: 'var(--text-muted)',
        fontSize: 10,
        flex: 1,
    },
    threshInput: {
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: 10,
        width: 40,
        padding: '2px 4px',
        background: 'var(--bg-deep)',
        border: '1px solid var(--border-dim)',
        color: 'var(--text-primary)',
        textAlign: 'center',
    },
    deniedNote: {
        fontSize: 10,
        color: 'var(--text-muted)',
        fontStyle: 'italic',
        marginTop: 4,
    },
}

function Toggle({ on, onChange }) {
    return (
        <div style={S.toggle(on)} onClick={() => onChange(!on)}>
            <div style={S.toggleKnob(on)} />
        </div>
    )
}

export default function NotificationBell({ settings, saveSettings, permStatus, requestPermission }) {
    const [open, setOpen] = useState(false)
    const ref = useRef(null)

    // Close on outside click
    useEffect(() => {
        if (!open) return
        const handler = (e) => {
            if (ref.current && !ref.current.contains(e.target)) setOpen(false)
        }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [open])

    const permLabel = permStatus === 'granted' ? '● GRANTED' :
                      permStatus === 'denied' ? '● DENIED' :
                      permStatus === 'unsupported' ? '● UNSUPPORTED' : '○ NOT SET'

    const canEnable = permStatus === 'granted'
    const needsRequest = permStatus === 'default'

    return (
        <div style={S.wrap} ref={ref}>
            <button
                style={S.btn(settings.enabled)}
                onClick={() => setOpen(o => !o)}
                title="Alert Settings"
            >
                {settings.enabled && <span style={S.dot} />}
                ALERTS
            </button>
            {open && (
                <div style={S.dropdown}>
                    <div style={S.title}>Push Notifications</div>

                    {/* Permission row */}
                    <div style={S.permRow}>
                        <div style={S.permStatus(permStatus)}>{permLabel}</div>
                        {needsRequest && (
                            <button style={S.permBtn} onClick={requestPermission}>
                                GRANT PERMISSION
                            </button>
                        )}
                        {permStatus === 'denied' && (
                            <div style={S.deniedNote}>
                                Allow notifications in browser settings to enable alerts.
                            </div>
                        )}
                        {permStatus === 'unsupported' && (
                            <div style={S.deniedNote}>
                                Your browser does not support push notifications.
                            </div>
                        )}
                    </div>

                    {/* Master enable */}
                    <div style={S.row}>
                        <span style={{ ...S.label, color: canEnable ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                            Enable Alerts
                        </span>
                        <Toggle
                            on={settings.enabled && canEnable}
                            onChange={(v) => canEnable && saveSettings(p => ({ ...p, enabled: v }))}
                        />
                    </div>

                    {/* Alert types */}
                    <div style={{ opacity: (settings.enabled && canEnable) ? 1 : 0.4, transition: 'opacity 0.2s' }}>
                        <div style={S.row}>
                            <span style={S.label}>Sov Campaigns</span>
                            <Toggle
                                on={settings.campaigns}
                                onChange={(v) => saveSettings(p => ({ ...p, campaigns: v }))}
                            />
                        </div>

                        <div style={S.row}>
                            <span style={S.label}>Primary Sov PVP Spike</span>
                            <Toggle
                                on={settings.pvp}
                                onChange={(v) => saveSettings(p => ({ ...p, pvp: v }))}
                            />
                        </div>
                        {settings.pvp && (
                            <div style={S.threshRow}>
                                <span style={S.threshLabel}>min kills to alert:</span>
                                <input
                                    type="number"
                                    min={1}
                                    max={50}
                                    value={settings.pvpThreshold}
                                    style={S.threshInput}
                                    onChange={(e) => {
                                        const v = Math.max(1, Math.min(50, parseInt(e.target.value) || 1))
                                        saveSettings(p => ({ ...p, pvpThreshold: v }))
                                    }}
                                />
                            </div>
                        )}

                        <div style={{ ...S.row, marginBottom: 0 }}>
                            <span style={S.label}>ADM Critical Drop</span>
                            <Toggle
                                on={settings.admCritical}
                                onChange={(v) => saveSettings(p => ({ ...p, admCritical: v }))}
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

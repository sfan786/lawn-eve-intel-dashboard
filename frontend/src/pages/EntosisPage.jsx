import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { Link } from 'react-router-dom'
import CornerBrackets from '../components/common/CornerBrackets'
import EveLoginButton from '../components/common/EveLoginButton'
import ConstellationMap from '../components/ConstellationMap'
import DscanParser from '../components/DscanParser'
import LocalScanner from '../components/LocalScanner'
import TimerBoard from '../components/TimerBoard'
import FleetCompAnalyzer from '../components/FleetCompAnalyzer'
import KillFeed from '../components/KillFeed'
import NotificationBell from '../components/NotificationBell'
import { useAuth } from '../utils/useAuth'
import { useNotifications } from '../hooks/useNotifications'
import { getCampaignPhase, formatCountdown, formatEveTime, formatLocalTime, formatVulnWindow } from '../utils/campaignHelpers'
import {
    groupNodesByEvent, constellationNamesForCampaigns,
    filterConfigToConstellations, systemsForConstellation, eventTypeLabel,
    campaignSystemIds,
} from '../utils/entosisHelpers'

const STATUS_META = {
    unclaimed:  { label: 'UNCLAIMED',  color: '#6a8090', bg: 'rgba(106,128,144,0.08)' },
    running:    { label: 'RUNNING',    color: '#00d4ff', bg: 'rgba(0,212,255,0.08)'   },
    contested:  { label: 'CONTESTED',  color: '#ffaa00', bg: 'rgba(255,170,0,0.10)'   },
    captured:   { label: 'CAPTURED',   color: '#00ff88', bg: 'rgba(0,255,136,0.08)'   },
    lost:       { label: 'LOST',       color: '#ff3355', bg: 'rgba(255,51,85,0.08)'   },
}

const NEXT_STATUSES = {
    unclaimed:  ['running', 'contested'],
    running:    ['contested', 'captured', 'lost'],
    contested:  ['running', 'captured', 'lost'],
    captured:   [],
    lost:       [],
}

const btn = (color) => ({
    background: 'transparent',
    border: `1px solid ${color}`,
    color,
    fontFamily: 'Share Tech Mono',
    fontSize: 10,
    padding: '2px 7px',
    cursor: 'pointer',
    letterSpacing: 0.5,
})

const inputStyle = {
    background: '#060a0f', border: '1px solid #1a3a4a', color: '#c0d8e8',
    padding: '3px 7px', fontSize: 11, fontFamily: 'Share Tech Mono',
}

const mono = { fontFamily: 'Share Tech Mono' }

function NodeCard({ node, myName, canManage, onClaim, onUnclaim, onPatch, onDelete, flagEventEnded }) {
    const meta = STATUS_META[node.status] || STATUS_META.unclaimed
    const nextStatuses = NEXT_STATUSES[node.status] || []
    const isClaimedByMe = myName && node.claimed_by === myName
    // In the unlinked section, a node that still carries a campaign_id means its
    // campaign resolved and vanished from ESI — surface that.
    const eventEnded = flagEventEnded && node.campaign_id != null

    return (
        <div style={{
            background: '#0a1018',
            border: `1px solid ${meta.color}`,
            borderLeft: `3px solid ${meta.color}`,
            padding: '10px 12px',
            position: 'relative',
        }}>
            <CornerBrackets />

            {/* System + label */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                <div>
                    <div style={{ fontFamily: 'Orbitron', fontSize: 12, color: '#c0d8e8', letterSpacing: 1 }}>
                        {node.system_name}
                        {eventEnded && (
                            <span style={{ ...mono, fontSize: 9, color: '#6a8090', marginLeft: 6, letterSpacing: 0.5 }}>
                                EVENT ENDED
                            </span>
                        )}
                    </div>
                    {node.label && (
                        <div style={{ ...mono, fontSize: 10, color: '#6a8090', marginTop: 1 }}>
                            {node.label}
                        </div>
                    )}
                </div>
                <span style={{
                    ...mono, fontSize: 10,
                    color: meta.color,
                    background: meta.bg,
                    padding: '2px 6px',
                    border: `1px solid ${meta.color}`,
                    animation: node.status === 'contested' ? 'pulse-reffed 2s infinite' : undefined,
                }}>
                    {meta.label}
                </span>
            </div>

            {/* Claimed by */}
            <div style={{ ...mono, fontSize: 10, color: node.claimed_by ? '#00ff88' : '#6a8090', marginBottom: 8, minHeight: 16 }}>
                {node.claimed_by
                    ? <>PILOT: <span style={{ color: isClaimedByMe ? '#00ff88' : '#c0d8e8' }}>{node.claimed_by}</span></>
                    : 'UNCLAIMED'}
            </div>

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                {node.status === 'unclaimed' && (
                    <button style={btn('#00d4ff')} onClick={() => onClaim(node.id)}>
                        CLAIM
                    </button>
                )}
                {node.claimed_by && isClaimedByMe && node.status === 'running' && (
                    <button style={btn('#6a8090')} onClick={() => onUnclaim(node.id)}>
                        RELEASE
                    </button>
                )}
                {nextStatuses.map(s => (
                    <button key={s} style={btn(STATUS_META[s].color)} onClick={() => onPatch(node.id, { status: s })}>
                        {STATUS_META[s].label}
                    </button>
                ))}
                {canManage && (
                    <button style={{ ...btn('#ff3355'), marginLeft: 'auto' }} onClick={() => onDelete(node.id)}>
                        ✕
                    </button>
                )}
            </div>
        </div>
    )
}

function AddNodeRow({ systems, onAdd, onCancel, error }) {
    const [system, setSystem] = useState('')
    const [label, setLabel] = useState('')

    return (
        <form
            onSubmit={e => { e.preventDefault(); if (system) onAdd(system, label) }}
            style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', padding: '6px 0' }}
        >
            <select style={{ ...inputStyle, minWidth: 130 }} value={system} onChange={e => setSystem(e.target.value)} required>
                <option value="">— system —</option>
                {systems.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <input
                style={{ ...inputStyle, width: 120 }}
                value={label}
                onChange={e => setLabel(e.target.value)}
                placeholder="label (optional)"
                maxLength={40}
            />
            <button type="submit" style={btn('#00ff88')}>ADD</button>
            <button type="button" style={btn('#6a8090')} onClick={onCancel}>CANCEL</button>
            {error && <span style={{ ...mono, fontSize: 10, color: '#ff3355' }}>{error}</span>}
        </form>
    )
}

function NodeGrid({ nodes, ...cardProps }) {
    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 8 }}>
            {nodes.map(node => <NodeCard key={node.id} node={node} {...cardProps} />)}
        </div>
    )
}

function EventPanel({ campaign, nodes, config, canManage, showAdd, onToggleAdd, onAdd, addError, cardProps }) {
    const phase = getCampaignPhase(campaign)
    const isActive = phase.phase === 'nodes'
    const vuln = formatVulnWindow(campaign.vulnerable_start_time, campaign.vulnerable_end_time)
    const constName = config?.constellations?.[String(campaign.constellation_id)]?.name
    const systems = systemsForConstellation(config, campaign.constellation_id)

    return (
        <div className="panel panel-wide" style={{ borderLeft: `3px solid ${isActive ? '#ff3355' : '#ffaa00'}` }}>
            <CornerBrackets />
            <div className="panel-header" style={{ flexWrap: 'wrap', gap: 6 }}>
                <span className="panel-title">⚔ {campaign.system_name}</span>
                <span className="panel-badge">{eventTypeLabel(campaign.event_type)}</span>
                <span className="panel-badge" style={{ color: campaign.defender_is_friendly ? '#00ff88' : '#ffaa00' }}>
                    {campaign.defender_is_friendly ? 'DEFENSE' : 'RECONQUEST'}
                </span>
                {constName && <span className="panel-badge" style={{ color: '#6a8090' }}>{constName}</span>}
                {vuln && <span className="panel-badge" style={{ color: '#6a8090' }}>VULN {vuln}</span>}
                <span className="panel-badge" style={{
                    color: isActive ? '#ff3355' : '#ffaa00',
                    animation: isActive ? 'pulse-reffed 2s infinite' : undefined,
                    marginLeft: 'auto',
                }}>
                    {isActive ? 'NODES ACTIVE' : `NODES IN ${formatCountdown(phase.nodesSpawnTime)}`}
                </span>
                {canManage && (
                    <button style={btn('#00d4ff')} onClick={onToggleAdd}>
                        {showAdd ? 'CANCEL' : '+ NODE'}
                    </button>
                )}
            </div>

            <div style={{ padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                {isActive ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <div style={{ flex: 1, height: 5, background: 'rgba(255,255,255,0.05)', borderRadius: 2, overflow: 'hidden', display: 'flex' }}>
                            <div style={{ width: `${(campaign.attackers_score || 0) * 100}%`, background: '#ff3355' }} />
                            <div style={{ width: `${(campaign.defender_score || 0) * 100}%`, background: '#00ff88' }} />
                        </div>
                        <div style={{ ...mono, fontSize: 11, whiteSpace: 'nowrap' }}>
                            <span style={{ color: '#ff3355' }}>ATK {((campaign.attackers_score || 0) * 100).toFixed(0)}%</span>
                            <span style={{ color: '#6a8090', margin: '0 5px' }}>vs</span>
                            <span style={{ color: '#00ff88' }}>DEF {((campaign.defender_score || 0) * 100).toFixed(0)}%</span>
                        </div>
                    </div>
                ) : (
                    <div style={{ ...mono, fontSize: 11, color: '#8a9aa0' }}>
                        Reinforced — nodes spawn across <span style={{ color: '#c0d8e8' }}>{constName || 'the constellation'}</span> at{' '}
                        <span style={{ color: '#ffaa00' }}>{formatEveTime(phase.nodesSpawnTime)}</span>
                        <span style={{ color: '#6a8090' }}> ({formatLocalTime(phase.nodesSpawnTime)} local)</span>
                    </div>
                )}

                {showAdd && <AddNodeRow systems={systems} onAdd={onAdd} onCancel={onToggleAdd} error={addError} />}

                {nodes.length > 0 ? (
                    <NodeGrid nodes={nodes} {...cardProps} />
                ) : (
                    <div style={{ ...mono, fontSize: 10, color: '#6a8090' }}>
                        {isActive
                            ? 'No command nodes tracked yet — FC adds spawns with [+ NODE].'
                            : 'No nodes yet — pre-stage assignments with [+ NODE] before spawn.'}
                    </div>
                )}
            </div>
        </div>
    )
}

function CollapsibleTool({ title, defaultOpen, children }) {
    const [open, setOpen] = useState(defaultOpen)
    return (
        <div>
            <div
                onClick={() => setOpen(o => !o)}
                style={{
                    display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer',
                    padding: '5px 10px', background: '#0a1018', border: '1px solid #1a2a3a',
                    borderBottom: open ? 'none' : '1px solid #1a2a3a',
                }}
            >
                <span style={{ ...mono, fontSize: 10, color: '#00d4ff' }}>{open ? '▾' : '▸'}</span>
                <span style={{ fontFamily: 'Orbitron', fontSize: 10, color: '#8a9aa0', letterSpacing: 1.5 }}>{title}</span>
            </div>
            {open && children}
        </div>
    )
}

export default function EntosisPage() {
    const [nodes, setNodes] = useState([])
    const [config, setConfig] = useState(null)
    const [campaigns, setCampaigns] = useState([])
    const [sovereignty, setSovereignty] = useState({})
    const [killFeed, setKillFeed] = useState([])
    const [selectedSystem, setSelectedSystem] = useState(null)
    const [mapMode, setMapMode] = useState('subway')
    const [callsign, setCallsign] = useState(() => localStorage.getItem('entosis_callsign') || '')
    const [callsignInput, setCallsignInput] = useState(() => localStorage.getItem('entosis_callsign') || '')
    const [password, setPassword] = useState(() => localStorage.getItem('timer_auth') || '')
    const [isAuth, setIsAuth] = useState(false)
    const [authError, setAuthError] = useState(false)
    const [addFormFor, setAddFormFor] = useState(null)   // campaign_id | 'unlinked' | null
    const [addError, setAddError] = useState('')
    const [patchError, setPatchError] = useState('')
    const [lastUpdate, setLastUpdate] = useState(null)
    const pollRef = useRef(null)
    const intelPollRef = useRef(null)
    const configRef = useRef(null)

    const auth = useAuth()
    const { settings: notifSettings, saveSettings: saveNotifSettings, permStatus, requestPermission, checkAndNotify } = useNotifications()
    // FC-level actions (add/delete/clear nodes); identity used for claims; ability to claim.
    const canManage = auth.ssoEnabled ? auth.authorized : isAuth
    const myName = auth.ssoEnabled ? auth.characterName : callsign
    const canClaim = auth.ssoEnabled ? auth.loggedIn : !!callsign
    const writeHeaders = auth.ssoEnabled ? {} : { 'X-Timer-Auth': password }

    const fetchNodes = useCallback(async () => {
        try {
            const res = await fetch('/api/entosis/nodes')
            if (res.ok) { setNodes(await res.json()); setLastUpdate(new Date()) }
        } catch (_) {}
    }, [])

    const fetchConfig = useCallback(async () => {
        try {
            const res = await fetch('/api/config')
            if (res.ok) {
                const cfg = await res.json()
                configRef.current = cfg
                setConfig(cfg)
            }
        } catch (_) {}
    }, [])

    const fetchIntel = useCallback(async () => {
        try {
            const [campRes, sovRes] = await Promise.all([
                fetch('/api/campaigns'),
                fetch('/api/sovereignty'),
            ])
            let camp = null
            let sov = null
            if (campRes.ok) {
                const data = await campRes.json()
                if (Array.isArray(data)) { camp = data; setCampaigns(data) }
            }
            if (sovRes.ok) {
                const data = await sovRes.json()
                if (data && typeof data === 'object' && !data.error) { sov = data; setSovereignty(data) }
            }
            fetch('/api/zkill/feed')
                .then(r => (r.ok ? r.json() : []))
                .then(data => { if (Array.isArray(data)) setKillFeed(data) })
                .catch(() => {})

            // Browser alerts: new campaigns + nodes-spawned + ADM drops
            const cfg = configRef.current
            if (camp && sov && cfg?.constellations) {
                const primaryIds = new Set()
                const names = {}
                Object.values(cfg.constellations).forEach(c => {
                    Object.values(c.systems || {}).forEach(s => {
                        names[s.system_id] = s.name
                        if (c.is_primary ?? c.is_lawn) primaryIds.add(String(s.system_id))
                    })
                })
                const allianceShort = cfg?.alliance?.short_name || cfg?.alliance?.ticker || 'PRIMARY'
                checkAndNotify(camp, sov, {}, primaryIds, names, allianceShort)
            }
        } catch (_) {}
    }, [checkAndNotify])

    useEffect(() => {
        fetchNodes()
        fetchConfig()
        fetchIntel()
        pollRef.current = setInterval(fetchNodes, 5000)
        intelPollRef.current = setInterval(fetchIntel, 60000)
        return () => { clearInterval(pollRef.current); clearInterval(intelPollRef.current) }
    }, [fetchNodes, fetchConfig, fetchIntel])

    // Auto-check auth once on mount using the stored password (not re-run on keystroke)
    useEffect(() => {
        const storedPw = localStorage.getItem('timer_auth')
        if (!storedPw) return
        fetch('/api/auth/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: storedPw }),
        }).then(r => {
            setIsAuth(r.ok)
            if (!r.ok) setAuthError(true)
        }).catch(() => setIsAuth(false))
    }, [])

    const saveCallsign = () => {
        const cs = callsignInput.trim()
        setCallsign(cs)
        localStorage.setItem('entosis_callsign', cs)
    }

    const handleAuth = async (e) => {
        e.preventDefault()
        const res = await fetch('/api/auth/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password }),
        })
        if (res.ok) {
            setIsAuth(true); setAuthError(false)
            localStorage.setItem('timer_auth', password)
        } else {
            setIsAuth(false); setAuthError(true)
        }
    }

    const addNode = async (systemName, label, campaignId) => {
        setAddError('')
        try {
            const res = await fetch('/api/entosis/nodes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...writeHeaders },
                body: JSON.stringify({
                    system_name: systemName,
                    label: label || null,
                    campaign_id: campaignId ?? null,
                }),
            })
            if (!res.ok) {
                const data = await res.json().catch(() => ({}))
                setAddError(res.status === 401 ? (auth.ssoEnabled ? 'Not authorized — log in with EVE' : 'Auth failed — re-enter FC password') : (data.error || `Error ${res.status}`))
                return
            }
            setAddFormFor(null); setAddError('')
        } catch (err) {
            setAddError('Network error — try again')
            return
        }
        fetchNodes()
    }

    const patchNode = async (id, patch) => {
        setPatchError('')
        try {
            const res = await fetch(`/api/entosis/nodes/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(patch),
            })
            if (!res.ok) {
                const data = await res.json().catch(() => ({}))
                setPatchError(data.error || `Update failed (${res.status})`)
            }
        } catch (_) {
            setPatchError('Network error — update not saved')
        }
        fetchNodes()
    }

    const claimNode = (id) => {
        if (!canClaim) {
            if (auth.ssoEnabled) return auth.login()
            return alert('Set your callsign first.')
        }
        // In SSO mode the server stamps claimed_by from the logged-in character.
        patchNode(id, { claimed_by: myName, status: 'running' })
    }

    const unclaimNode = (id) => {
        patchNode(id, { claimed_by: '', status: 'unclaimed' })
    }

    const deleteNode = async (id) => {
        await fetch(`/api/entosis/nodes/${id}`, {
            method: 'DELETE',
            headers: { ...writeHeaders },
        })
        fetchNodes()
    }

    const clearAll = async () => {
        if (!confirm('Clear all command nodes?')) return
        await fetch('/api/entosis/nodes', {
            method: 'DELETE',
            headers: { ...writeHeaders },
        })
        fetchNodes()
    }

    // --- Event grouping + focused map config ---
    const { events, unlinked } = useMemo(() => groupNodesByEvent(nodes, campaigns), [nodes, campaigns])
    const focusedConfig = useMemo(() => {
        if (!config) return null
        return filterConfigToConstellations(config, constellationNamesForCampaigns(campaigns, config))
    }, [config, campaigns])
    // Kill feed scoped to systems in campaign constellations (where nodes spawn)
    const opKills = useMemo(() => {
        const ids = campaignSystemIds(campaigns, config)
        return (killFeed || []).filter(k => ids.has(String(k.system_id)))
    }, [killFeed, campaigns, config])
    const mapHasSystems = focusedConfig && Object.keys(
        (mapMode === 'subway' ? focusedConfig.map_layout_subway : focusedConfig.map_layout) || {}
    ).length > 0

    const activeCount = events.filter(e => getCampaignPhase(e.campaign).phase === 'nodes').length
    const upcomingCount = events.length - activeCount

    const primarySystems = config?.constellations ? Object.values(config.constellations)
        .filter(c => c.is_primary ?? c.is_lawn)
        .flatMap(c => Object.values(c.systems || {}).map(s => s.name))
        .sort()
        : []

    const cardProps = {
        myName, canManage,
        onClaim: claimNode, onUnclaim: unclaimNode,
        onPatch: patchNode, onDelete: deleteNode,
    }

    const headerStyle = {
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 16px', background: '#0a1018',
        borderBottom: '1px solid #1a2a3a', gap: 12, flexWrap: 'wrap',
    }

    const toggleAddFor = (key) => {
        setAddError('')
        setAddFormFor(cur => (cur === key ? null : key))
    }

    // Show the unlinked panel when it has nodes, or as the primary board when
    // no campaigns are detected (graceful fallback to the manual workflow).
    const showUnlinked = unlinked.length > 0 || events.length === 0

    return (
        <div style={{ minHeight: '100vh', background: '#060a0f', color: '#c0d8e8' }}>
            {/* Page header */}
            <div style={headerStyle}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <Link to="/" style={{ ...mono, fontSize: 10, color: '#6a8090', textDecoration: 'none' }}>
                        ← DASHBOARD
                    </Link>
                    <div>
                        <div style={{ fontFamily: 'Orbitron', fontSize: 14, color: '#00d4ff', letterSpacing: 2 }}>
                            ENTOSIS OPS
                        </div>
                        <div style={{ ...mono, fontSize: 10, color: '#6a8090', marginTop: 2 }}>
                            {lastUpdate ? `UPDATED ${lastUpdate.toLocaleTimeString()}` : 'CONNECTING...'}
                            {patchError && <span style={{ color: '#ff3355' }}> · {patchError}</span>}
                        </div>
                    </div>
                </div>

                {/* Summary badges */}
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <span style={{ ...mono, fontSize: 10, color: activeCount ? '#ff3355' : '#6a8090', border: `1px solid ${activeCount ? '#ff3355' : '#1a2a3a'}`, padding: '2px 7px' }}>
                        {activeCount} ACTIVE
                    </span>
                    <span style={{ ...mono, fontSize: 10, color: upcomingCount ? '#ffaa00' : '#6a8090', border: `1px solid ${upcomingCount ? '#ffaa00' : '#1a2a3a'}`, padding: '2px 7px' }}>
                        {upcomingCount} UPCOMING
                    </span>
                    <span style={{ ...mono, fontSize: 10, color: '#00d4ff', border: '1px solid #00d4ff', padding: '2px 7px', opacity: 0.9 }}>
                        {nodes.length} NODES
                    </span>
                </div>

                {/* Right controls */}
                <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                    <NotificationBell
                        settings={notifSettings}
                        saveSettings={saveNotifSettings}
                        permStatus={permStatus}
                        requestPermission={requestPermission}
                    />
                    {/* Callsign — only in legacy password mode; SSO uses the EVE character */}
                    {!auth.ssoEnabled && (
                        <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
                            <span style={{ ...mono, fontSize: 10, color: '#6a8090' }}>CALLSIGN</span>
                            <input
                                style={{ ...inputStyle, width: 110 }}
                                value={callsignInput}
                                onChange={e => setCallsignInput(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && saveCallsign()}
                                placeholder="your handle"
                                maxLength={32}
                            />
                            <button style={btn('#00d4ff')} onClick={saveCallsign}>SET</button>
                            {callsign && (
                                <span style={{ ...mono, fontSize: 10, color: '#00ff88' }}>
                                    ✓ {callsign}
                                </span>
                            )}
                        </div>
                    )}

                    {/* FC auth */}
                    {auth.ssoEnabled ? (
                        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                            {canManage && nodes.length > 0 && (
                                <button style={btn('#ff3355')} onClick={clearAll}>CLEAR ALL</button>
                            )}
                            <EveLoginButton auth={auth} />
                        </div>
                    ) : !isAuth ? (
                        <form onSubmit={handleAuth} style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
                            <input
                                type="password"
                                style={{ ...inputStyle, width: 90 }}
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="FC password"
                            />
                            <button type="submit" style={btn(authError ? '#ff3355' : '#ffaa00')}>
                                {authError ? 'WRONG PW' : 'FC LOGIN'}
                            </button>
                        </form>
                    ) : (
                        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                            <span style={{ ...mono, fontSize: 10, color: '#00ff88' }}>FC AUTHED</span>
                            {nodes.length > 0 && (
                                <button style={btn('#ff3355')} onClick={clearAll}>CLEAR ALL</button>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Body: event board + op map (left), intel tools (right) */}
            <div className="entosis-body" style={{ display: 'grid', gap: 8, padding: 12, alignItems: 'start' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 0 }}>
                    {/* Focused op map — only constellations with an active/upcoming event */}
                    <div className="panel panel-wide">
                        <CornerBrackets />
                        <div className="panel-header">
                            <span className="panel-title">OP MAP</span>
                            {events.length > 0 && (
                                <span className="panel-badge">
                                    {[...constellationNamesForCampaigns(campaigns, config || {})].join(' · ')}
                                </span>
                            )}
                            <button
                                style={{ ...btn('#00d4ff'), marginLeft: 'auto' }}
                                onClick={() => setMapMode(m => (m === 'subway' ? 'traditional' : 'subway'))}
                            >
                                {mapMode === 'subway' ? 'SUBWAY' : 'MAP'}
                            </button>
                        </div>
                        {mapHasSystems ? (
                            <ConstellationMap
                                config={focusedConfig}
                                sovereignty={sovereignty}
                                activity={{}}
                                campaigns={campaigns}
                                selectedSystem={selectedSystem}
                                onSelectSystem={setSelectedSystem}
                                mapMode={mapMode}
                            />
                        ) : (
                            <div style={{ ...mono, padding: 10, fontSize: 11, color: '#6a8090' }}>
                                {campaigns.length === 0
                                    ? 'NO ACTIVE SOV CAMPAIGNS — MAP STANDBY'
                                    : 'TARGET CONSTELLATION NOT IN DEPLOYMENT LAYOUT'}
                            </div>
                        )}
                    </div>

                    {/* Event board — one panel per ESI-detected campaign */}
                    {events.map(({ campaign, nodes: eventNodes }) => (
                        <EventPanel
                            key={campaign.campaign_id}
                            campaign={campaign}
                            nodes={eventNodes}
                            config={config}
                            canManage={canManage}
                            showAdd={addFormFor === campaign.campaign_id}
                            onToggleAdd={() => toggleAddFor(campaign.campaign_id)}
                            onAdd={(system, label) => addNode(system, label, campaign.campaign_id)}
                            addError={addFormFor === campaign.campaign_id ? addError : ''}
                            cardProps={cardProps}
                        />
                    ))}

                    {/* Unlinked / manual nodes */}
                    {showUnlinked && (
                        <div className="panel panel-wide">
                            <CornerBrackets />
                            <div className="panel-header">
                                <span className="panel-title">{events.length === 0 ? 'COMMAND NODES' : 'UNLINKED NODES'}</span>
                                {unlinked.length > 0 && <span className="panel-badge">{unlinked.length}</span>}
                                {canManage && (
                                    <button style={{ ...btn('#00d4ff'), marginLeft: 'auto' }} onClick={() => toggleAddFor('unlinked')}>
                                        {addFormFor === 'unlinked' ? 'CANCEL' : '+ NODE'}
                                    </button>
                                )}
                            </div>
                            <div style={{ padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                                {addFormFor === 'unlinked' && (
                                    <AddNodeRow
                                        systems={primarySystems}
                                        onAdd={(system, label) => addNode(system, label, null)}
                                        onCancel={() => toggleAddFor('unlinked')}
                                        error={addError}
                                    />
                                )}
                                {unlinked.length > 0 ? (
                                    <NodeGrid nodes={unlinked} {...cardProps} flagEventEnded />
                                ) : (
                                    <div style={{ ...mono, fontSize: 10, color: '#6a8090' }}>
                                        No manual nodes — events detected via ESI appear above automatically.
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Intel tools column */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 0 }}>
                    <CollapsibleTool title="DSCAN PARSER" defaultOpen>
                        <DscanParser />
                    </CollapsibleTool>
                    <CollapsibleTool title="LOCAL SCANNER" defaultOpen>
                        <LocalScanner />
                    </CollapsibleTool>
                    <CollapsibleTool title="OP KILL FEED" defaultOpen>
                        <KillFeed kills={opKills} config={config} />
                    </CollapsibleTool>
                    <CollapsibleTool title="FLEET COMP ANALYZER" defaultOpen={false}>
                        <FleetCompAnalyzer />
                    </CollapsibleTool>
                    <CollapsibleTool title="TIMERBOARD" defaultOpen={false}>
                        <TimerBoard />
                    </CollapsibleTool>
                </div>
            </div>
        </div>
    )
}

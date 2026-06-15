import React, { useState, useRef, useEffect, useMemo } from 'react'
import { getAdmColor } from '../utils/admHelpers'
import { getCampaignPhase, formatCountdown, formatVulnWindow } from '../utils/campaignHelpers'
import { getSystemUpgrades, getUpgradeSummary, UPGRADE_CATEGORY_COLORS } from '../utils/upgradeHelpers'
import {
    constellationColor,
    constellationBounds,
    viewBoxFor,
    neighbourRegionGroups,
    gatewayDestinations,
} from '../utils/mapHelpers'
import UpgradeBadges from './common/UpgradeBadges'
import { useAuth } from '../utils/useAuth'

const EMPTY_LAYOUT = {}
const EMPTY_CONNECTIONS = []

export default function ConstellationMap({ config, sovereignty, activity, campaigns, selectedSystem, onSelectSystem, mapMode = "subway", annotations = {}, onAnnotationChange, jumpBridges = [], intelAlerts = [] }) {
    const [tooltip, setTooltip] = useState(null)
    const [touchTransform, setTouchTransform] = useState({ scale: 1, x: 0, y: 0 })
    const [annotationEditor, setAnnotationEditor] = useState(null)
    const svgRef = useRef(null)
    const auth = useAuth()
    // SSO uses the session cookie; password mode sends the legacy header.
    const writeHeaders = auth.ssoEnabled ? {} : { "X-Timer-Auth": localStorage.getItem("timer_auth") || "" }
    const authHint = auth.ssoEnabled ? "Log in with EVE (Timers panel) to edit" : "FC password required — log in on the Timers panel"
    const touchStateRef = useRef(null)
    const mapContainerRef = useRef(null)

    const allianceShort = config?.alliance?.short_name || config?.alliance?.ticker || "PRIMARY"
    const regionLabel = config?.region?.name || ""
    const layoutTraditional = config?.map_layout || EMPTY_LAYOUT
    const layoutSubway = config?.map_layout_subway || EMPTY_LAYOUT
    const connections = config?.map_connections || EMPTY_CONNECTIONS
    const borderSystems = config?.border_systems || []

    useEffect(() => {
        if (!annotationEditor) return
        const handler = (e) => { if (e.key === 'Escape') setAnnotationEditor(null) }
        window.addEventListener('keydown', handler)
        return () => window.removeEventListener('keydown', handler)
    }, [annotationEditor])

    useEffect(() => {
        const el = mapContainerRef.current
        if (!el) return
        const handler = (e) => {
            if (touchStateRef.current) e.preventDefault()
        }
        el.addEventListener('touchmove', handler, { passive: false })
        return () => el.removeEventListener('touchmove', handler)
    }, [])

    function handleTouchStart(e) {
        if (e.touches.length === 1) {
            touchStateRef.current = {
                type: 'pan',
                startX: e.touches[0].clientX,
                startY: e.touches[0].clientY,
                lastX: e.touches[0].clientX,
                lastY: e.touches[0].clientY,
                moved: false,
            }
        } else if (e.touches.length === 2) {
            const dx = e.touches[0].clientX - e.touches[1].clientX
            const dy = e.touches[0].clientY - e.touches[1].clientY
            touchStateRef.current = {
                type: 'pinch',
                lastDist: Math.sqrt(dx * dx + dy * dy),
            }
        }
    }

    function handleTouchMove(e) {
        const state = touchStateRef.current
        if (!state) return
        if (state.type === 'pan' && e.touches.length === 1) {
            const dx = e.touches[0].clientX - state.lastX
            const dy = e.touches[0].clientY - state.lastY
            const totalDx = e.touches[0].clientX - state.startX
            const totalDy = e.touches[0].clientY - state.startY
            if (!state.moved && Math.sqrt(totalDx * totalDx + totalDy * totalDy) > 5) {
                state.moved = true
                setTooltip(null)
            }
            if (state.moved) {
                state.lastX = e.touches[0].clientX
                state.lastY = e.touches[0].clientY
                setTouchTransform(t => ({ ...t, x: t.x + dx, y: t.y + dy }))
            }
        } else if (state.type === 'pinch' && e.touches.length === 2) {
            const dx = e.touches[0].clientX - e.touches[1].clientX
            const dy = e.touches[0].clientY - e.touches[1].clientY
            const dist = Math.sqrt(dx * dx + dy * dy)
            const scaleDelta = dist / state.lastDist
            state.lastDist = dist
            setTouchTransform(t => ({
                ...t,
                scale: Math.min(5, Math.max(0.5, t.scale * scaleDelta)),
            }))
        }
    }

    function handleTouchEnd() {
        touchStateRef.current = null
    }

    const isTouchTransformed = touchTransform.scale !== 1 || touchTransform.x !== 0 || touchTransform.y !== 0

    const isSubway = mapMode === "subway"
    const activeLayout = isSubway ? layoutSubway : layoutTraditional
    const { vb: activeViewBox, w: vbWidth, h: vbHeight } = useMemo(
        () => viewBoxFor(activeLayout, mapMode),
        [activeLayout, mapMode]
    )

    const nameToId = {}
    const idToName = {}
    const primaryConstIds = new Set((config?.primary_constellation_ids || []).map(String))
    const primarySystemIds = new Set()
    if (config && config.constellations) {
        Object.entries(config.constellations).forEach(([cid, c]) => {
            const isPrimary = c.is_primary || c.is_lawn || primaryConstIds.has(String(cid))
            Object.values(c.systems).forEach(sys => {
                nameToId[sys.name] = String(sys.system_id)
                idToName[String(sys.system_id)] = sys.name
                if (isPrimary) primarySystemIds.add(String(sys.system_id))
            })
        })
    }
    if (config && config.neighbor_systems) {
        Object.values(config.neighbor_systems).forEach(sys => {
            nameToId[sys.name] = String(sys.system_id)
            idToName[String(sys.system_id)] = sys.name
        })
    }

    const primaryConstellationNames = useMemo(() => {
        const set = new Set()
        Object.values(activeLayout).forEach(p => {
            if (p.lawn && p.constellation) set.add(p.constellation)
        })
        return [...set].sort()
    }, [activeLayout])

    const neighbourRegions = useMemo(() => neighbourRegionGroups(activeLayout), [activeLayout])
    const gatewayLabels = useMemo(() => gatewayDestinations(activeLayout, connections), [activeLayout, connections])
    const gatewaySystems = useMemo(() => new Set(borderSystems), [borderSystems])

    // Map from system name → intel entry for systems with active hostile intel
    const intelAlertSet = useMemo(() => {
        const m = new Map()
        for (const e of intelAlerts) {
            if (!e.expired && !e.isClear && (e.count ?? 0) > 0) m.set(e.system, e)
        }
        return m
    }, [intelAlerts])

    function getColor(name) {
        const layout = activeLayout[name]
        if (!layout) return "#3a5060"
        if (layout.constellation === "neighbor") return "#444455"
        if (layout.lawn) {
            const sysId = nameToId[name]
            const sov = sysId ? (sovereignty[sysId] || {}) : {}
            if (sov.alliance_name && !sov.is_friendly) return "#ff3355"
            return "#00ff88"
        }
        return constellationColor(layout.constellation)
    }

    function isLostSystem(name) {
        const layout = activeLayout[name]
        if (!layout || !layout.lawn) return false
        const sysId = nameToId[name]
        if (!sysId) return false
        const sov = sovereignty[sysId] || {}
        return !!(sov.alliance_name && !sov.is_friendly)
    }

    function getPvpGlow(name) {
        const sysId = nameToId[name]
        if (!sysId) return 0
        const act = activity[sysId] || {}
        const pvp = (act.ship_kills || 0) + (act.pod_kills || 0)
        if (pvp >= 5) return 14
        if (pvp >= 1) return 8
        return 0
    }

    function getNpcRing(name) {
        const sysId = nameToId[name]
        if (!sysId) return null
        const npc = (activity[sysId] || {}).npc_kills || 0
        if (npc > 500) return { r: 24, o: 0.18 }
        if (npc > 200) return { r: 18, o: 0.10 }
        return null
    }

    function isReffed(name) {
        const sysId = nameToId[name]
        if (!sysId) return false
        return campaigns && campaigns.some(c => String(c.solar_system_id) === sysId)
    }

    function needsCriticalGrinding(name) {
        const layout = activeLayout[name]
        if (!layout || !layout.lawn) return false
        const sysId = nameToId[name]
        if (!sysId) return false
        const sov = sovereignty[sysId] || {}
        if (!sov.is_friendly) return false
        const adm = sov.adm || 0
        return adm > 0 && adm < 2
    }

    function needsCautionGrinding(name) {
        const layout = activeLayout[name]
        if (!layout || !layout.lawn) return false
        const sysId = nameToId[name]
        if (!sysId) return false
        const sov = sovereignty[sysId] || {}
        if (!sov.is_friendly) return false
        const adm = sov.adm || 0
        return adm >= 2 && adm < 4
    }

    function getConnectionStyle(from, to, type) {
        if (!isSubway) {
            const styles = {
                internal: { stroke: "#1a3040", width: 1.5, dash: "none", opacity: 0.8 },
                cross: { stroke: "#00d4ff", width: 1.2, dash: "6 3", opacity: 0.8 },
                regional: { stroke: "#cc44aa", width: 1, dash: "8 4", opacity: 0.8 },
                neighbor: { stroke: "#1a2030", width: 1, dash: "none", opacity: 0.5 },
            }
            return styles[type] || styles.internal
        }
        const fromPrimary = activeLayout[from]?.lawn
        const toPrimary = activeLayout[to]?.lawn
        const bothPrimary = fromPrimary && toPrimary

        if (bothPrimary && type === "internal") return { stroke: "#00ff88", width: 3, dash: "none", opacity: 1.0, cap: "round" }
        if (bothPrimary && type === "cross") return { stroke: "#00d4ff", width: 2.5, dash: "8 4", opacity: 1.0, cap: "round" }
        if ((fromPrimary || toPrimary) && !bothPrimary) return { stroke: "#ffaa00", width: 2.5, dash: "6 4", opacity: 0.9, cap: "round" }

        if (type === "neighbor") return { stroke: "#252535", width: 0.8, dash: "none", opacity: 0.4 }
        if (type === "regional") return { stroke: "#774466", width: 1, dash: "6 4", opacity: 0.5 }
        if (type === "cross") return { stroke: "#3a6070", width: 1.2, dash: "4 3", opacity: 0.6 }
        return { stroke: "#1e3040", width: 1.2, dash: "none", opacity: 0.65 }
    }

    async function handleSaveAnnotation() {
        const res = await fetch("/api/annotations", {
            method: "POST",
            headers: { "Content-Type": "application/json", ...writeHeaders },
            body: JSON.stringify({ system_name: annotationEditor.name, note: annotationEditor.note }),
        }).catch(() => null)
        if (!res || !res.ok) {
            setAnnotationEditor({ ...annotationEditor, error: res && res.status === 401 ? authHint : "Save failed" })
            return
        }
        setAnnotationEditor(null)
        if (onAnnotationChange) onAnnotationChange()
    }

    async function handleDeleteAnnotation() {
        const res = await fetch(`/api/annotations/${encodeURIComponent(annotationEditor.name)}`, {
            method: "DELETE",
            headers: { ...writeHeaders },
        }).catch(() => null)
        if (!res || !res.ok) {
            setAnnotationEditor({ ...annotationEditor, error: res && res.status === 401 ? authHint : "Delete failed" })
            return
        }
        setAnnotationEditor(null)
        if (onAnnotationChange) onAnnotationChange()
    }

    function handleHover(e, name) {
        if (annotationEditor) return
        const layout = activeLayout[name]
        const sysId = nameToId[name]
        const act = sysId ? (activity[sysId] || {}) : {}
        const sov = sysId ? (sovereignty[sysId] || {}) : {}

        const rect = svgRef.current.getBoundingClientRect()
        const sx = rect.width / vbWidth
        const sy = rect.height / vbHeight
        let tx = (layout.x + (isSubway ? 10 : 40)) * sx + rect.left + 20
        let ty = (layout.y + (isSubway ? 10 : 20)) * sy + rect.top - 10
        if (tx + 210 > window.innerWidth) tx -= 230

        const neighborInfo = config && config.neighbor_systems && sysId ? config.neighbor_systems[sysId] : null

        setTooltip({
            x: tx, y: ty, name,
            holder: sov.alliance_name || (layout.constellation === "neighbor" ? (layout.holder || layout.note || "Unknown") : "Unknown"),
            corp: sov.corporation_name || "",
            adm: sov.adm || 0,
            pvp: (act.ship_kills || 0) + (act.pod_kills || 0),
            npc: act.npc_kills || 0,
            jumps: act.jumps || 0,
            isNeighbor: layout.constellation === "neighbor",
            isPrimary: !!layout.lawn,
            is_friendly: sov.is_friendly || false,
            note: layout.note || (neighborInfo ? neighborInfo.region_name : null),
            vulnerable_start_time: sov.vulnerable_start_time || null,
            vulnerable_end_time: sov.vulnerable_end_time || null,
        })
    }

    const sortedConnections = isSubway
        ? [...connections].sort((a, b) => {
            const aPrimary = (activeLayout[a[0]]?.lawn && activeLayout[a[1]]?.lawn) ? 1 : 0
            const bPrimary = (activeLayout[b[0]]?.lawn && activeLayout[b[1]]?.lawn) ? 1 : 0
            return aPrimary - bPrimary
        })
        : connections

    return (
        <div style={{ position: 'relative' }}>
            <div
                className="map-container"
                ref={mapContainerRef}
                onTouchStart={handleTouchStart}
                onTouchMove={handleTouchMove}
                onTouchEnd={handleTouchEnd}
            >
                {isTouchTransformed && (
                    <button
                        className="map-reset-btn"
                        onClick={() => setTouchTransform({ scale: 1, x: 0, y: 0 })}
                    >
                        Reset View
                    </button>
                )}
                <div style={{
                    transform: `translate(${touchTransform.x}px, ${touchTransform.y}px) scale(${touchTransform.scale})`,
                    transformOrigin: 'center center',
                    width: '100%',
                }}>
                <svg ref={svgRef} viewBox={activeViewBox} xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#0a1520" strokeWidth="0.5" />
                        </pattern>
                        <filter id="glow-r"><feGaussianBlur stdDeviation="4" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
                        <filter id="glow-c"><feGaussianBlur stdDeviation="3" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
                        <filter id="glow-amber"><feGaussianBlur stdDeviation="3" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
                        <filter id="glow-green"><feGaussianBlur stdDeviation="5" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
                    </defs>
                    <rect x={-2000} y={-2000} width={6000} height={6000} fill="#030608" />
                    <rect x={-2000} y={-2000} width={6000} height={6000} fill="url(#grid)" />

                    {primaryConstellationNames.map(cname => {
                        const bounds = constellationBounds(activeLayout, cname)
                        if (!bounds) return null
                        return (
                            <g key={`const-${cname}`}>
                                <rect
                                    x={bounds.x} y={bounds.y}
                                    width={bounds.width} height={bounds.height}
                                    rx={6}
                                    fill={isSubway ? "rgba(0,255,136,0.015)" : "none"}
                                    stroke={isSubway ? "rgba(0,255,136,0.06)" : "#0a3020"}
                                    strokeWidth={isSubway ? 1 : 1.5}
                                    strokeDasharray={isSubway ? "6 4" : "4 4"}
                                />
                                <text
                                    x={bounds.x + 12}
                                    y={bounds.y + bounds.height - 8}
                                    fontFamily="Orbitron, sans-serif"
                                    fontSize={isSubway ? 11 : 9}
                                    fill={isSubway ? "rgba(0,255,136,0.25)" : "#0d3828"}
                                    letterSpacing="2"
                                >{cname}</text>
                            </g>
                        )
                    })}

                    {Object.entries(neighbourRegions).map(([rname, members]) => {
                        const xs = members.map(m => m.x)
                        const ys = members.map(m => m.y)
                        return (
                            <text
                                key={`nb-${rname}`}
                                x={Math.min(...xs)}
                                y={Math.min(...ys) - 12}
                                fontFamily="Share Tech Mono, monospace"
                                fontSize={isSubway ? 7 : 8}
                                fill={isSubway ? "#222233" : "#333344"}
                                letterSpacing="1"
                                fontStyle="italic"
                            >{rname}</text>
                        )
                    })}

                    {sortedConnections.map(([from, to, type]) => {
                        const a = activeLayout[from], b = activeLayout[to]
                        if (!a || !b) return null
                        const s = getConnectionStyle(from, to, type)
                        return <line key={`${from}-${to}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={s.stroke} strokeWidth={s.width} strokeDasharray={s.dash} opacity={s.opacity} strokeLinecap={s.cap || "butt"} />
                    })}

                    {jumpBridges.map(jb => {
                        const a = activeLayout[jb.system_a], b = activeLayout[jb.system_b]
                        if (!a || !b) return null
                        return (
                            <g key={`jb-${jb.id}`}>
                                <line x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                                    stroke="#cc44ff" strokeWidth={isSubway ? 2.5 : 2}
                                    strokeDasharray="10 4" opacity={0.85} strokeLinecap="round" />
                                {jb.label && (
                                    <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 5}
                                        textAnchor="middle" fontFamily="Share Tech Mono, monospace"
                                        fontSize={isSubway ? 8 : 7} fill="#cc44ff" opacity={0.7}>{jb.label}</text>
                                )}
                            </g>
                        )
                    })}

                    {Object.entries(activeLayout).map(([name, pos]) => {
                        const isN = pos.constellation === "neighbor"
                        const isPrimary = pos.lawn
                        const isGateway = isSubway && gatewaySystems.has(name)
                        const color = getColor(name)
                        const pvp = getPvpGlow(name)
                        const npc = getNpcRing(name)
                        const sysId = nameToId[name]
                        const isSel = sysId && selectedSystem === sysId
                        const sov = sysId ? (sovereignty[sysId] || {}) : {}
                        const adm = sov.adm || 0

                        let r, nameSize, nameOff, admSize, admOff, nodeOpacity, nameFill, nodeStroke, nodeFill
                        if (!isSubway) {
                            r = isN ? 4 : 6
                            nameSize = isN ? 8 : 10
                            nameOff = isN ? 10 : 13
                            admSize = 10
                            admOff = 22
                            nodeOpacity = isN ? 0.6 : 1
                            nameFill = isN ? "#554400" : color
                            nodeStroke = isN ? 1 : 1.5
                            nodeFill = isN ? "#0a0a08" : "#060a0f"
                        } else if (isN) {
                            r = 3; nameSize = 7; nameOff = 8; admSize = 0; admOff = 0
                            nodeOpacity = 0.55; nameFill = "#555565"; nodeStroke = 1; nodeFill = "#080810"
                        } else if (isPrimary) {
                            r = isGateway ? 12 : 10
                            nameSize = 13; nameOff = isGateway ? 22 : 18
                            admSize = 11; admOff = isGateway ? 28 : 24
                            nodeOpacity = 1; nameFill = "#e0fff0"; nodeStroke = isGateway ? 3 : 2.5; nodeFill = "#0a1a10"
                        } else {
                            r = 4; nameSize = 7.5; nameOff = 9; admSize = 0; admOff = 0
                            nodeOpacity = 0.8; nameFill = color; nodeStroke = 1; nodeFill = "#060a0f"
                        }

                        const critGrind = needsCriticalGrinding(name)
                        const cautGrind = needsCautionGrinding(name)
                        const isLost = isLostSystem(name)
                        if (isLost && isPrimary && isSubway) { nameFill = "#ff8888"; nodeFill = "#1a0408" }
                        const strokeColor = critGrind ? "#ff3355" : cautGrind ? "#ffaa00" : color
                        const strokeW = critGrind ? (isSubway && isPrimary ? 4 : 3) : cautGrind ? (isSubway && isPrimary ? 3 : 2) : isLost ? (isSubway && isPrimary ? 4 : 3) : nodeStroke
                        const nodeFilter = critGrind ? "url(#glow-r)" : cautGrind ? "url(#glow-amber)" : isLost ? "url(#glow-r)" : (isSubway && isPrimary ? "url(#glow-green)" : undefined)

                        const reffedR = isSubway ? (isPrimary ? r + 8 : r + 6) : 16
                        const selR = isSubway ? (isPrimary ? r + 4 : r + 3) : 11
                        const gatewayDest = isGateway ? gatewayLabels[name] : null

                        return (
                            <g key={name}
                                onMouseEnter={(e) => handleHover(e, name)}
                                onMouseLeave={() => { if (!annotationEditor) setTooltip(null) }}
                                onClick={() => sysId && onSelectSystem(sysId)}
                                onContextMenu={(e) => {
                                    if (isN) return
                                    e.preventDefault()
                                    let x = e.clientX, y = e.clientY
                                    if (x + 260 > window.innerWidth) x -= 270
                                    if (y + 180 > window.innerHeight) y -= 180
                                    setAnnotationEditor({ name, note: (annotations[name]?.note) || '', x, y })
                                }}
                                style={{ cursor: isN ? 'default' : 'pointer' }}
                            >
                                {isGateway && (
                                    <circle cx={pos.x} cy={pos.y} r={r + 5} fill="none" stroke="#ffaa00" strokeWidth="1.5" strokeDasharray="4 3" opacity={0.6} />
                                )}
                                {isLost && !isN && (
                                    <circle
                                        cx={pos.x} cy={pos.y}
                                        r={isSubway ? (isPrimary ? r + 12 : r + 8) : r + 10}
                                        fill="none"
                                        stroke="#ff3355"
                                        strokeWidth="2"
                                        strokeDasharray="5 3"
                                        filter="url(#glow-r)"
                                        opacity={0.75}
                                        style={{ animation: 'pulse-reffed 2.5s ease-in-out infinite' }}
                                    />
                                )}
                                {isReffed(name) && (() => {
                                    const sid = nameToId[name]
                                    if (!sid) return null
                                    const campaign = campaigns.find(c => String(c.solar_system_id) === sid)
                                    if (!campaign) return null

                                    const phase = getCampaignPhase(campaign)
                                    const isNodesActive = phase.phase === "nodes"

                                    return (
                                        <circle
                                            cx={pos.x} cy={pos.y} r={reffedR}
                                            fill="none"
                                            stroke={isNodesActive ? "#ff3355" : "#ffaa00"}
                                            strokeWidth={isNodesActive ? "2.5" : "2"}
                                            strokeDasharray={isNodesActive ? "6 2" : "4 3"}
                                            filter={isNodesActive ? "url(#glow-r)" : "url(#glow-amber)"}
                                            style={{
                                                animation: isNodesActive ?
                                                    'pulse-reffed 1s infinite' :
                                                    'pulse-reffed 2s infinite'
                                            }}
                                        />
                                    )
                                })()}
                                {intelAlertSet.has(name) && (
                                    <circle
                                        cx={pos.x} cy={pos.y}
                                        r={isN ? r + 5 : reffedR + 9}
                                        fill="none" stroke="#ff8800" strokeWidth="1.5"
                                        strokeDasharray="3 2" opacity={0.9}
                                        style={{ animation: 'pulse-reffed 1.2s ease-in-out infinite' }}
                                    />
                                )}
                                {npc && <circle cx={pos.x} cy={pos.y} r={isSubway && isPrimary ? npc.r * 1.3 : npc.r} fill={`rgba(0,212,255,${npc.o})`} />}
                                {pvp > 0 && <circle cx={pos.x} cy={pos.y} r={isSubway && isPrimary ? pvp * 1.3 : pvp} fill="rgba(255,51,85,0.3)" filter="url(#glow-r)" />}
                                {isSel && <circle cx={pos.x} cy={pos.y} r={selR} fill="none" stroke="#00d4ff" strokeWidth="1.5" strokeDasharray="3 2" opacity={0.8} filter="url(#glow-c)" />}
                                <circle cx={pos.x} cy={pos.y} r={r}
                                    fill={nodeFill}
                                    stroke={strokeColor}
                                    strokeWidth={strokeW}
                                    strokeDasharray={isN && !isSubway ? "2 2" : "none"}
                                    opacity={nodeOpacity}
                                    filter={nodeFilter}
                                />
                                {critGrind && (
                                    <text
                                        x={pos.x + (isSubway && isPrimary ? 14 : 9)}
                                        y={pos.y - (isSubway && isPrimary ? 12 : 8)}
                                        fontFamily="Orbitron, sans-serif"
                                        fontSize={isSubway && isPrimary ? "14" : "11"}
                                        fill="#ff3355"
                                        fontWeight="bold"
                                        opacity={0.95}
                                    >!</text>
                                )}
                                {isLost && !isN && (
                                    <text
                                        x={pos.x + (isSubway && isPrimary ? 14 : 9)}
                                        y={pos.y - (isSubway && isPrimary ? 12 : 8)}
                                        fontFamily="Orbitron, sans-serif"
                                        fontSize={isSubway && isPrimary ? "13" : "10"}
                                        fill="#ff3355"
                                        fontWeight="bold"
                                        opacity={0.9}
                                    >✕</text>
                                )}
                                {!isN && annotations[name] && (
                                    <circle
                                        cx={pos.x + r + 2} cy={pos.y - r - 2}
                                        r={isSubway && isPrimary ? 3.5 : 2.5}
                                        fill="#ffaa00" opacity={0.9}
                                    />
                                )}
                                <text x={pos.x} y={pos.y - nameOff}
                                    textAnchor="middle"
                                    fontFamily="Share Tech Mono, monospace"
                                    fontSize={nameSize}
                                    fill={nameFill}
                                    opacity={isSubway ? (isN ? 0.4 : isPrimary ? 1 : 0.7) : (isN ? 0.6 : 0.9)}
                                    letterSpacing={isSubway && isPrimary ? "1" : "0.5"}
                                    fontWeight={isSubway && isPrimary ? "bold" : "normal"}
                                    stroke={isSubway && isPrimary ? "#060a0f" : "none"}
                                    strokeWidth={isSubway && isPrimary ? 3 : 0}
                                    paintOrder={isSubway && isPrimary ? "stroke" : "normal"}
                                >{name}</text>
                                {!isN && adm > 0 && admSize > 0 && (() => {
                                    const admText = adm.toFixed(1)
                                    const admCol = getAdmColor(adm)
                                    const admX = pos.x
                                    const admY = pos.y + admOff + (isSubway && isPrimary ? 2 : 0)
                                    if (isSubway) {
                                        const charW = admSize * 0.62
                                        const pillPadX = 4, pillPadY = 3
                                        const pillW = admText.length * charW + pillPadX * 2
                                        const pillH = admSize + pillPadY * 2
                                        const centerY = admY - admSize * 0.3
                                        return (
                                            <g>
                                                <rect
                                                    x={admX - pillW / 2} y={centerY - pillH / 2}
                                                    width={pillW} height={pillH}
                                                    rx={3} fill="#060a0f" opacity={1}
                                                    stroke={admCol} strokeWidth={0.5} strokeOpacity={0.35}
                                                />
                                                <text x={admX} y={centerY}
                                                    textAnchor="middle" dominantBaseline="central"
                                                    fontFamily="Share Tech Mono, monospace"
                                                    fontSize={admSize} fill={admCol} fontWeight="bold"
                                                    stroke="#060a0f" strokeWidth={2.5} paintOrder="stroke"
                                                >{admText}</text>
                                            </g>
                                        )
                                    }
                                    return (
                                        <text x={admX} y={admY}
                                            textAnchor="middle"
                                            fontFamily="Share Tech Mono, monospace"
                                            fontSize={admSize} fill={admCol} fontWeight="bold"
                                            stroke="#060a0f" strokeWidth={3} paintOrder="stroke"
                                        >{admText}</text>
                                    )
                                })()}
                                {isPrimary && (() => {
                                    const upSummary = getUpgradeSummary(name, config)
                                    const cats = []
                                    if (upSummary.military > 0) cats.push(UPGRADE_CATEGORY_COLORS.military)
                                    if (upSummary.industry > 0) cats.push(UPGRADE_CATEGORY_COLORS.industry)
                                    if (upSummary.strategic > 0) cats.push(UPGRADE_CATEGORY_COLORS.strategic)
                                    if (cats.length === 0) return null
                                    const dotR = isSubway ? 1.5 : 1.2
                                    const dotGap = isSubway ? 4 : 3.5
                                    const baseX = pos.x - (cats.length - 1) * dotGap / 2
                                    const baseY = pos.y + (adm > 0 ? admOff + (isSubway ? 14 : 8) : nameOff)
                                    return cats.map((c, ci) => (
                                        <circle key={ci} cx={baseX + ci * dotGap} cy={baseY} r={dotR} fill={c} opacity={0.8} />
                                    ))
                                })()}
                                {isGateway && gatewayDest && (
                                    <text x={pos.x} y={pos.y + r + 44} textAnchor="middle" fontFamily="Orbitron, sans-serif" fontSize="9" fill="#ffaa00" opacity={0.85} letterSpacing="1">{'→'} {gatewayDest.toUpperCase()}</text>
                                )}
                                {isN && pos.holder && (
                                    <text x={pos.x} y={pos.y + (isSubway ? 8 : 14)} textAnchor="middle" fontFamily="Share Tech Mono, monospace" fontSize="6" fill="#443300" opacity={isSubway ? 0.3 : 0.5}>{pos.holder}</text>
                                )}
                                {isN && pos.note && !pos.holder && (
                                    <text x={pos.x} y={pos.y + (isSubway ? 12 : 14)} textAnchor="middle" fontFamily="Share Tech Mono, monospace" fontSize={isSubway ? "5" : "6"} fill={isSubway ? "#444455" : "#444"} fontStyle="italic" opacity={isSubway ? 0.5 : 1}>{pos.note}</text>
                                )}
                            </g>
                        )
                    })}
                </svg>
                </div>
            </div>

            {tooltip && (
                <div className="map-tooltip visible" style={{ left: tooltip.x, top: tooltip.y }}>
                    <div className="map-tooltip-name" style={{ color: tooltip.isNeighbor ? '#ffaa00' : (tooltip.isPrimary && !tooltip.is_friendly && tooltip.holder && tooltip.holder !== 'Unknown') ? '#ff3355' : '#00ff88' }}>{tooltip.name}</div>
                    <div className="map-tooltip-row"><span className="map-tooltip-label">Holder</span><span style={{ color: tooltip.isPrimary && !tooltip.is_friendly && tooltip.holder && tooltip.holder !== 'Unknown' ? '#ff8888' : undefined }}>{tooltip.holder}</span></div>
                    {tooltip.corp && <div className="map-tooltip-row"><span className="map-tooltip-label">Corp</span><span>{tooltip.corp}</span></div>}
                    <div className="map-tooltip-row">
                        <span className="map-tooltip-label">ADM</span>
                        <span style={{ color: tooltip.adm > 0 ? getAdmColor(tooltip.adm) : '#3a5060' }}>
                            {tooltip.adm > 0 ? tooltip.adm.toFixed(1) : '—'}
                        </span>
                    </div>
                    {tooltip.isPrimary && !tooltip.is_friendly && tooltip.holder && tooltip.holder !== 'Unknown' && (
                        <div style={{
                            fontSize: 11,
                            color: '#ff3355',
                            marginTop: 6,
                            paddingTop: 6,
                            fontWeight: 'bold',
                            borderTop: '1px solid #ff335533'
                        }}>
                            ☠ HOSTILE SOV — RECONQUEST NEEDED
                        </div>
                    )}
                    {tooltip.isPrimary && tooltip.adm > 0 && tooltip.adm < 4 && tooltip.is_friendly && (
                        <div style={{
                            fontSize: 10,
                            color: tooltip.adm < 2 ? '#ff3355' : '#ffaa00',
                            marginTop: 4,
                            fontStyle: 'italic'
                        }}>
                            {tooltip.adm < 2 ? '⚠ Critical - Needs immediate grinding' : '⚠ Below safe threshold (4.0)'}
                        </div>
                    )}
                    {isReffed(tooltip.name) && (() => {
                        const sid = nameToId[tooltip.name]
                        if (!sid) return null
                        const campaign = campaigns.find(c => String(c.solar_system_id) === sid)
                        if (!campaign) return null

                        const phase = getCampaignPhase(campaign)
                        const isNodesActive = phase.phase === "nodes"

                        return (
                            <div style={{
                                fontSize: 11,
                                color: isNodesActive ? '#ff3355' : '#ffaa00',
                                marginTop: 8,
                                paddingTop: 8,
                                fontWeight: 'bold',
                                borderTop: `1px solid ${isNodesActive ? '#ff335533' : '#ffaa0033'}`
                            }}>
                                {isNodesActive ? (
                                    <>
                                        ⚠ NODES ACTIVE — {((campaign.attackers_score || 0) * 100).toFixed(0)}% vs {((campaign.defender_score || 0) * 100).toFixed(0)}%
                                    </>
                                ) : (
                                    <>
                                        ⚠ REINFORCED — Nodes in {formatCountdown(phase.nodesSpawnTime)}
                                    </>
                                )}
                            </div>
                        )
                    })()}
                    <div className="map-tooltip-row"><span className="map-tooltip-label">PVP kills</span><span style={{ color: tooltip.pvp > 0 ? '#ff3355' : '#3a5060' }}>{tooltip.pvp}</span></div>
                    <div className="map-tooltip-row"><span className="map-tooltip-label">NPC kills</span><span style={{ color: '#00d4ff' }}>{tooltip.npc}</span></div>
                    <div className="map-tooltip-row"><span className="map-tooltip-label">Jumps</span><span style={{ color: '#ffaa00' }}>{tooltip.jumps}</span></div>
                    {tooltip.vulnerable_start_time && tooltip.vulnerable_end_time && (
                        <div style={{
                            fontSize: 10,
                            color: '#6a8090',
                            marginTop: 6,
                            paddingTop: 6,
                            borderTop: '1px solid rgba(106,128,144,0.2)',
                            fontFamily: 'Share Tech Mono, monospace'
                        }}>
                            Vuln Window: <span style={{ color: '#00d4ff' }}>
                                {formatVulnWindow(tooltip.vulnerable_start_time, tooltip.vulnerable_end_time)}
                            </span>
                        </div>
                    )}
                    {tooltip.isPrimary && (() => {
                        const upgrades = getSystemUpgrades(tooltip.name, config)
                        if (upgrades.length === 0) return null
                        return (
                            <div className="upgrade-badges">
                                <div style={{ width: '100%', fontSize: 8, color: '#6a8090', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 2 }}>Sov Upgrades</div>
                                <UpgradeBadges upgrades={upgrades} config={config} />
                            </div>
                        )
                    })()}
                    {tooltip.note && <div style={{ marginTop: 4, color: '#6a8090', fontStyle: 'italic', fontSize: 10 }}>{tooltip.note}</div>}
                    {annotations[tooltip.name] && (
                        <div style={{
                            marginTop: 6, paddingTop: 6,
                            borderTop: '1px solid rgba(255,170,0,0.2)',
                            color: '#ffaa00', fontSize: 10, fontStyle: 'italic',
                        }}>📌 {annotations[tooltip.name].note}</div>
                    )}
                </div>
            )}

            {annotationEditor && (
                <div style={{
                    position: 'fixed', left: annotationEditor.x, top: annotationEditor.y,
                    zIndex: 10001,
                    background: '#060a0f',
                    border: '1px solid rgba(255,170,0,0.4)',
                    padding: '8px 10px',
                    minWidth: 230,
                    fontFamily: 'Share Tech Mono, monospace',
                    fontSize: 11,
                    boxShadow: '0 4px 20px rgba(0,0,0,0.8)',
                }}>
                    <div style={{ color: '#ffaa00', fontSize: 10, letterSpacing: 1, marginBottom: 6, fontFamily: 'Orbitron, sans-serif' }}>
                        NOTE: {annotationEditor.name}
                    </div>
                    <textarea
                        autoFocus
                        value={annotationEditor.note}
                        onChange={e => setAnnotationEditor({ ...annotationEditor, note: e.target.value })}
                        maxLength={120}
                        rows={2}
                        placeholder="Enter note (120 chars max)..."
                        style={{
                            width: '100%', background: 'rgba(0,0,0,0.3)',
                            border: '1px solid rgba(106,128,144,0.3)',
                            color: '#c0d4e0',
                            fontFamily: 'Share Tech Mono, monospace', fontSize: 11,
                            padding: '4px 6px', resize: 'none', outline: 'none',
                            boxSizing: 'border-box',
                        }}
                    />
                    {annotationEditor.error && (
                        <div style={{ color: '#ff3355', fontSize: 10, marginTop: 4 }}>{annotationEditor.error}</div>
                    )}
                    <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                        <button onClick={handleSaveAnnotation} style={{
                            background: 'none', border: '1px solid rgba(0,255,136,0.4)',
                            color: '#00ff88', cursor: 'pointer',
                            fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                            padding: '2px 10px', letterSpacing: 1,
                        }}>SAVE</button>
                        {annotations[annotationEditor.name] && (
                            <button onClick={handleDeleteAnnotation} style={{
                                background: 'none', border: '1px solid rgba(255,51,85,0.4)',
                                color: '#ff3355', cursor: 'pointer',
                                fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                                padding: '2px 10px', letterSpacing: 1,
                            }}>DELETE</button>
                        )}
                        <button onClick={() => setAnnotationEditor(null)} style={{
                            background: 'none', border: '1px solid rgba(106,128,144,0.3)',
                            color: '#6a8090', cursor: 'pointer',
                            fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                            padding: '2px 10px', letterSpacing: 1,
                        }}>CANCEL</button>
                    </div>
                </div>
            )}

            <div className="map-legend">
                <div className="map-legend-item">
                    <div style={{ width: 8, height: 8, background: 'transparent', border: '2.5px dashed #ff3355', borderRadius: '50%' }} />
                    <span>Nodes Active</span>
                </div>
                <div className="map-legend-item">
                    <div style={{ width: 8, height: 8, background: 'transparent', border: '1.5px dashed #ff8800', borderRadius: '50%' }} />
                    <span>Intel alert</span>
                </div>
                <div className="map-legend-item">
                    <div style={{ width: 8, height: 8, background: 'transparent', border: '2px dashed #ffaa00', borderRadius: '50%' }} />
                    <span>Reffed (active timer)</span>
                </div>
                <div className="map-legend-item">
                    <div style={{ width: 8, height: 8, background: 'transparent', border: '3px solid #ff3355', borderRadius: '50%' }} />
                    <span>Critical (ADM &lt; 2)</span>
                </div>
                <div className="map-legend-item">
                    <div style={{ width: 8, height: 8, background: 'transparent', border: '2px solid #ffaa00', borderRadius: '50%' }} />
                    <span>Caution (ADM 2-4)</span>
                </div>
                <div className="map-legend-item"><div className="map-legend-dot" style={{ background: '#00ff88' }} /><span>{allianceShort} Sov</span></div>
                <div className="map-legend-item"><div className="map-legend-dot" style={{ background: 'rgba(0,212,255,0.3)', border: '1px solid rgba(0,212,255,0.2)' }} /><span>NPC ratting</span></div>
                <div className="map-legend-item"><div className="map-legend-dot" style={{ background: '#ff3355' }} /><span>PVP danger</span></div>
                <div className="map-legend-item">
                    <div style={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                        <div style={{ width: 4, height: 4, borderRadius: '50%', background: '#ff6677' }} />
                        <div style={{ width: 4, height: 4, borderRadius: '50%', background: '#00ff88' }} />
                        <div style={{ width: 4, height: 4, borderRadius: '50%', background: '#00d4ff' }} />
                    </div>
                    <span>Upgrades (mil/ind/str)</span>
                </div>
                <div className="map-legend-item">
                    <div style={{ width: 16, height: 0, borderTop: '2.5px dashed #cc44ff', opacity: 0.85 }} />
                    <span>Jump Bridge</span>
                </div>
                <div className="map-legend-item">
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#ffaa00', opacity: 0.9 }} />
                    <span>Has note (right-click)</span>
                </div>
                {isSubway ? (
                    <>
                        <div className="map-legend-item">
                            <div style={{ width: 10, height: 10, background: 'transparent', border: '2px solid #ffaa00', borderRadius: '50%', boxShadow: '0 0 0 2px transparent, 0 0 0 3px #ffaa0066' }} />
                            <span>Gateway (exit)</span>
                        </div>
                        <div className="map-legend-item"><div style={{ width: 16, height: 0, borderTop: '3px solid #00ff88' }} /><span>{allianceShort} gate</span></div>
                        <div className="map-legend-item"><div style={{ width: 16, height: 0, borderTop: '2.5px dashed #00d4ff' }} /><span>{allianceShort} bridge</span></div>
                        <div className="map-legend-item"><div style={{ width: 16, height: 0, borderTop: '2.5px dashed #ffaa00' }} /><span>{allianceShort} exit</span></div>
                        <div className="map-legend-item"><div style={{ width: 16, height: 0, borderTop: '1px solid #1a2a35', opacity: 0.6 }} /><span>{regionLabel || 'Region'} gate</span></div>
                        <div className="map-legend-item"><div style={{ width: 16, height: 0, borderTop: '1px dashed #663355', opacity: 0.5 }} /><span>Regional gate</span></div>
                    </>
                ) : (
                    <>
                        <div className="map-legend-item"><div className="map-legend-dot" style={{ background: '#444455', border: '1px dashed #444455' }} /><span>Neighbor region</span></div>
                        <div className="map-legend-item"><div style={{ width: 16, height: 0, borderTop: '1.5px solid #1a3040' }} /><span>Internal gate</span></div>
                        <div className="map-legend-item"><div style={{ width: 16, height: 0, borderTop: '1.5px dashed #00d4ff', opacity: 0.6 }} /><span>Cross-constellation</span></div>
                        <div className="map-legend-item"><div style={{ width: 16, height: 0, borderTop: '1.5px dashed #cc44aa' }} /><span>Regional gate</span></div>
                    </>
                )}
            </div>
        </div>
    )
}

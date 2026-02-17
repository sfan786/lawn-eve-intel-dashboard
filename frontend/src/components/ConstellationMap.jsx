import React, { useState, useRef } from 'react'
import { MAP_LAYOUT, MAP_LAYOUT_SUBWAY, MAP_CONNECTIONS } from '../data/mapData'
import { getAdmColor } from '../utils/admHelpers'
import { getCampaignPhase, formatCountdown, formatVulnWindow } from '../utils/campaignHelpers'
import { getSystemUpgrades, getUpgradeSummary, UPGRADE_CATEGORY_COLORS } from '../utils/upgradeHelpers'
import UpgradeBadges from './common/UpgradeBadges'

export default function ConstellationMap({ config, sovereignty, activity, campaigns, selectedSystem, onSelectSystem }) {
    const [tooltip, setTooltip] = useState(null)
    const [mapMode, setMapMode] = useState("subway")
    const svgRef = useRef(null)

    const isSubway = mapMode === "subway"
    const activeLayout = isSubway ? MAP_LAYOUT_SUBWAY : MAP_LAYOUT
    const activeViewBox = isSubway ? "-10 -30 1180 1000" : "-40 -20 1220 790"
    const vbWidth = isSubway ? 1180 : 1220
    const vbHeight = isSubway ? 1000 : 790

    // Build name<->ID mappings from ALL constellations + neighbors
    const nameToId = {}
    const idToName = {}
    const lawnConstellationIds = new Set((config && config.lawn_constellation_ids || []).map(String))
    const lawnSystemIds = new Set()
    if (config && config.constellations) {
        Object.entries(config.constellations).forEach(([cid, c]) => {
            const isLawn = c.is_lawn || lawnConstellationIds.has(String(cid))
            Object.values(c.systems).forEach(sys => {
                nameToId[sys.name] = String(sys.system_id)
                idToName[String(sys.system_id)] = sys.name
                if (isLawn) lawnSystemIds.add(String(sys.system_id))
            })
        })
    }
    if (config && config.neighbor_systems) {
        Object.values(config.neighbor_systems).forEach(sys => {
            nameToId[sys.name] = String(sys.system_id)
            idToName[String(sys.system_id)] = sys.name
        })
    }

    function getColor(name) {
        const layout = activeLayout[name]
        if (!layout) return "#3a5060"

        if (layout.constellation === "neighbor") {
            return "#444455"
        }

        if (layout.lawn || layout.constellation === "6-CBBM" || layout.constellation === "2Q-8WA") {
            return "#00ff88"
        }

        if (layout.constellation === "S4S-SD") return "#668844"
        if (layout.constellation === "3NA-Z1") return "#667744"
        if (layout.constellation === "78-6RI") return "#446688"
        if (layout.constellation === "U-HSM3") return "#445577"
        if (layout.constellation === "2O-VY7") return "#444466"
        if (layout.constellation === "8UD2-J") return "#554466"
        if (layout.constellation === "XPG-HE") return "#664455"
        if (layout.constellation === "P-B2NE") return "#553355"

        return "#555555"
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
        const adm = sov.adm || 0
        return adm > 0 && adm < 2
    }

    function needsCautionGrinding(name) {
        const layout = activeLayout[name]
        if (!layout || !layout.lawn) return false
        const sysId = nameToId[name]
        if (!sysId) return false
        const sov = sovereignty[sysId] || {}
        const adm = sov.adm || 0
        return adm >= 2 && adm < 4
    }

    const GATEWAY_SYSTEMS = ["UDVW-O", "N-JK02"]

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
        const fromLawn = activeLayout[from]?.lawn
        const toLawn = activeLayout[to]?.lawn
        const bothLawn = fromLawn && toLawn

        if (bothLawn && type === "internal") return { stroke: "#00ff88", width: 3, dash: "none", opacity: 1.0, cap: "round" }
        if (bothLawn && type === "cross") return { stroke: "#00d4ff", width: 2.5, dash: "8 4", opacity: 1.0, cap: "round" }
        if ((fromLawn || toLawn) && !bothLawn) return { stroke: "#ffaa00", width: 2.5, dash: "6 4", opacity: 0.9, cap: "round" }

        if (type === "neighbor") return { stroke: "#252535", width: 0.8, dash: "none", opacity: 0.4 }
        if (type === "regional") return { stroke: "#774466", width: 1, dash: "6 4", opacity: 0.5 }
        if (type === "cross") return { stroke: "#3a6070", width: 1.2, dash: "4 3", opacity: 0.6 }
        return { stroke: "#1e3040", width: 1.2, dash: "none", opacity: 0.65 }
    }

    function handleHover(e, name) {
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
            isLawn: !!layout.lawn,
            note: layout.note || (neighborInfo ? neighborInfo.region_name : null),
            vulnerable_start_time: sov.vulnerable_start_time || null,
            vulnerable_end_time: sov.vulnerable_end_time || null,
        })
    }

    const sortedConnections = isSubway
        ? [...MAP_CONNECTIONS].sort((a, b) => {
            const aLawn = (activeLayout[a[0]]?.lawn && activeLayout[a[1]]?.lawn) ? 1 : 0
            const bLawn = (activeLayout[b[0]]?.lawn && activeLayout[b[1]]?.lawn) ? 1 : 0
            return aLawn - bLawn
        })
        : MAP_CONNECTIONS

    return (
        <div style={{ position: 'relative' }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
                <div className="map-mode-toggle">
                    <button className={`map-mode-btn ${mapMode === 'traditional' ? 'active' : ''}`} onClick={() => setMapMode('traditional')}>Traditional</button>
                    <button className={`map-mode-btn ${mapMode === 'subway' ? 'active' : ''}`} onClick={() => setMapMode('subway')}>Subway</button>
                </div>
            </div>
            <div className="map-container">
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
                    <rect x={isSubway ? -10 : -40} y={isSubway ? -30 : -20} width={vbWidth} height={vbHeight} fill="#030608" />
                    <rect x={isSubway ? -10 : -40} y={isSubway ? -10 : -20} width={vbWidth} height={vbHeight} fill="url(#grid)" />

                    {isSubway ? (
                        <>
                            <rect x="270" y="-15" width="370" height="470" rx="6" fill="rgba(0,255,136,0.015)" stroke="rgba(0,255,136,0.06)" strokeWidth="1" strokeDasharray="6 4" />
                            <text x="282" y="450" fontFamily="Orbitron, sans-serif" fontSize="11" fill="rgba(0,255,136,0.2)" letterSpacing="2">6-CBBM</text>
                            <rect x="670" y="-15" width="460" height="270" rx="6" fill="rgba(0,255,136,0.015)" stroke="rgba(0,255,136,0.06)" strokeWidth="1" strokeDasharray="6 4" />
                            <text x="682" y="250" fontFamily="Orbitron, sans-serif" fontSize="11" fill="rgba(0,255,136,0.2)" letterSpacing="2">2Q-8WA</text>
                        </>
                    ) : (
                        <>
                            <rect x="460" y="30" width="210" height="162" rx="4" fill="none" stroke="#0a3020" strokeWidth="1.5" strokeDasharray="4 4" />
                            <text x="470" y="44" fontFamily="Orbitron, sans-serif" fontSize="9" fill="#0d3828" letterSpacing="2">6-CBBM</text>
                            <rect x="748" y="0" width="360" height="132" rx="4" fill="none" stroke="#0a3020" strokeWidth="1.5" strokeDasharray="4 4" />
                            <text x="758" y="14" fontFamily="Orbitron, sans-serif" fontSize="9" fill="#0d3828" letterSpacing="2">2Q-8WA</text>
                        </>
                    )}

                    {isSubway ? (
                        <>
                            <text x="50" y="50" fontFamily="Share Tech Mono, monospace" fontSize="7" fill="#222233" letterSpacing="1" fontStyle="italic">Geminate</text>
                            <text x="100" y="8" fontFamily="Share Tech Mono, monospace" fontSize="7" fill="#222233" letterSpacing="1" fontStyle="italic">Vale of the Silent</text>
                            <text x="720" y="440" fontFamily="Share Tech Mono, monospace" fontSize="7" fill="#222233" letterSpacing="1" fontStyle="italic">Etherium Reach</text>
                            <text x="940" y="620" fontFamily="Share Tech Mono, monospace" fontSize="7" fill="#222233" letterSpacing="1" fontStyle="italic">Malpais</text>
                        </>
                    ) : (
                        <>
                            <text x="90" y="25" fontFamily="Share Tech Mono, monospace" fontSize="8" fill="#333344" letterSpacing="1" fontStyle="italic">Geminate</text>
                            <text x="245" y="-4" fontFamily="Share Tech Mono, monospace" fontSize="8" fill="#333344" letterSpacing="1" fontStyle="italic">Vale of the Silent</text>
                        </>
                    )}

                    {sortedConnections.map(([from, to, type], i) => {
                        const a = activeLayout[from], b = activeLayout[to]
                        if (!a || !b) return null
                        const s = getConnectionStyle(from, to, type)
                        return <line key={`${from}-${to}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={s.stroke} strokeWidth={s.width} strokeDasharray={s.dash} opacity={s.opacity} strokeLinecap={s.cap || "butt"} />
                    })}

                    {Object.entries(activeLayout).map(([name, pos]) => {
                        const isN = pos.constellation === "neighbor"
                        const isLawn = pos.lawn
                        const isGateway = isSubway && GATEWAY_SYSTEMS.includes(name)
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
                        } else if (isLawn) {
                            r = isGateway ? 12 : 10
                            nameSize = 13; nameOff = isGateway ? 22 : 18
                            admSize = 11; admOff = isGateway ? 28 : 24
                            nodeOpacity = 1; nameFill = "#e0fff0"; nodeStroke = isGateway ? 3 : 2.5; nodeFill = "#0a1a10"
                        } else if (pos.constellation === "S4S-SD") {
                            r = 4.5; nameSize = 8; nameOff = 10; admSize = 0; admOff = 0
                            nodeOpacity = 0.85; nameFill = color; nodeStroke = 1.2; nodeFill = "#060a0f"
                        } else {
                            r = 4; nameSize = 7.5; nameOff = 9; admSize = 0; admOff = 0
                            nodeOpacity = 0.7; nameFill = color; nodeStroke = 1; nodeFill = "#060a0f"
                        }

                        const critGrind = needsCriticalGrinding(name)
                        const cautGrind = needsCautionGrinding(name)
                        const strokeColor = critGrind ? "#ff3355" : cautGrind ? "#ffaa00" : color
                        const strokeW = critGrind ? (isSubway && isLawn ? 4 : 3) : cautGrind ? (isSubway && isLawn ? 3 : 2) : nodeStroke
                        const nodeFilter = critGrind ? "url(#glow-r)" : cautGrind ? "url(#glow-amber)" : (isSubway && isLawn ? "url(#glow-green)" : undefined)

                        const reffedR = isSubway ? (isLawn ? r + 8 : r + 6) : 16
                        const selR = isSubway ? (isLawn ? r + 4 : r + 3) : 11

                        return (
                            <g key={name}
                                onMouseEnter={(e) => handleHover(e, name)}
                                onMouseLeave={() => setTooltip(null)}
                                onClick={() => sysId && onSelectSystem(sysId)}
                                style={{ cursor: isN ? 'default' : 'pointer' }}
                            >
                                {isGateway && (
                                    <circle cx={pos.x} cy={pos.y} r={r + 5} fill="none" stroke="#ffaa00" strokeWidth="1.5" strokeDasharray="4 3" opacity={0.6} />
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
                                {npc && <circle cx={pos.x} cy={pos.y} r={isSubway && isLawn ? npc.r * 1.3 : npc.r} fill={`rgba(0,212,255,${npc.o})`} />}
                                {pvp > 0 && <circle cx={pos.x} cy={pos.y} r={isSubway && isLawn ? pvp * 1.3 : pvp} fill="rgba(255,51,85,0.3)" filter="url(#glow-r)" />}
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
                                        x={pos.x + (isSubway && isLawn ? 14 : 9)}
                                        y={pos.y - (isSubway && isLawn ? 12 : 8)}
                                        fontFamily="Orbitron, sans-serif"
                                        fontSize={isSubway && isLawn ? "14" : "11"}
                                        fill="#ff3355"
                                        fontWeight="bold"
                                        opacity={0.95}
                                    >!</text>
                                )}
                                <text x={pos.x} y={pos.y - nameOff}
                                    textAnchor="middle"
                                    fontFamily="Share Tech Mono, monospace"
                                    fontSize={nameSize}
                                    fill={nameFill}
                                    opacity={isSubway ? (isN ? 0.4 : isLawn ? 1 : 0.7) : (isN ? 0.6 : 0.9)}
                                    letterSpacing={isSubway && isLawn ? "1" : "0.5"}
                                    fontWeight={isSubway && isLawn ? "bold" : "normal"}
                                    stroke={isSubway && isLawn ? "#060a0f" : "none"}
                                    strokeWidth={isSubway && isLawn ? 3 : 0}
                                    paintOrder={isSubway && isLawn ? "stroke" : "normal"}
                                >{name}</text>
                                {!isN && adm > 0 && admSize > 0 && (() => {
                                    const admText = adm.toFixed(1)
                                    const admCol = getAdmColor(adm)
                                    const admX = pos.x
                                    const admY = pos.y + admOff + (isSubway && isLawn ? 2 : 0)
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
                                {isLawn && (() => {
                                    const upSummary = getUpgradeSummary(name, config)
                                    const cats = []
                                    if (upSummary.military > 0) cats.push(UPGRADE_CATEGORY_COLORS.military)
                                    if (upSummary.industry > 0) cats.push(UPGRADE_CATEGORY_COLORS.industry)
                                    if (upSummary.strategic > 0) cats.push(UPGRADE_CATEGORY_COLORS.strategic)
                                    if (cats.length === 0) return null
                                    const dotR = isSubway ? 1.5 : 1.2
                                    const dotGap = isSubway ? 4 : 3.5
                                    const baseX = pos.x - (cats.length - 1) * dotGap / 2
                                    const baseY = pos.y + (isSubway ? (adm > 0 ? 19 : 12) : (adm > 0 ? 17 : 12))
                                    return cats.map((c, ci) => (
                                        <circle key={ci} cx={baseX + ci * dotGap} cy={baseY} r={dotR} fill={c} opacity={0.8} />
                                    ))
                                })()}
                                {isGateway && name === "UDVW-O" && (
                                    <text x={pos.x - 25} y={pos.y} textAnchor="end" fontFamily="Orbitron, sans-serif" fontSize="9" fill="#ffaa00" opacity={0.85} letterSpacing="1">{'\u2192'} VALE</text>
                                )}
                                {isGateway && name === "N-JK02" && (
                                    <text x={pos.x - 20} y={pos.y + 25} textAnchor="end" fontFamily="Orbitron, sans-serif" fontSize="9" fill="#ffaa00" opacity={0.85} letterSpacing="1">{'\u2192'} TKE</text>
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

            {tooltip && (
                <div className="map-tooltip visible" style={{ left: tooltip.x, top: tooltip.y }}>
                    <div className="map-tooltip-name" style={{ color: tooltip.isNeighbor ? '#ffaa00' : '#00ff88' }}>{tooltip.name}</div>
                    <div className="map-tooltip-row"><span className="map-tooltip-label">Holder</span><span>{tooltip.holder}</span></div>
                    {tooltip.corp && <div className="map-tooltip-row"><span className="map-tooltip-label">Corp</span><span>{tooltip.corp}</span></div>}
                    <div className="map-tooltip-row">
                        <span className="map-tooltip-label">ADM</span>
                        <span style={{ color: tooltip.adm > 0 ? getAdmColor(tooltip.adm) : '#3a5060' }}>
                            {tooltip.adm > 0 ? tooltip.adm.toFixed(1) : '—'}
                        </span>
                    </div>
                    {tooltip.isLawn && tooltip.adm > 0 && tooltip.adm < 4 && (
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
                    {tooltip.isLawn && (() => {
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
                </div>
            )}

            <div className="map-legend">
                <div className="map-legend-item">
                    <div style={{ width: 8, height: 8, background: 'transparent', border: '2.5px dashed #ff3355', borderRadius: '50%' }} />
                    <span>Nodes Active</span>
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
                <div className="map-legend-item"><div className="map-legend-dot" style={{ background: '#00ff88' }} /><span>LAWN Sov</span></div>
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
                {isSubway ? (
                    <>
                        <div className="map-legend-item">
                            <div style={{ width: 10, height: 10, background: 'transparent', border: '2px solid #ffaa00', borderRadius: '50%', boxShadow: '0 0 0 2px transparent, 0 0 0 3px #ffaa0066' }} />
                            <span>Gateway (exit)</span>
                        </div>
                        <div className="map-legend-item"><div style={{ width: 16, height: 0, borderTop: '3px solid #00ff88' }} /><span>LAWN gate</span></div>
                        <div className="map-legend-item"><div style={{ width: 16, height: 0, borderTop: '2.5px dashed #00d4ff' }} /><span>LAWN bridge</span></div>
                        <div className="map-legend-item"><div style={{ width: 16, height: 0, borderTop: '2.5px dashed #ffaa00' }} /><span>LAWN exit</span></div>
                        <div className="map-legend-item"><div style={{ width: 16, height: 0, borderTop: '1px solid #1a2a35', opacity: 0.6 }} /><span>TKE gate</span></div>
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

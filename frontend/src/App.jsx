import React, { useState, useEffect, useCallback, useRef } from 'react'
import Clock from './components/common/Clock'
import { getCampaignPhase } from './utils/campaignHelpers'
import CornerBrackets from './components/common/CornerBrackets'
import SummaryCard from './components/common/SummaryCard'
import ConstellationMap from './components/ConstellationMap'
import SystemTable from './components/SystemTable'
import KillFeed from './components/KillFeed'
import AdmTrends from './components/AdmTrends'
import GrindingPlan from './components/GrindingPlan'
import UpgradesOverview from './components/UpgradesOverview'
import CampaignAlerts from './components/CampaignAlerts'
import TimerBoard from './components/TimerBoard'
import PlanetaryIntel from './components/PlanetaryIntel'
import NeighborIntel from './components/NeighborIntel'
import ActivityHeatmap from './components/ActivityHeatmap'
import MobileNav from './components/MobileNav'
import DscanParser from './components/DscanParser'
import LocalScanner from './components/LocalScanner'
import JumpBridgeManager from './components/JumpBridgeManager'
import NotificationBell from './components/NotificationBell'
import { useNotifications } from './hooks/useNotifications'

export default function App() {
    const [config, setConfig] = useState(null)
    const [sovereignty, setSovereignty] = useState({})
    const [activity, setActivity] = useState({})
    const [campaigns, setCampaigns] = useState([])
    const [killFeed, setKillFeed] = useState([])
    const [admHistory, setAdmHistory] = useState({})
    const [annotations, setAnnotations] = useState({})
    const [jumpBridges, setJumpBridges] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [refreshing, setRefreshing] = useState(false)
    const [lastUpdate, setLastUpdate] = useState(null)
    const [activeConst, setActiveConst] = useState("lawn")
    const [selectedSystem, setSelectedSystem] = useState(null)
    const [mapMode, setMapMode] = useState("subway")
    const [isMobile, setIsMobile] = useState(() => window.innerWidth < 640)
    const [mobileTab, setMobileTab] = useState(0)
    const timer = useRef(null)
    const { settings: notifSettings, saveSettings: saveNotifSettings, permStatus, requestPermission, checkAndNotify } = useNotifications()

    const fetchData = useCallback(async (init = false) => {
        try {
            if (!init) setRefreshing(true)
            const checkedFetch = (url) => fetch(url).then(r => {
                if (!r.ok) throw new Error(`${url}: ${r.status}`)
                return r.json()
            })
            const [cfg, sov, act, camp] = await Promise.all([
                checkedFetch("/api/config"),
                checkedFetch("/api/sovereignty"),
                checkedFetch("/api/activity"),
                checkedFetch("/api/campaigns"),
            ])
            setConfig(cfg); setSovereignty(sov); setActivity(act); setCampaigns(camp)
            checkedFetch("/api/zkill/feed").then(setKillFeed).catch(e => console.warn("Kill feed unavailable:", e.message))
            checkedFetch("/api/history/adm").then(setAdmHistory).catch(e => console.warn("ADM history unavailable:", e.message))
            checkedFetch("/api/annotations").then(setAnnotations).catch(e => console.warn("Annotations unavailable:", e.message))
            checkedFetch("/api/jumpbridges").then(setJumpBridges).catch(e => console.warn("Jump bridges unavailable:", e.message))
            setLastUpdate(new Date()); setError(null)

            // Build LAWN sys lookup from fresh config and check for alert-worthy changes
            if (cfg && cfg.constellations) {
                const lawnIds = new Set()
                const names = {}
                Object.values(cfg.constellations).forEach(c => {
                    Object.values(c.systems).forEach(s => {
                        names[s.system_id] = s.name
                        if (c.is_lawn) lawnIds.add(String(s.system_id))
                    })
                })
                checkAndNotify(camp, sov, act, lawnIds, names)
            }
        } catch (err) { if (init) setError(err.message) }
        finally { setLoading(false); setRefreshing(false) }
    }, [checkAndNotify])

    useEffect(() => {
        fetchData(true)
        timer.current = setInterval(() => fetchData(false), 5 * 60 * 1000)
        return () => clearInterval(timer.current)
    }, [fetchData])

    useEffect(() => {
        const handler = () => setIsMobile(window.innerWidth < 640)
        window.addEventListener('resize', handler)
        return () => window.removeEventListener('resize', handler)
    }, [])

    if (loading) return (
        <div className="loading">
            <div className="loading-spinner" />
            <div className="loading-text">CONNECTING TO ESI...</div>
        </div>
    )

    if (error || !config || !config.constellations) return (
        <div className="error-panel">
            <h3>{error ? "CONNECTION FAILED" : "NO DATA"}</h3>
            <p>{error || "Check config.py"}</p>
        </div>
    )

    const consts = config.constellations
    const cids = Object.keys(consts)
    const lawnCids = cids.filter(c => consts[c].is_lawn)
    const lawnSysIdSet = new Set()
    lawnCids.forEach(c => Object.values(consts[c].systems).forEach(s => lawnSysIdSet.add(String(s.system_id))))

    let visible = []
    if (activeConst === "lawn") {
        lawnCids.forEach(c => Object.values(consts[c].systems).forEach(s => visible.push(s)))
    } else if (activeConst === "all") {
        cids.forEach(c => Object.values(consts[c].systems).forEach(s => visible.push(s)))
    } else {
        const c = consts[activeConst]; if (c) visible = Object.values(c.systems)
    }

    const totPVP = visible.reduce((s, v) => { const a = activity[v.system_id] || {}; return s + (a.ship_kills || 0) + (a.pod_kills || 0) }, 0)
    const totNPC = visible.reduce((s, v) => s + ((activity[v.system_id] || {}).npc_kills || 0), 0)
    const totJ = visible.reduce((s, v) => s + ((activity[v.system_id] || {}).jumps || 0), 0)
    const hostile = visible.filter(s => { const sv = sovereignty[s.system_id]; return sv && sv.alliance_name && !sv.is_friendly }).length
    const criticalSystems = visible.filter(s => {
        const sov = sovereignty[s.system_id]
        return lawnSysIdSet.has(String(s.system_id)) && sov && sov.adm > 0 && sov.adm < 2
    }).length

    const lawnSystems = Object.values(consts).filter(c => c.is_lawn).flatMap(c => Object.values(c.systems))
    const lawnPVP = lawnSystems.reduce((s, v) => { const a = activity[v.system_id] || {}; return s + (a.ship_kills || 0) + (a.pod_kills || 0) }, 0)
    const lawnNPC = lawnSystems.reduce((s, v) => s + ((activity[v.system_id] || {}).npc_kills || 0), 0)
    const lawnJumps = lawnSystems.reduce((s, v) => s + ((activity[v.system_id] || {}).jumps || 0), 0)

    // Panels grouped for conditional rendering
    const summaryPanels = (
        <>
            <div className="panel panel-wide">
                <CornerBrackets />
                <div className="panel-header">
                    <span className="panel-title">Situation Overview</span>
                    <span className="panel-badge">Last hour</span>
                </div>
                <div className="summary-row">
                    <SummaryCard label="Systems" value={visible.length} />
                    <SummaryCard label="PVP Kills" value={totPVP} type={totPVP > 10 ? "danger" : totPVP > 0 ? "warn" : "safe"} />
                    <SummaryCard label="NPC Kills" value={totNPC.toLocaleString()} />
                    <SummaryCard label="Jumps" value={totJ.toLocaleString()} type={totJ > 200 ? "warn" : "default"} />
                    <SummaryCard label="Critical ADM" value={criticalSystems} type={criticalSystems > 3 ? "danger" : criticalSystems > 0 ? "warn" : "safe"} />
                    <SummaryCard label="Hostile Sov" value={hostile} type={hostile > 0 ? "danger" : "safe"} />
                    {(() => {
                        const activeCount = campaigns.filter(c => getCampaignPhase(c).phase === 'nodes').length
                        const reffedCount = campaigns.filter(c => getCampaignPhase(c).phase === 'reinforced').length
                        let type = "safe"
                        if (activeCount > 0) type = "danger"
                        else if (reffedCount > 0) type = "warn"
                        const valueStr = activeCount > 0 ? `${activeCount} (+${reffedCount})` : reffedCount
                        return <SummaryCard label="Campaigns" value={valueStr} type={type} />
                    })()}
                </div>
            </div>

            <div className="panel panel-wide">
                <CornerBrackets />
                <div className="panel-header">
                    <span className="panel-title">LAWN Alliance Activity</span>
                    <span className="panel-badge">15 systems · Last hour</span>
                </div>
                <div className="summary-row">
                    <SummaryCard label="Alliance PVP" value={lawnPVP} type={lawnPVP > 15 ? "danger" : lawnPVP > 5 ? "warn" : "safe"} />
                    <SummaryCard label="Alliance NPC" value={lawnNPC.toLocaleString()} />
                    <SummaryCard label="Alliance Jumps" value={lawnJumps.toLocaleString()} type={lawnJumps > 300 ? "warn" : "default"} />
                    <SummaryCard label="Avg Activity" value={lawnSystems.length > 0 ? Math.round((lawnPVP + lawnNPC / 10 + lawnJumps / 20) / lawnSystems.length) : 0} />
                </div>
            </div>
        </>
    )

    const mapPanel = (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">Constellation Map</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div className="map-mode-toggle">
                        <button className={`map-mode-btn ${mapMode === 'traditional' ? 'active' : ''}`} onClick={() => setMapMode('traditional')}>Traditional</button>
                        <button className={`map-mode-btn ${mapMode === 'subway' ? 'active' : ''}`} onClick={() => setMapMode('subway')}>Subway</button>
                    </div>
                    <span className="panel-badge">69 systems + 18 neighbors</span>
                </div>
            </div>
            <ConstellationMap
                config={config}
                sovereignty={sovereignty}
                activity={activity}
                campaigns={campaigns}
                selectedSystem={selectedSystem}
                onSelectSystem={setSelectedSystem}
                mapMode={mapMode}
                annotations={annotations}
                onAnnotationChange={() => fetch("/api/annotations").then(r => r.json()).then(setAnnotations).catch(() => {})}
                jumpBridges={jumpBridges}
            />
        </div>
    )

    const systemStatusPanel = (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">System Status</span>
                <span className="panel-badge">{visible.length} systems</span>
            </div>
            <div className="const-tabs">
                <button
                    className={`const-tab ${activeConst === 'lawn' ? 'active' : ''}`}
                    onClick={() => setActiveConst('lawn')}
                    style={activeConst === 'lawn' ? { borderColor: 'var(--green-dim)', color: 'var(--green)' } : {}}
                >LAWN</button>
                <button className={`const-tab ${activeConst === 'all' ? 'active' : ''}`} onClick={() => setActiveConst('all')}>ALL TKE</button>
                {cids.map(c => (
                    <button
                        key={c}
                        className={`const-tab ${activeConst === c ? 'active' : ''}`}
                        onClick={() => setActiveConst(c)}
                        style={consts[c].is_lawn ? { borderLeftColor: 'var(--green-dim)', borderLeftWidth: 2 } : {}}
                    >{consts[c].name}</button>
                ))}
            </div>
            <SystemTable
                systems={visible}
                sovereignty={sovereignty}
                activity={activity}
                selectedSystem={selectedSystem}
                onSelectSystem={setSelectedSystem}
                lawnSystemIds={lawnSysIdSet}
                config={config}
                annotations={annotations}
            />
        </div>
    )

    return (
        <div>
            <div className="header">
                <div className="header-left">
                    <img src="/static/logo.png" alt="" style={{ height: 40, marginRight: 12, display: 'block' }} onError={(e) => { e.target.style.display = 'none' }} />
                    <div>
                        <div className="logo-text">GET OFF MY LAWN</div>
                        <div className="logo-sub" style={{ marginTop: '4px' }}>KALEVALA EXPANSE — INTEL DASHBOARD</div>
                    </div>
                </div>
                <div className="status-bar">
                    <Clock />
                    {!isMobile && <div style={{ width: 1, height: 16, background: 'var(--border-dim)' }}></div>}
                    <span><span className="status-dot" />ONLINE</span>
                    {!isMobile && lastUpdate && <span>ESI DATA: {lastUpdate.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>}
                    <button className={`refresh-btn ${refreshing ? 'refreshing' : ''}`} onClick={() => fetchData(false)} disabled={refreshing}>
                        {refreshing ? (isMobile ? "..." : "REFRESHING...") : "↻ REFRESH"}
                    </button>
                    <NotificationBell
                        settings={notifSettings}
                        saveSettings={saveNotifSettings}
                        permStatus={permStatus}
                        requestPermission={requestPermission}
                    />
                </div>
            </div>
            <div className="dashboard">
                {/* Tab 0: Map — summary cards + map */}
                {(!isMobile || mobileTab === 0) && summaryPanels}

                {/* Tab 1: Systems — grinding plan */}
                {(!isMobile || mobileTab === 1) && (
                    <GrindingPlan config={config} sovereignty={sovereignty} activity={activity} admHistory={admHistory} />
                )}

                {/* Tab 0: Map — constellation map */}
                {(!isMobile || mobileTab === 0) && mapPanel}

                {/* Tab 1: Systems — system table */}
                {(!isMobile || mobileTab === 1) && systemStatusPanel}

                {/* Tab 2: Kills — kill feed */}
                {(!isMobile || mobileTab === 2) && <KillFeed kills={killFeed} />}

                {/* Tab 3+4: Campaign alerts + Timers — side by side on tablet+ */}
                {(!isMobile || mobileTab === 3 || mobileTab === 4) && (
                    <div className="panel-pair">
                        {(!isMobile || mobileTab === 3) && <CampaignAlerts campaigns={campaigns} config={config} />}
                        {(!isMobile || mobileTab === 4) && <TimerBoard />}
                    </div>
                )}

                {/* Tab 5: Industry — PI */}
                {(!isMobile || mobileTab === 5) && <PlanetaryIntel />}

                {/* Tab 2: Kills — activity heatmap */}
                {(!isMobile || mobileTab === 2) && <ActivityHeatmap config={config} sovereignty={sovereignty} lastUpdate={lastUpdate} />}

                {/* Tab 3: Intel — JB manager + neighbor intel + dscan + local scanner */}
                {(!isMobile || mobileTab === 3) && (
                    <JumpBridgeManager
                        jumpBridges={jumpBridges}
                        onJbChange={() => fetch("/api/jumpbridges").then(r => r.json()).then(setJumpBridges).catch(() => {})}
                    />
                )}
                {(!isMobile || mobileTab === 3) && <NeighborIntel lastUpdate={lastUpdate} />}
                {(!isMobile || mobileTab === 3) && <DscanParser />}
                {(!isMobile || mobileTab === 3) && <LocalScanner />}

                {/* Tab 1: Systems — adm trends + upgrades side by side on tablet+ */}
                {(!isMobile || mobileTab === 1) && (
                    <div className="panel-pair">
                        <AdmTrends admHistory={admHistory} config={config} sovereignty={sovereignty} />
                        <UpgradesOverview config={config} />
                    </div>
                )}
            </div>
            {isMobile && <MobileNav activeTab={mobileTab} onTabChange={setMobileTab} />}
        </div>
    )
}

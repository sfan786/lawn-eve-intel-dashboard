import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { Link } from 'react-router-dom'
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
import RegionalIntel from './components/RegionalIntel'
import ActivityHeatmap from './components/ActivityHeatmap'
import MobileNav, { SOV_TABS, ROOTLESS_TABS } from './components/MobileNav'
import DscanParser from './components/DscanParser'
import LocalScanner from './components/LocalScanner'
import FleetCompAnalyzer from './components/FleetCompAnalyzer'
import IntelChannelParser from './components/IntelChannelParser'
import ActiveHostileTracker from './components/ActiveHostileTracker'
import JumpBridgeManager from './components/JumpBridgeManager'
import NotificationBell from './components/NotificationBell'
import EveLoginButton from './components/common/EveLoginButton'
import { useAuth } from './utils/useAuth'
import { useNotifications } from './hooks/useNotifications'
import { ANALYTICS_SEEN_KEY } from './utils/analyticsAuth'

const checkedFetch = (url) => fetch(url).then(r => {
    if (!r.ok) throw new Error(`${url}: ${r.status}`)
    return r.json()
})

const isPrimaryConst = (c) => c.is_primary ?? c.is_lawn

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
    const [activeConst, setActiveConst] = useState("primary")
    const [selectedSystem, setSelectedSystem] = useState(null)
    const [mapMode, setMapMode] = useState("subway")
    const [isMobile, setIsMobile] = useState(() => window.innerWidth < 640)
    // Login lives in the header, not only inside the panels that happen to need
    // write access. Buried in the Timerboard it was undiscoverable, so features
    // gated on being logged in (SHARE, AI summaries) looked simply absent.
    const auth = useAuth()
    // The /analytics page is operator-only and unadvertised: the link appears
    // only on a browser that has already unlocked it, so it isn't a signpost
    // for the rest of the alliance. The page enforces access server-side.
    const [showUsageLink] = useState(() => localStorage.getItem(ANALYTICS_SEEN_KEY) === '1')
    const [mobileTab, setMobileTab] = useState(0)
    const [intelAlerts, setIntelAlerts] = useState([])
    // Which region the kill feed / hostile tracker are pointed at. Only
    // meaningful when the deployment watches more than one (see WATCHED_REGIONS);
    // null means "whatever the backend defaults to".
    const [regionId, setRegionId] = useState(null)
    const timer = useRef(null)
    // Mirrors `config` so fetchData can read it without taking it as a dependency
    // (which would rebuild the poll timer every time config lands).
    const configRef = useRef(null)
    // Same reason: the poll reads the selected region without depending on it.
    const regionIdRef = useRef(null)
    const { settings: notifSettings, saveSettings: saveNotifSettings, permStatus, requestPermission, checkAndNotify } = useNotifications()

    const fetchData = useCallback(async (init = false) => {
        try {
            if (!init) setRefreshing(true)
            // /api/config is static per deployment — map layout, connections,
            // system lists, upgrade catalog. Fetch it once rather than re-sending
            // the whole payload every 5 minutes. Keyed on "do we have it yet"
            // rather than on `init` so a failed first load still self-heals on a
            // later poll instead of leaving the app stuck on "NO DATA".
            const needConfig = init || !configRef.current
            const [cfgFresh, sov, act, camp] = await Promise.all([
                needConfig ? checkedFetch("/api/config") : Promise.resolve(null),
                checkedFetch("/api/sovereignty"),
                checkedFetch("/api/activity"),
                checkedFetch("/api/campaigns"),
            ])
            const cfg = cfgFresh || configRef.current
            if (cfgFresh) {
                configRef.current = cfgFresh; setConfig(cfgFresh)
                // Default the feed to the deployment's own region on first load.
                if (regionIdRef.current == null && cfgFresh.region?.id) {
                    regionIdRef.current = cfgFresh.region.id
                    setRegionId(cfgFresh.region.id)
                }
            }
            setSovereignty(sov); setActivity(act); setCampaigns(camp)
            const regionQs = regionIdRef.current ? `?region_id=${regionIdRef.current}` : ''
            checkedFetch(`/api/zkill/feed${regionQs}`).then(setKillFeed).catch(e => console.warn("Kill feed unavailable:", e.message))
            checkedFetch("/api/history/adm").then(setAdmHistory).catch(e => console.warn("ADM history unavailable:", e.message))
            checkedFetch("/api/annotations").then(setAnnotations).catch(e => console.warn("Annotations unavailable:", e.message))
            checkedFetch("/api/jumpbridges").then(setJumpBridges).catch(e => console.warn("Jump bridges unavailable:", e.message))
            setLastUpdate(new Date()); setError(null)

            // Build primary sys lookup from fresh config and check for alert-worthy changes
            if (cfg && cfg.constellations) {
                const primaryIds = new Set()
                const names = {}
                Object.values(cfg.constellations).forEach(c => {
                    Object.values(c.systems).forEach(s => {
                        names[s.system_id] = s.name
                        if (isPrimaryConst(c)) primaryIds.add(String(s.system_id))
                    })
                })
                const allianceShort = cfg?.alliance?.short_name || cfg?.alliance?.ticker || 'PRIMARY'
                checkAndNotify(camp, sov, act, primaryIds, names, allianceShort, cfg?.holds_sov !== false)
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

    // Switching regions refetches just the kill feed rather than the whole
    // dashboard — sov/activity/campaigns are scoped to the deployment, not to
    // whichever region the feed happens to be pointed at.
    const changeRegion = useCallback((id) => {
        regionIdRef.current = id
        setRegionId(id)
        checkedFetch(`/api/zkill/feed?region_id=${id}`)
            .then(setKillFeed)
            .catch(e => console.warn("Kill feed unavailable:", e.message))
    }, [])

    const primarySysIdSet = useMemo(() => {
        if (!config?.constellations) return new Set()
        const s = new Set()
        Object.values(config.constellations).filter(isPrimaryConst).forEach(c =>
            Object.values(c.systems).forEach(sys => s.add(String(sys.system_id)))
        )
        return s
    }, [config])

    // Host alliance name, for labelling whose sov and iHubs these actually are.
    // Must stay above the early returns below — hooks run in the same order on
    // every render or React throws "Rendered fewer hooks than expected".
    const hostName = useMemo(() => {
        if (!config?.host_alliance_ids?.length) return ""
        const hit = Object.values(sovereignty).find(s => s?.is_host && s.alliance_name)
        return hit?.alliance_name || ""
    }, [config, sovereignty])

    if (loading) return (
        <div className="loading">
            <div className="loading-spinner" />
            <div className="loading-text">CONNECTING TO ESI...</div>
        </div>
    )

    if (error || !config || !config.constellations) return (
        <div className="error-panel">
            <h3>{error ? "CONNECTION FAILED" : "NO DATA"}</h3>
            <p>{error || "Check the active deployment in deployments/"}</p>
        </div>
    )

    const alliance = config.alliance || {}
    const allianceShort = alliance.short_name || alliance.ticker || "PRIMARY"
    const allianceDisplay = alliance.display_name || alliance.name || allianceShort
    const regionName = config.region?.name || ""
    // Two independent questions, because a guest answers them differently.
    //   holdsSov — do we own this space? Gates the ADM trends and grinding
    //              planner, which are about raising OUR index.
    //   hasAo    — do we have a home at all? Gates the map, system table,
    //              campaigns, activity and neighbour intel.
    // A guest is holdsSov=false, hasAo=true: it lives somewhere, defends it,
    // and watches its neighbours, but the iHubs belong to the host.
    // Both default to true so an older backend behaves exactly as before.
    const holdsSov = config.holds_sov !== false
    const hasAo = config.has_ao !== false
    const tabs = hasAo ? SOV_TABS : ROOTLESS_TABS
    // Tab 0 (Map) doesn't exist rootless; fall back to Intel rather than
    // opening on a blank screen.
    const activeTab = tabs.some(t => t.id === mobileTab) ? mobileTab : tabs[0].id
    const showTab = (id) => !isMobile || activeTab === id
    const consts = config.constellations
    const cids = Object.keys(consts)
    const primaryCids = cids.filter(c => isPrimaryConst(consts[c]))
    const totalRegionSystems = Object.values(consts).reduce((s, c) => s + Object.keys(c.systems || {}).length, 0)
    const totalNeighborSystems = Object.keys(config.neighbor_systems || {}).length

    let visible = []
    if (activeConst === "primary") {
        primaryCids.forEach(c => Object.values(consts[c].systems).forEach(s => visible.push(s)))
    } else if (activeConst === "all") {
        cids.forEach(c => Object.values(consts[c].systems).forEach(s => visible.push(s)))
    } else {
        const c = consts[activeConst]; if (c) visible = Object.values(c.systems)
    }

    const totPVP = visible.reduce((s, v) => { const a = activity[v.system_id] || {}; return s + (a.ship_kills || 0) + (a.pod_kills || 0) }, 0)
    const totNPC = visible.reduce((s, v) => s + ((activity[v.system_id] || {}).npc_kills || 0), 0)
    const totJ = visible.reduce((s, v) => s + ((activity[v.system_id] || {}).jumps || 0), 0)
    const hostile = visible.filter(s => { const sv = sovereignty[s.system_id]; return sv && sv.alliance_name && !sv.is_friendly }).length
    // Guarded on holdsSov: a host counts as friendly, so without this a guest
    // would read the host's low-ADM systems as our own critical grinding debt.
    const criticalSystems = !holdsSov ? 0 : visible.filter(s => {
        const sov = sovereignty[s.system_id]
        return primarySysIdSet.has(String(s.system_id)) && sov && sov.is_friendly && sov.adm > 0 && sov.adm < 2
    }).length
    const hostSystems = visible.filter(s => sovereignty[s.system_id]?.is_host).length

    const primarySystems = Object.values(consts).filter(isPrimaryConst).flatMap(c => Object.values(c.systems))
    const { primaryPVP, primaryNPC, primaryJumps } = primarySystems.reduce((acc, v) => {
        const a = activity[v.system_id] || {}
        acc.primaryPVP += (a.ship_kills || 0) + (a.pod_kills || 0)
        acc.primaryNPC += (a.npc_kills || 0)
        acc.primaryJumps += (a.jumps || 0)
        return acc
    }, { primaryPVP: 0, primaryNPC: 0, primaryJumps: 0 })

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
                    {holdsSov
                        ? <SummaryCard label="Critical ADM" value={criticalSystems} type={criticalSystems > 3 ? "danger" : criticalSystems > 0 ? "warn" : "safe"} />
                        : hostName && <SummaryCard label="Host Sov" value={hostSystems} type="safe" />}
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
                    {/* "Alliance Activity" over space we don't own would claim it
                        as ours; under a guest posture it's our area of operations. */}
                    <span className="panel-title">{holdsSov ? `${allianceShort} Alliance Activity` : `${allianceShort} AO Activity`}</span>
                    <span className="panel-badge">{primarySystems.length} systems · Last hour</span>
                </div>
                <div className="summary-row">
                    <SummaryCard label="Alliance PVP" value={primaryPVP} type={primaryPVP > 15 ? "danger" : primaryPVP > 5 ? "warn" : "safe"} />
                    <SummaryCard label="Alliance NPC" value={primaryNPC.toLocaleString()} />
                    <SummaryCard label="Alliance Jumps" value={primaryJumps.toLocaleString()} type={primaryJumps > 300 ? "warn" : "default"} />
                    <SummaryCard label="Avg Activity" value={primarySystems.length > 0 ? Math.round((primaryPVP + primaryNPC / 10 + primaryJumps / 20) / primarySystems.length) : 0} />
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
                    <span className="panel-badge">{totalRegionSystems} systems + {totalNeighborSystems} neighbors</span>
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
                onAnnotationChange={() => checkedFetch("/api/annotations").then(setAnnotations).catch(() => {})}
                jumpBridges={jumpBridges}
                intelAlerts={intelAlerts}
                holdsSov={holdsSov}
                hostName={hostName}
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
                    className={`const-tab ${activeConst === 'primary' ? 'active' : ''}`}
                    onClick={() => setActiveConst('primary')}
                    style={activeConst === 'primary' ? { borderColor: 'var(--green-dim)', color: 'var(--green)' } : {}}
                >{allianceShort}</button>
                <button className={`const-tab ${activeConst === 'all' ? 'active' : ''}`} onClick={() => setActiveConst('all')}>ALL {regionName ? regionName.toUpperCase() : 'REGION'}</button>
                {cids.map(c => (
                    <button
                        key={c}
                        className={`const-tab ${activeConst === c ? 'active' : ''}`}
                        onClick={() => setActiveConst(c)}
                        style={isPrimaryConst(consts[c]) ? { borderLeftColor: 'var(--green-dim)', borderLeftWidth: 2 } : {}}
                    >{consts[c].name}</button>
                ))}
            </div>
            <SystemTable
                systems={visible}
                sovereignty={sovereignty}
                activity={activity}
                selectedSystem={selectedSystem}
                onSelectSystem={setSelectedSystem}
                lawnSystemIds={primarySysIdSet}
                config={config}
                annotations={annotations}
                holdsSov={holdsSov}
            />
        </div>
    )

    return (
        <div>
            <div className="header">
                <div className="header-left">
                    <img src="/static/logo.png" alt="" style={{ height: 40, marginRight: 12, display: 'block' }} onError={(e) => { e.target.style.display = 'none' }} />
                    <div>
                        <div className="logo-text">{allianceDisplay}</div>
                        <div className="logo-sub" style={{ marginTop: '4px' }}>{(config.posture_label || regionName).toUpperCase()} — INTEL DASHBOARD</div>
                    </div>
                </div>
                <div className="status-bar">
                    <Link to="/entosis" style={{ fontFamily: 'Orbitron', fontSize: 10, color: 'var(--cyan)', textDecoration: 'none', letterSpacing: 1, border: '1px solid var(--cyan-dim)', padding: '3px 8px', whiteSpace: 'nowrap' }}>
                        ENTOSIS OP
                    </Link>
                    {!!config?.wars?.length && (
                        <Link to="/war" title={config.wars[0].name} style={{ fontFamily: 'Orbitron', fontSize: 10, color: 'var(--red)', textDecoration: 'none', letterSpacing: 1, border: '1px solid var(--red-dim)', padding: '3px 8px', whiteSpace: 'nowrap' }}>
                            WAR
                        </Link>
                    )}
                    {!isMobile && showUsageLink && (
                        <Link to="/analytics" title="Dashboard usage stats (operator only)" style={{ fontFamily: 'Orbitron', fontSize: 10, color: 'var(--text-muted)', textDecoration: 'none', letterSpacing: 1, border: '1px solid var(--border-dim)', padding: '3px 8px', whiteSpace: 'nowrap' }}>
                            USAGE
                        </Link>
                    )}
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
                        holdsSov={holdsSov}
                        hasAo={hasAo}
                    />
                    <EveLoginButton auth={auth} />
                </div>
            </div>
            {hasAo ? (
                <div className="dashboard">
                    {/* Tab 0: Map — summary cards + map */}
                    {showTab(0) && summaryPanels}

                    {/* Tab 1: Systems — grinding plan. Sov-holders only: it ranks
                        where to rat to raise our own index, which we cannot do in
                        a host's space. */}
                    {showTab(1) && holdsSov && (
                        <GrindingPlan config={config} sovereignty={sovereignty} activity={activity} admHistory={admHistory} />
                    )}

                    {/* Tab 0: Map — constellation map */}
                    {showTab(0) && mapPanel}

                    {/* Tab 1: Systems — system table */}
                    {showTab(1) && systemStatusPanel}

                    {/* Tab 2: Kills — kill feed */}
                    {showTab(2) && <KillFeed kills={killFeed} config={config} regionId={regionId} onRegionChange={changeRegion} />}

                    {/* Tab 3+4: Campaign alerts + Timers — side by side on tablet+ */}
                    {(!isMobile || activeTab === 3 || activeTab === 4) && (
                        <div className="panel-pair">
                            {showTab(3) && <CampaignAlerts campaigns={campaigns} config={config} />}
                            {showTab(4) && <TimerBoard />}
                        </div>
                    )}

                    {/* Tab 5: Industry — PI */}
                    {showTab(5) && <PlanetaryIntel config={config} />}

                    {/* Tab 2: Kills — activity heatmap */}
                    {showTab(2) && <ActivityHeatmap config={config} sovereignty={sovereignty} lastUpdate={lastUpdate} />}

                    {/* Tab 3: Intel — channel parser + hostile tracker + JB + neighbor intel + dscan + local scanner */}
                    {showTab(3) && <IntelChannelParser config={config} onBoardChange={setIntelAlerts} />}
                    {showTab(3) && <ActiveHostileTracker lastUpdate={lastUpdate} regionId={regionId} />}
                    {showTab(3) && (
                        <JumpBridgeManager
                            jumpBridges={jumpBridges}
                            onJbChange={() => checkedFetch("/api/jumpbridges").then(setJumpBridges).catch(() => {})}
                        />
                    )}
                    {showTab(3) && <RegionalIntel lastUpdate={lastUpdate} />}
                    {showTab(3) && <NeighborIntel lastUpdate={lastUpdate} />}
                    {showTab(3) && <DscanParser />}
                    {showTab(3) && <LocalScanner />}
                    {showTab(3) && <FleetCompAnalyzer />}

                    {/* Tab 1: Systems — adm trends + upgrades side by side on tablet+.
                        ADM trends are ours-only; upgrades stay under a guest posture
                        because what's installed decides what anomalies spawn in the
                        space we're living in, whoever owns the iHub. */}
                    {showTab(1) && (holdsSov ? (
                        <div className="panel-pair">
                            <AdmTrends admHistory={admHistory} config={config} sovereignty={sovereignty} />
                            <UpgradesOverview config={config} />
                        </div>
                    ) : (
                        <UpgradesOverview config={config} hostName={hostName} />
                    ))}
                </div>
            ) : (
                /* Rootless: no sov, no home region. Everything derived from owning
                   the primary constellations is gone; what's left is the paste-in
                   intel tooling, which needs only standings and works anywhere. */
                <div className="dashboard">
                    {/* Tab 3: Intel — the toolkit leads, it's the reason to open the app */}
                    {showTab(3) && <DscanParser />}
                    {showTab(3) && <LocalScanner />}
                    {showTab(3) && <FleetCompAnalyzer />}

                    {/* Tab 2: Kills — feed over whichever watched region is selected */}
                    {showTab(2) && <KillFeed kills={killFeed} config={config} regionId={regionId} onRegionChange={changeRegion} />}
                    {showTab(2) && <ActiveHostileTracker lastUpdate={lastUpdate} regionId={regionId} />}

                    {/* Tab 4: Timers — structure timers are still worth tracking on red sov */}
                    {showTab(4) && <TimerBoard />}

                    {/* Tab 3: Intel — channel parser is standings-driven, not sov-driven */}
                    {showTab(3) && <IntelChannelParser config={config} onBoardChange={setIntelAlerts} />}
                </div>
            )}
            {isMobile && <MobileNav activeTab={activeTab} onTabChange={setMobileTab} tabs={tabs} />}
        </div>
    )
}

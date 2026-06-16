import React, { useState, useMemo } from 'react'
import CornerBrackets from './common/CornerBrackets'
import { AiSummaryButton, AiSummaryBox } from './common/AiSummary'
import { useAiSummary } from '../utils/useAiSummary'
import { useAuth } from '../utils/useAuth'

// Lowercase-keyed version built at module load for case-insensitive matching
const GROUP_CATEGORIES_LOWER = {}

const GROUP_CATEGORIES = {
    'Titan': 'SUPER', 'Supercarrier': 'SUPER',
    'Dreadnought': 'CAPITAL', 'Carrier': 'CAPITAL', 'Force Auxiliary': 'CAPITAL',
    'Black Ops': 'CAPITAL',
    'Battleship': 'BATTLESHIP', 'Marauder': 'BATTLESHIP',
    'Battlecruiser': 'BATTLECRUISER', 'Command Ship': 'BATTLECRUISER',
    'Attack Battlecruiser': 'BATTLECRUISER',
    'Strategic Cruiser': 'DOCTRINE', 'Heavy Assault Cruiser': 'DOCTRINE',
    'Force Recon Ship': 'RECON', 'Combat Recon Ship': 'RECON',
    'Logistics Cruiser': 'SUPPORT', 'Logistics Frigate': 'SUPPORT',
    'Interceptor': 'TACKLE', 'Interdictor': 'TACKLE', 'Heavy Interdictor': 'TACKLE',
    'Cruiser': 'CRUISER', 'Electronic Attack Ship': 'EWAR',
    'Covert Ops': 'COVOPS', 'Stealth Bomber': 'BOMBER',
    'Destroyer': 'DESTROYER', 'Assault Frigate': 'FRIGATE', 'Frigate': 'FRIGATE',
    'Capsule': 'POD',
    // Upwell structure groups
    'Citadel': 'STRUCTURE', 'Engineering Complex': 'STRUCTURE', 'Refinery': 'STRUCTURE',
    'Jump Gate': 'STRUCTURE',             // Ansiblex Jump Gate
    'Orbital Infrastructure': 'STRUCTURE', // Player-owned Customs Office (POCO)
    'Control Tower': 'STRUCTURE',          // POS towers
    'Moon Drill': 'STRUCTURE',             // Metenox Moon Harvester
    'Starbase Defense': 'STRUCTURE',       // POS guns/batteries
    'Cynosural Beacon': 'STRUCTURE',       // Upwell Cyno Beacon
    // Upwell type-name fallbacks (for when Group column is missing/blank)
    'Astrahus': 'STRUCTURE', 'Fortizar': 'STRUCTURE', 'Keepstar': 'STRUCTURE',
    'Raitaru': 'STRUCTURE', 'Azbel': 'STRUCTURE', 'Sotiyo': 'STRUCTURE',
    'Athanor': 'STRUCTURE', 'Tatara': 'STRUCTURE',
    'Ansiblex Jump Gate': 'STRUCTURE', 'Metenox Moon Harvester': 'STRUCTURE',
    'Customs Office': 'STRUCTURE',
    // Deployables
    'Mobile Depot': 'DEPLOYABLE', 'Mobile Cynosural Inhibitor': 'DEPLOYABLE',
    'Mobile Cyno Inhibitor': 'DEPLOYABLE',
    'Mobile Large Warp Disruptor': 'BUBBLE', 'Mobile Medium Warp Disruptor': 'BUBBLE',
    'Mobile Small Warp Disruptor': 'BUBBLE',
    'Scanner Probe': 'PROBE', 'Survey Probe': 'PROBE', 'Combat Scanner Probe': 'PROBE',
    'Sovereignty Blockade Unit': 'SOV', 'Infrastructure Hub': 'SOV', 'Sovereignty Hub': 'SOV',
    // Misc objects to silently ignore (not threats, not structures)
    'Sun': 'PROBE', // suns show up on dscan — bucket into PROBE so they're skipped

    // ===== SHIP TYPE NAMES (when Group column is blank/dash) =====
    // Titans
    'Avatar': 'SUPER', 'Erebus': 'SUPER', 'Ragnarok': 'SUPER', 'Leviathan': 'SUPER',
    'Vanquisher': 'SUPER', 'Komodo': 'SUPER', 'Molok': 'SUPER', 'Azariel': 'SUPER',
    // Supercarriers
    'Aeon': 'SUPER', 'Nyx': 'SUPER', 'Hel': 'SUPER', 'Wyvern': 'SUPER',
    'Vendetta': 'SUPER', 'Revenant': 'SUPER', 'Vehement': 'SUPER',
    // Dreadnoughts
    'Revelation': 'CAPITAL', 'Naglfar': 'CAPITAL', 'Moros': 'CAPITAL', 'Phoenix': 'CAPITAL',
    'Zirnitra': 'CAPITAL',
    'Revelation Navy Issue': 'CAPITAL', 'Phoenix Navy Issue': 'CAPITAL',
    // Carriers
    'Archon': 'CAPITAL', 'Thanatos': 'CAPITAL', 'Chimera': 'CAPITAL', 'Nidhoggur': 'CAPITAL',
    // Force Auxiliaries
    'Apostle': 'CAPITAL', 'Lif': 'CAPITAL', 'Ninazu': 'CAPITAL', 'Minokawa': 'CAPITAL',
    // Black Ops
    'Sin': 'CAPITAL', 'Widow': 'CAPITAL', 'Panther': 'CAPITAL', 'Redeemer': 'CAPITAL',
    // Marauders
    'Paladin': 'BATTLESHIP', 'Kronos': 'BATTLESHIP', 'Golem': 'BATTLESHIP', 'Vargur': 'BATTLESHIP',
    // T1 Battleships
    'Armageddon': 'BATTLESHIP', 'Apocalypse': 'BATTLESHIP', 'Abaddon': 'BATTLESHIP',
    'Dominix': 'BATTLESHIP', 'Megathron': 'BATTLESHIP', 'Hyperion': 'BATTLESHIP',
    'Raven': 'BATTLESHIP', 'Rokh': 'BATTLESHIP', 'Scorpion': 'BATTLESHIP',
    'Maelstrom': 'BATTLESHIP', 'Typhoon': 'BATTLESHIP', 'Tempest': 'BATTLESHIP',
    'Apocalypse Navy Issue': 'BATTLESHIP', 'Armageddon Navy Issue': 'BATTLESHIP',
    'Megathron Navy Issue': 'BATTLESHIP', 'Dominix Navy Issue': 'BATTLESHIP',
    'Raven Navy Issue': 'BATTLESHIP', 'Scorpion Navy Issue': 'BATTLESHIP',
    'Typhoon Fleet Issue': 'BATTLESHIP', 'Tempest Fleet Issue': 'BATTLESHIP',
    // Faction/Pirate Battleships
    'Bhaalgorn': 'BATTLESHIP', 'Vindicator': 'BATTLESHIP', 'Nightmare': 'BATTLESHIP',
    'Machariel': 'BATTLESHIP', 'Leshak': 'BATTLESHIP', 'Barghest': 'BATTLESHIP',
    'Rattlesnake': 'BATTLESHIP', 'Nestor': 'BATTLESHIP', 'Praxis': 'BATTLESHIP',
    'Drekavac': 'BATTLESHIP', 'Caiman': 'BATTLESHIP', 'Chemosh': 'BATTLESHIP',
    // Command Ships
    'Absolution': 'BATTLECRUISER', 'Damnation': 'BATTLECRUISER',
    'Astarte': 'BATTLECRUISER', 'Eos': 'BATTLECRUISER',
    'Nighthawk': 'BATTLECRUISER', 'Vulture': 'BATTLECRUISER',
    'Sleipnir': 'BATTLECRUISER', 'Claymore': 'BATTLECRUISER',
    // Attack BCs
    'Naga': 'BATTLECRUISER', 'Oracle': 'BATTLECRUISER', 'Tornado': 'BATTLECRUISER', 'Talos': 'BATTLECRUISER',
    // T1 Battlecruisers
    'Prophecy': 'BATTLECRUISER', 'Harbinger': 'BATTLECRUISER',
    'Drake': 'BATTLECRUISER', 'Ferox': 'BATTLECRUISER',
    'Cyclone': 'BATTLECRUISER', 'Hurricane': 'BATTLECRUISER',
    'Brutix': 'BATTLECRUISER', 'Myrmidon': 'BATTLECRUISER',
    'Harbinger Navy Issue': 'BATTLECRUISER', 'Drake Navy Issue': 'BATTLECRUISER',
    'Hurricane Fleet Issue': 'BATTLECRUISER', 'Brutix Navy Issue': 'BATTLECRUISER',
    // T3 Strategic Cruisers
    'Legion': 'DOCTRINE', 'Tengu': 'DOCTRINE', 'Proteus': 'DOCTRINE', 'Loki': 'DOCTRINE',
    // Heavy Assault Cruisers
    'Sacrilege': 'DOCTRINE', 'Zealot': 'DOCTRINE',
    'Cerberus': 'DOCTRINE', 'Eagle': 'DOCTRINE',
    'Muninn': 'DOCTRINE', 'Vagabond': 'DOCTRINE',
    'Deimos': 'DOCTRINE', 'Ishtar': 'DOCTRINE',
    // Force Recon
    'Pilgrim': 'RECON', 'Arazu': 'RECON', 'Falcon': 'RECON', 'Rapier': 'RECON',
    // Combat Recon
    'Curse': 'RECON', 'Lachesis': 'RECON', 'Rook': 'RECON', 'Huginn': 'RECON',
    // Logistics Cruisers
    'Guardian': 'SUPPORT', 'Oneiros': 'SUPPORT', 'Basilisk': 'SUPPORT', 'Scimitar': 'SUPPORT',
    // Logistics Frigates
    'Deacon': 'SUPPORT', 'Thalia': 'SUPPORT', 'Kirin': 'SUPPORT', 'Scalpel': 'SUPPORT',
    // Interceptors
    'Malediction': 'TACKLE', 'Crusader': 'TACKLE', 'Stiletto': 'TACKLE', 'Crow': 'TACKLE',
    'Raptor': 'TACKLE', 'Claw': 'TACKLE', 'Ares': 'TACKLE', 'Taranis': 'TACKLE',
    // Interdictors
    'Heretic': 'TACKLE', 'Flycatcher': 'TACKLE', 'Eris': 'TACKLE', 'Sabre': 'TACKLE',
    // Heavy Interdictors
    'Devoter': 'TACKLE', 'Broadsword': 'TACKLE', 'Phobos': 'TACKLE', 'Onyx': 'TACKLE',
    // Electronic Attack Ships
    'Sentinel': 'EWAR', 'Kitsune': 'EWAR', 'Keres': 'EWAR', 'Hyena': 'EWAR',
    // Stealth Bombers
    'Purifier': 'BOMBER', 'Hound': 'BOMBER', 'Manticore': 'BOMBER', 'Nemesis': 'BOMBER',
    // Covert Ops
    'Anathema': 'COVOPS', 'Buzzard': 'COVOPS', 'Helios': 'COVOPS', 'Cheetah': 'COVOPS',
    'Astero': 'COVOPS', 'Stratios': 'COVOPS',
    // T1 Cruisers — Amarr
    'Omen': 'CRUISER', 'Maller': 'CRUISER', 'Arbitrator': 'CRUISER', 'Augoror': 'CRUISER',
    // T1 Cruisers — Gallente
    'Thorax': 'CRUISER', 'Vexor': 'CRUISER', 'Exequror': 'CRUISER', 'Celestis': 'CRUISER',
    // T1 Cruisers — Caldari
    'Caracal': 'CRUISER', 'Blackbird': 'CRUISER', 'Moa': 'CRUISER', 'Osprey': 'CRUISER',
    // T1 Cruisers — Minmatar
    'Stabber': 'CRUISER', 'Rupture': 'CRUISER', 'Bellicose': 'CRUISER', 'Scythe': 'CRUISER',
    // Navy Cruisers
    'Omen Navy Issue': 'CRUISER', 'Vexor Navy Issue': 'CRUISER',
    'Caracal Navy Issue': 'CRUISER', 'Stabber Fleet Issue': 'CRUISER',
    // Faction/Pirate Cruisers
    'Gila': 'CRUISER', 'Cynabal': 'CRUISER', 'Phantasm': 'CRUISER', 'Vigilant': 'CRUISER',
    'Vedmak': 'CRUISER', 'Zarmazd': 'SUPPORT', 'Rodiva': 'SUPPORT',
    // T2 Destroyers / Command Destroyers
    'Pontifex': 'DESTROYER', 'Stork': 'DESTROYER', 'Magus': 'DESTROYER', 'Bifrost': 'DESTROYER',
    // T1 Destroyers — Amarr
    'Coercer': 'DESTROYER', 'Dragoon': 'DESTROYER',
    // T1 Destroyers — Gallente
    'Catalyst': 'DESTROYER', 'Algos': 'DESTROYER',
    // T1 Destroyers — Caldari
    'Cormorant': 'DESTROYER', 'Corax': 'DESTROYER',
    // T1 Destroyers — Minmatar
    'Thrasher': 'DESTROYER', 'Talwar': 'DESTROYER',
    // Navy/Faction Destroyers
    'Coercer Navy Issue': 'DESTROYER', 'Catalyst Navy Issue': 'DESTROYER',
    'Cormorant Navy Issue': 'DESTROYER', 'Thrasher Fleet Issue': 'DESTROYER',
    'Kikimora': 'DESTROYER',
    // T2 Assault Frigates — Amarr
    'Retribution': 'FRIGATE', 'Vengeance': 'FRIGATE',
    // T2 Assault Frigates — Gallente
    'Enyo': 'FRIGATE', 'Ishkur': 'FRIGATE',
    // T2 Assault Frigates — Caldari
    'Hawk': 'FRIGATE', 'Harpy': 'FRIGATE',
    // T2 Assault Frigates — Minmatar
    'Wolf': 'FRIGATE', 'Jaguar': 'FRIGATE',
    // Faction/Pirate Frigates
    'Daredevil': 'FRIGATE', 'Dramiel': 'FRIGATE', 'Cruor': 'FRIGATE', 'Succubus': 'FRIGATE',
    'Worm': 'FRIGATE', 'Imperial Navy Slicer': 'FRIGATE',
    'Caldari Navy Hookbill': 'FRIGATE', 'Republic Fleet Firetail': 'FRIGATE',
    'Federation Navy Comet': 'FRIGATE', 'Pacifier': 'FRIGATE', 'Enforcer': 'FRIGATE',
    // T1 Frigates — Amarr
    'Punisher': 'FRIGATE', 'Executioner': 'FRIGATE', 'Inquisitor': 'FRIGATE', 'Tormentor': 'FRIGATE',
    // T1 Frigates — Gallente
    'Incursus': 'FRIGATE', 'Atron': 'FRIGATE', 'Navitas': 'FRIGATE', 'Tristan': 'FRIGATE',
    // T1 Frigates — Caldari
    'Kestrel': 'FRIGATE', 'Merlin': 'FRIGATE', 'Bantam': 'FRIGATE', 'Heron': 'FRIGATE',
    // T1 Frigates — Minmatar
    'Rifter': 'FRIGATE', 'Breacher': 'FRIGATE', 'Slasher': 'FRIGATE',
    // Rookie / Civilian ships
    'Reaper': 'FRIGATE', 'Ibis': 'FRIGATE', 'Velator': 'FRIGATE', 'Impairor': 'FRIGATE',
    // Mining ships (sometimes on dscan)
    'Venture': 'FRIGATE', 'Endurance': 'FRIGATE',
    'Procurer': 'CRUISER', 'Retriever': 'CRUISER', 'Covetor': 'CRUISER',
    'Skiff': 'CRUISER', 'Mackinaw': 'CRUISER', 'Hulk': 'CRUISER',
    'Orca': 'CAPITAL', 'Rorqual': 'CAPITAL',
    // Misc containers/objects that show on dscan — suppress as PROBE so they're skipped
    'Enormous Freight Container': 'PROBE', 'Large Freight Container': 'PROBE',
    'Medium Freight Container': 'PROBE', 'Small Freight Container': 'PROBE',
    'Giant Freight Container': 'PROBE', 'Huge Freight Container': 'PROBE',
    'Secure Container': 'PROBE', 'Station Container': 'PROBE',
    'Mercenary Den': 'PROBE', 'Outpost Platform': 'PROBE',
}

// Populate lowercase map after GROUP_CATEGORIES is defined
Object.entries(GROUP_CATEGORIES).forEach(([k, v]) => { GROUP_CATEGORIES_LOWER[k.toLowerCase()] = v })

// Regex to detect distance-like fields so we skip them during column scanning
const DISTANCE_RE = /^[\d,.*-]|km$|au$| m$/i

const CATEGORY_ORDER = [
    'SUPER', 'CAPITAL', 'BATTLESHIP', 'BATTLECRUISER', 'DOCTRINE', 'RECON',
    'SUPPORT', 'TACKLE', 'CRUISER', 'EWAR', 'BOMBER', 'COVOPS',
    'DESTROYER', 'FRIGATE', 'POD',
    'STRUCTURE', 'DEPLOYABLE', 'BUBBLE', 'SOV', 'PROBE',
]

const CATEGORY_LABELS = {
    SUPER: 'Supercapital', CAPITAL: 'Capital', BATTLESHIP: 'Battleship',
    BATTLECRUISER: 'Battlecruiser', DOCTRINE: 'T3/HAC', RECON: 'Recon',
    SUPPORT: 'Logistics', TACKLE: 'Tackle/Dictor', CRUISER: 'Cruiser',
    EWAR: 'EWAR', BOMBER: 'Bomber', COVOPS: 'Covert Ops',
    DESTROYER: 'Destroyer', FRIGATE: 'Frigate', POD: 'Pod',
    STRUCTURE: 'Structure', DEPLOYABLE: 'Deployable', BUBBLE: 'Warp Bubble',
    SOV: 'Sov Object', PROBE: 'Probe',
}

const CATEGORY_COLORS = {
    SUPER: '#ff3355', CAPITAL: '#ff6677', BATTLESHIP: '#ffaa00',
    BATTLECRUISER: '#ffcc44', DOCTRINE: '#ff8844', RECON: '#ff9966',
    SUPPORT: '#00d4ff', TACKLE: '#cc88ff', CRUISER: '#88aaff',
    EWAR: '#aa88ff', BOMBER: '#9966cc', COVOPS: '#7755aa',
    DESTROYER: '#6699aa', FRIGATE: '#4488aa', POD: '#336677',
    STRUCTURE: '#66aa88', DEPLOYABLE: '#558877', BUBBLE: '#ddaa44',
    SOV: '#aaaaaa', PROBE: '#445566',
}

const THREAT_TIERS = [
    { tier: 'CRITICAL', color: '#ff3355', bg: 'rgba(255,51,85,0.15)', test: cats => cats.has('SUPER') },
    { tier: 'HIGH',     color: '#ff6677', bg: 'rgba(255,102,119,0.12)', test: cats => cats.has('CAPITAL') },
    { tier: 'MEDIUM',   color: '#ffaa00', bg: 'rgba(255,170,0,0.12)', test: cats => cats.has('DOCTRINE') || cats.has('RECON') },
    { tier: 'LOW',      color: '#ffcc44', bg: 'rgba(255,204,68,0.10)', test: cats => cats.has('BATTLESHIP') || cats.has('BATTLECRUISER') || cats.has('SUPPORT') || cats.has('TACKLE') },
    { tier: 'MINIMAL',  color: '#00ff88', bg: 'rgba(0,255,136,0.08)', test: () => true },
]

function parseDscan(raw) {
    if (!raw.trim()) return null

    // Normalise line endings (Windows \r\n → \n)
    const lines = raw.replace(/\r/g, '').trim().split('\n').map(l => l.trim()).filter(Boolean)
    const ships = []
    const structures = []
    let unrecognized = 0
    const unrecognizedSamples = []

    for (const line of lines) {
        const parts = line.split('\t')
        if (parts.length < 2) { unrecognized++; unrecognizedSamples.push(line); continue }

        // Scan every column for a GROUP_CATEGORIES match (case-insensitive).
        // Skip columns that look like distances ("1,234 km", "2.1 AU", "*", "-").
        // This handles any column order EVE might use.
        let cat = null
        let matchedField = ''
        for (const part of parts) {
            const val = part.trim()
            if (!val || DISTANCE_RE.test(val)) continue
            // Sun types appear as "Sun K2 (Yellow)" etc — prefix match
            if (/^Sun\s/i.test(val)) { cat = 'PROBE'; matchedField = val; break }
            const found = GROUP_CATEGORIES[val] || GROUP_CATEGORIES_LOWER[val.toLowerCase()]
            if (found) { cat = found; matchedField = val; break }
        }

        if (!cat) { unrecognized++; if (unrecognizedSamples.length < 5) unrecognizedSamples.push(line); continue }

        // Name: first column that isn't a distance and isn't the matched type/group field
        const name = parts.find(p => {
            const v = p.trim()
            return v && !DISTANCE_RE.test(v) && v !== matchedField
        })?.trim() || matchedField

        const entry = { name, type: matchedField, category: cat }

        if (['STRUCTURE', 'DEPLOYABLE', 'BUBBLE', 'SOV'].includes(cat)) {
            structures.push(entry)
        } else if (cat === 'PROBE') {
            // skip probes
        } else {
            ships.push(entry)
        }
    }

    // Group ships by category
    const byCat = {}
    for (const s of ships) {
        if (!byCat[s.category]) byCat[s.category] = { count: 0, types: {} }
        byCat[s.category].count++
        byCat[s.category].types[s.type] = (byCat[s.category].types[s.type] || 0) + 1
    }

    const presentCats = new Set(Object.keys(byCat))
    const threat = ships.length === 0
        ? { tier: 'CLEAR', color: '#00ff88', bg: 'rgba(0,255,136,0.08)' }
        : (THREAT_TIERS.find(t => t.test(presentCats)) || THREAT_TIERS[THREAT_TIERS.length - 1])

    return { byCat, structures, ships: ships.length, total: lines.length, unrecognized, unrecognizedSamples, threat }
}

function buildCopyText(result, shipCatRows, structureCounts) {
    const lines = [`THREAT: ${result.threat.tier}`]
    lines.push(`${result.ships} combat ships · ${result.structures.length} structures`)
    lines.push('')
    for (const { cat, count, types } of shipCatRows) {
        const typeStr = Object.entries(types)
            .sort((a, b) => b[1] - a[1])
            .map(([t, n]) => n > 1 ? `${t} x${n}` : t)
            .join(', ')
        lines.push(`${CATEGORY_LABELS[cat]}: ${count}  (${typeStr})`)
    }
    if (Object.keys(structureCounts).length > 0) {
        lines.push('')
        lines.push('Objects: ' + Object.entries(structureCounts)
            .map(([t, n]) => n > 1 ? `${t} x${n}` : t).join(', '))
    }
    return lines.join('\n')
}

export default function DscanParser() {
    const [rawInput, setRawInput] = useState('')
    const [copied, setCopied] = useState(false)
    const { authorized, ssoEnabled } = useAuth()
    // Show the AI button when the session can write (SSO) or when SSO is off
    // (demo / no-SSO) — matches the backend require_write_auth gate.
    const canUseAi = authorized || !ssoEnabled
    // In password-only deployments the AI endpoint is authed via X-Timer-Auth,
    // same as the other write features; under SSO the session cookie carries it.
    const writeHeaders = ssoEnabled ? {} : { 'X-Timer-Auth': localStorage.getItem('timer_auth') || '' }
    const { summary: aiSummary, generating: generatingAiSummary, error: aiError, generate } = useAiSummary(rawInput)

    const result = useMemo(() => parseDscan(rawInput), [rawInput])

    const shipCatRows = result
        ? CATEGORY_ORDER.filter(cat => result.byCat[cat]).map(cat => ({
            cat,
            count: result.byCat[cat].count,
            types: result.byCat[cat].types,
        }))
        : []

    // Group structures by type
    const structureCounts = result?.structures.reduce((acc, s) => {
        acc[s.type] = (acc[s.type] || 0) + 1
        return acc
    }, {}) || {}

    function generateAiSummary() {
        if (!result) return
        const shipData = shipCatRows.map(({ cat, count, types }) => {
            const typesStr = Object.entries(types)
                .map(([t, n]) => n > 1 ? `${t} x${n}` : t).join(', ')
            return `${CATEGORY_LABELS[cat]}: ${count} (${typesStr})`
        }).join('\n')

        generate({
            type: 'dscan',
            data: `Total Combat Ships: ${result.ships}\n${shipData}`,
        }, writeHeaders)
    }

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">DSCAN PARSER</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {result && <span className="panel-badge">{result.ships} ships · {result.total} total</span>}
                    {result && (
                        <button
                            onClick={async () => {
                                const text = buildCopyText(result, shipCatRows, structureCounts)
                                try {
                                    await navigator.clipboard.writeText(text)
                                } catch {
                                    const el = document.createElement('textarea')
                                    el.value = text
                                    document.body.appendChild(el)
                                    el.select()
                                    document.execCommand('copy')
                                    document.body.removeChild(el)
                                }
                                setCopied(true)
                                setTimeout(() => setCopied(false), 2000)
                            }}
                            style={{
                                background: 'none',
                                border: `1px solid ${copied ? '#00ff8866' : 'var(--border-dim)'}`,
                                color: copied ? '#00ff88' : 'var(--text-secondary)',
                                cursor: 'pointer',
                                fontFamily: 'Share Tech Mono, monospace',
                                fontSize: 10, padding: '2px 8px', letterSpacing: 1,
                                transition: 'color 0.2s, border-color 0.2s',
                            }}
                        >{copied ? 'COPIED!' : 'COPY'}</button>
                    )}
                    {rawInput && (
                        <button
                            onClick={() => setRawInput('')}
                            style={{
                                background: 'none', border: '1px solid var(--border-dim)',
                                color: 'var(--text-secondary)', cursor: 'pointer',
                                fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                                padding: '2px 8px', letterSpacing: 1,
                            }}
                        >CLEAR</button>
                    )}
                </div>
            </div>

            <textarea
                value={rawInput}
                onChange={e => setRawInput(e.target.value)}
                placeholder="Paste EVE directional scan output here..."
                style={{
                    width: '100%', minHeight: 80, background: 'rgba(0,0,0,0.3)',
                    border: '1px solid var(--border-dim)', color: 'var(--text-primary)',
                    fontFamily: 'Share Tech Mono, monospace', fontSize: 11,
                    padding: '8px 10px', resize: 'vertical', outline: 'none',
                    boxSizing: 'border-box',
                }}
            />

            {result && (
                <>
                    {/* Threat Banner */}
                    <div style={{
                        marginTop: 10, padding: '7px 12px',
                        background: result.threat.bg,
                        border: `1px solid ${result.threat.color}`,
                        display: 'flex', alignItems: 'center', gap: 12,
                    }}>
                        <span style={{
                            fontFamily: 'Orbitron, sans-serif', fontSize: 11,
                            fontWeight: 700, letterSpacing: 3,
                            color: result.threat.color,
                        }}>THREAT: {result.threat.tier}</span>
                        <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: 'var(--text-secondary)' }}>
                            {result.ships} combat ships · {result.structures.length} structures
                            {result.unrecognized > 0 && ` · ${result.unrecognized} unrecognized`}
                        </span>
                        {canUseAi && <>
                            <div style={{ flex: 1 }} />
                            <AiSummaryButton
                                generating={generatingAiSummary}
                                disabled={result.ships === 0}
                                onClick={generateAiSummary}
                            />
                        </>}
                    </div>

                    <AiSummaryBox summary={aiSummary} error={aiError} />

                    {/* Ship Groups */}
                    {shipCatRows.length > 0 && (
                        <div style={{ marginTop: 10 }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <tbody>
                                    {shipCatRows.map(({ cat, count, types }) => (
                                        <tr key={cat} style={{ borderBottom: '1px solid var(--border-dim)' }}>
                                            <td style={{ padding: '5px 8px', width: 120 }}>
                                                <span style={{
                                                    fontFamily: 'Orbitron, sans-serif', fontSize: 9,
                                                    fontWeight: 600, letterSpacing: 2,
                                                    color: CATEGORY_COLORS[cat],
                                                }}>{CATEGORY_LABELS[cat]}</span>
                                            </td>
                                            <td style={{ padding: '5px 8px', width: 40, textAlign: 'right' }}>
                                                <span style={{
                                                    fontFamily: 'Share Tech Mono, monospace', fontSize: 12,
                                                    color: CATEGORY_COLORS[cat], fontWeight: 700,
                                                }}>{count}</span>
                                            </td>
                                            <td style={{ padding: '5px 8px' }}>
                                                <span style={{
                                                    fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                                                    color: 'var(--text-secondary)',
                                                }}>
                                                    {Object.entries(types)
                                                        .sort((a, b) => b[1] - a[1])
                                                        .map(([t, n]) => n > 1 ? `${t} ×${n}` : t)
                                                        .join(', ')}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Structures / Deployables */}
                    {result.structures.length > 0 && (
                        <div style={{ marginTop: 8, padding: '6px 8px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-dim)' }}>
                            <span style={{
                                fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 2,
                                color: 'var(--text-secondary)', marginRight: 10,
                            }}>OBJECTS</span>
                            {Object.entries(structureCounts).map(([type, n]) => (
                                <span key={type} style={{
                                    fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                                    color: 'var(--text-primary)', marginRight: 12,
                                }}>
                                    {type}{n > 1 ? ` ×${n}` : ''}
                                </span>
                            ))}
                        </div>
                    )}

                    {result.ships === 0 && result.structures.length === 0 && (
                        <div style={{ padding: '8px 0', color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                            No recognized ships or structures found.
                        </div>
                    )}

                    {/* Debug: show sample unrecognized lines so we can identify format issues */}
                    {result.unrecognized > 0 && result.unrecognizedSamples.length > 0 && (
                        <div style={{ marginTop: 8, padding: '6px 8px', background: 'rgba(255,170,0,0.05)', border: '1px solid var(--amber-dim)' }}>
                            <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 2, color: 'var(--amber)', marginRight: 8 }}>
                                UNRECOGNIZED ({result.unrecognized})
                            </span>
                            <div style={{ marginTop: 4 }}>
                                {result.unrecognizedSamples.map((l, i) => (
                                    <div key={i} style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-muted)', whiteSpace: 'pre' }}>
                                        {l.replace(/\t/g, ' → ')}
                                    </div>
                                ))}
                                {result.unrecognized > result.unrecognizedSamples.length && (
                                    <div style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 9, color: 'var(--text-muted)' }}>
                                        …and {result.unrecognized - result.unrecognizedSamples.length} more
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </>
            )}

            {!rawInput && (
                <div style={{ padding: '8px 0', color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                    In EVE: open D-Scan, select all results (Ctrl+A), copy (Ctrl+C), paste above.
                </div>
            )}
        </div>
    )
}

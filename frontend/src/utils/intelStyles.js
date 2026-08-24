/**
 * Shared colour maps for the pilot-intel surfaces (Local Scanner, Fleet Comp,
 * and the shared read-only renderings of both).
 *
 * These were declared separately in each component, which meant a risk tier
 * could drift to a different colour depending on which panel you read it in.
 * IntelChannelParser deliberately still keeps its own copy — it may be removed
 * outright, and there is no point coupling it to this first.
 */

// Risk tiers from POST /api/chars/analyze.
// FleetCompAnalyzer previously used a marginally darker `nodata` (#2a3a4a);
// unified here so the same tier reads the same colour in both panels.
export const RISK_COLOR = {
    very_dangerous: '#ff2244',
    dangerous:      '#ff3355',
    moderate:       '#ffaa00',
    snuggly:        '#00d4ff',
    newbie:         '#6a8090',
    nodata:         '#334455',
}

export const RISK_ORDER = ['very_dangerous', 'dangerous', 'moderate', 'snuggly', 'newbie', 'nodata']

// Capital / covert role badges from _detect_roles() in routes/intel_routes.py.
export const ROLE_COLOR = {
    TITAN:   '#ff2244',
    SUPER:   '#ff5500',
    DREAD:   '#ff7744',
    CARRIER: '#ffaa44',
    FAX:     '#ffdd00',
    BLOPS:   '#cc44ff',
    RECON:   '#aa55ff',
    BOMBER:  '#8855dd',
    T3C:     '#7755cc',
    COVOPS:  '#6644aa',
}

export const FLEET_ROLE_COLOR = {
    LOGI:    '#00ff88',
    DICTOR:  '#00d4ff',
    HIC:     '#44aaff',
    BOOSTER: '#ffcc44',
    BOOSH:   '#ffdd66',
    BS:      '#ff7744',
    BC:      '#ff9944',
    HAC:     '#ffbb44',
    T3C:     '#7755cc',
    CRUISER: '#8a9aa0',
    FRIG:    '#6a8090',
    DESTROYER: '#6a8090',
}

export const CAPITAL_ROLES = new Set(['TITAN', 'SUPER', 'DREAD', 'CARRIER', 'FAX'])

// Local Scanner: a standing is a label to read, and `unknown` is neutral grey
// because a local list is mostly people you have no opinion about.
export const STANDING_CONFIG = {
    unknown:    { label: 'UNKNOWN',    color: '#6a8090', bg: 'rgba(106,128,144,0.08)' },
    friendly:   { label: 'FRIENDLY',   color: '#00d4ff', bg: 'rgba(0,212,255,0.08)' },
    lawn:       { label: 'LAWN',       color: '#00ff88', bg: 'rgba(0,255,136,0.08)' },
    unresolved: { label: '?',          color: '#ffaa00', bg: 'rgba(255,170,0,0.08)' },
}

export const STANDING_ORDER = { unknown: 0, friendly: 1, lawn: 2, unresolved: 3 }

// Fleet Comp: deliberately a different map, not a subset. You analyse a fleet
// because you are about to fight it, so `unknown` is hostile-orange rather than
// neutral grey. Do not collapse this into STANDING_CONFIG.
export const FLEET_STANDING_COLOR = {
    unknown:    { color: '#ff9966' },
    friendly:   { color: '#00d4ff' },
    lawn:       { color: '#00ff88' },
    unresolved: { color: '#ffaa00' },
}

/** Compact kill count: 1234 → "1.2k". */
export function formatKills(n) {
    return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)
}

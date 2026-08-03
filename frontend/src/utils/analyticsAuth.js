// localStorage keys for the operator-only /analytics page.
//
// The analytics credential is deliberately separate from the fleet-wide timer
// password ('timer_auth'): that one is handed out for timers and entosis, and
// reusing it would let anyone in the fleet read usage stats.

export const ANALYTICS_AUTH_KEY = 'analytics_auth'

// Set once this browser has successfully loaded stats. The dashboard uses it to
// decide whether to show the USAGE link, so the page stays unadvertised to
// everyone else. It is a UI hint only — access is enforced server-side.
export const ANALYTICS_SEEN_KEY = 'analytics_seen'

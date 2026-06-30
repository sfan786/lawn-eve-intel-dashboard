import '@testing-library/jest-dom'
import { vi } from 'vitest'

// jsdom does not provide a working localStorage in this environment, so
// components that read it during render (e.g. the X-Timer-Auth header in
// LocalScanner/DscanParser) throw "Cannot read properties of undefined".
// Provide a minimal in-memory stub for all tests.
if (typeof globalThis.localStorage === 'undefined') {
    const store = new Map()
    globalThis.localStorage = {
        getItem: vi.fn((key) => (store.has(key) ? store.get(key) : null)),
        setItem: vi.fn((key, value) => { store.set(key, String(value)) }),
        removeItem: vi.fn((key) => { store.delete(key) }),
        clear: vi.fn(() => { store.clear() }),
    }
}

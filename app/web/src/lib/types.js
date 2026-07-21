// Shared JSDoc types for incrementally typed scan-session code.

/**
 * @typedef {Object} ScanSessionPage
 * @property {string} id
 * @property {number} position
 * @property {string} preview_url
 * @property {string} created_at
 */

/**
 * @typedef {Object} ScanSession
 * @property {string} id
 * @property {string} device_id
 * @property {string} profile_id
 * @property {string|null} target_id
 * @property {string} source
 * @property {'interactive'|'automatic'} capture_mode
 * @property {'active'|'processing'|'completed'|'cancelled'} status
 * @property {ScanSessionPage[]} pages
 * @property {string} created_at
 * @property {string} updated_at
 */

export {};

// @ts-check

/** @typedef {import('./types.js').ScanSessionPage} ScanSessionPage */

/**
 * Return a complete page-id order after moving one page by a relative offset.
 * @param {ScanSessionPage[]} pages
 * @param {number} index
 * @param {number} delta
 * @returns {string[]}
 */
export function movedPageIds(pages, index, delta) {
  const next = index + delta;
  const ids = pages.map((page) => page.id);
  if (index < 0 || index >= ids.length || next < 0 || next >= ids.length) return ids;
  [ids[index], ids[next]] = [ids[next], ids[index]];
  return ids;
}

/**
 * Multi-page output is always PDF; a single photo may remain JPEG.
 * @param {number} pageCount
 * @param {string} category
 * @returns {'pdf'|'jpeg'}
 */
export function outputFormatFor(pageCount, category) {
  return pageCount > 1 || category !== 'photo' ? 'pdf' : 'jpeg';
}

/**
 * @param {string} source
 * @param {'interactive'|'automatic'} requested
 * @returns {'interactive'|'automatic'}
 */
export function captureModeFor(source, requested) {
  return source === 'ADF' ? requested : 'interactive';
}

import test from 'node:test';
import assert from 'node:assert/strict';

import { captureModeFor, movedPageIds, outputFormatFor } from './scanSession.js';

test('moves pages while preserving every id', () => {
  const pages = [{ id: 'one' }, { id: 'two' }, { id: 'three' }];
  assert.deepEqual(movedPageIds(pages, 1, -1), ['two', 'one', 'three']);
  assert.deepEqual(movedPageIds(pages, 0, -1), ['one', 'two', 'three']);
});

test('forces multi-page documents to PDF', () => {
  assert.equal(outputFormatFor(2, 'photo'), 'pdf');
  assert.equal(outputFormatFor(1, 'photo'), 'jpeg');
  assert.equal(outputFormatFor(1, 'document'), 'pdf');
});

test('automatic capture is limited to the ADF', () => {
  assert.equal(captureModeFor('ADF', 'automatic'), 'automatic');
  assert.equal(captureModeFor('Flatbed', 'automatic'), 'interactive');
});

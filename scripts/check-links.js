#!/usr/bin/env node
/**
 * Internal link checker for the Bullitt Cargo Bike site.
 * Scans the built `dist/` directory and reports any href that does NOT
 * start with the configured base path.
 *
 * Usage:
 *   npm run build && node scripts/check-links.js
 *
 * Exit codes:
 *   0 — no broken internal links found
 *   1 — one or more broken links detected
 */

import { readFileSync, readdirSync, statSync } from 'fs';
import { join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DIST_DIR = join(__dirname, '..', 'dist');
const BASE = '/bullitt-cargo-site';

// Collect all HTML files under dist/
function walkHtml(dir) {
  const results = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      results.push(...walkHtml(full));
    } else if (entry.endsWith('.html')) {
      results.push(full);
    }
  }
  return results;
}

// Match all href="..." and src="..." values
const LINK_RE = /(?:href|src)="([^"#?]+)"/g;

let broken = [];

for (const file of walkHtml(DIST_DIR)) {
  const html = readFileSync(file, 'utf8');
  let m;
  while ((m = LINK_RE.exec(html)) !== null) {
    const href = m[1];
    // Only check absolute-path links (start with /)
    if (!href.startsWith('/')) continue;
    // External protocol-relative links or mailto etc — skip
    if (href.startsWith('//')) continue;
    // Must start with the base path
    if (!href.startsWith(BASE) && href !== BASE) {
      broken.push({ file: file.replace(DIST_DIR, 'dist'), href });
    }
  }
}

if (broken.length === 0) {
  console.log('✓ No broken internal links found.');
  process.exit(0);
} else {
  console.error(`✗ ${broken.length} broken internal link(s) found:\n`);
  for (const { file, href } of broken) {
    console.error(`  ${file}\n    href="${href}"`);
  }
  process.exit(1);
}

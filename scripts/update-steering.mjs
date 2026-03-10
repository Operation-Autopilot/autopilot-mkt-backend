#!/usr/bin/env node

/**
 * update-steering.mjs
 *
 * Regenerates the directory tree and file inventory section of
 * .claude/steering/structure.md by scanning the actual codebase.
 *
 * Uses sentinel markers in structure.md to locate and replace sections:
 *   <!-- AUTO-TREE:START -->
 *   <!-- AUTO-TREE:END -->
 *   <!-- AUTO-MIGRATIONS:START -->
 *   <!-- AUTO-MIGRATIONS:END -->
 *
 * Usage:
 *   node scripts/update-steering.mjs
 *   npm run steering:update
 */

import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');
const STEERING_FILE = path.resolve(ROOT, '.claude', 'steering', 'structure.md');
const BACKEND_SRC = path.resolve(ROOT, 'src');
const MIGRATIONS_DIR = path.resolve(ROOT, 'supabase', 'migrations');

// ---------------------------------------------------------------------------
// Directory tree builder
// ---------------------------------------------------------------------------

const TREE_IGNORE = new Set([
  '__pycache__', '.pyc', 'node_modules', '.git',
  '.pytest_cache', '.ruff_cache', '.mypy_cache',
]);

function scanDir(dir, indent = 0) {
  if (!fs.existsSync(dir)) return [];
  const entries = fs.readdirSync(dir, { withFileTypes: true })
    .filter(e => !TREE_IGNORE.has(e.name) && !e.name.startsWith('.'))
    .sort((a, b) => {
      // Directories first, then files
      if (a.isDirectory() !== b.isDirectory()) return a.isDirectory() ? -1 : 1;
      return a.name.localeCompare(b.name);
    });

  const lines = [];
  for (const entry of entries) {
    const prefix = '│   '.repeat(indent) + (indent > 0 ? '├── ' : '');
    if (entry.isDirectory()) {
      lines.push(`${prefix}${entry.name}/`);
      lines.push(...scanDir(path.join(dir, entry.name), indent + 1));
    } else {
      lines.push(`${prefix}${entry.name}`);
    }
  }
  return lines;
}

function buildDirectoryTree() {
  const sections = [
    { label: 'src/api/routes/', dir: path.join(BACKEND_SRC, 'api', 'routes') },
    { label: 'src/api/middleware/', dir: path.join(BACKEND_SRC, 'api', 'middleware') },
    { label: 'src/services/', dir: path.join(BACKEND_SRC, 'services') },
    { label: 'src/schemas/', dir: path.join(BACKEND_SRC, 'schemas') },
    { label: 'src/models/', dir: path.join(BACKEND_SRC, 'models') },
    { label: 'src/core/', dir: path.join(BACKEND_SRC, 'core') },
  ];

  let tree = 'autopilot-mkt-backend/\n';

  for (const { label, dir } of sections) {
    if (!fs.existsSync(dir)) continue;
    tree += `├── ${label}\n`;
    const files = fs.readdirSync(dir)
      .filter(f => !TREE_IGNORE.has(f) && !f.startsWith('.') && !f.endsWith('.pyc'))
      .sort()
      .filter(f => fs.statSync(path.join(dir, f)).isFile());
    for (const f of files) {
      tree += `│   ├── ${f}\n`;
    }
  }

  // Scripts
  const scriptsDir = path.resolve(ROOT, 'scripts');
  if (fs.existsSync(scriptsDir)) {
    tree += `├── scripts/\n`;
    const files = fs.readdirSync(scriptsDir)
      .filter(f => !f.startsWith('.'))
      .sort()
      .filter(f => fs.statSync(path.join(scriptsDir, f)).isFile());
    for (const f of files) tree += `│   ├── ${f}\n`;
  }

  // Migrations
  if (fs.existsSync(MIGRATIONS_DIR)) {
    const migrations = fs.readdirSync(MIGRATIONS_DIR).filter(f => f.endsWith('.sql')).sort();
    tree += `└── supabase/migrations/  (${migrations.length} files)\n`;
    const last = migrations[migrations.length - 1];
    if (last) tree += `    └── ...${last}  ← last applied\n`;
  }

  return tree;
}

// ---------------------------------------------------------------------------
// Migration list builder
// ---------------------------------------------------------------------------

function buildMigrationList() {
  if (!fs.existsSync(MIGRATIONS_DIR)) return '_No migrations directory found._';

  const files = fs.readdirSync(MIGRATIONS_DIR)
    .filter(f => f.endsWith('.sql'))
    .sort();

  const lines = [];
  for (const f of files) {
    const content = fs.readFileSync(path.join(MIGRATIONS_DIR, f), 'utf-8');
    const basename = path.basename(f, '.sql');
    const commentMatch = content.match(/^--\s*(.+)/m);
    const description = commentMatch
      ? commentMatch[1].replace(/^Migration \d+:\s*/i, '').trim()
      : basename.replace(/_/g, ' ');
    lines.push(`- \`${basename}.sql\` — ${description}`);
  }

  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// Sentinel-based file updater
// ---------------------------------------------------------------------------

function replaceSection(content, startMarker, endMarker, newContent) {
  const startIdx = content.indexOf(startMarker);
  const endIdx = content.indexOf(endMarker);

  if (startIdx === -1 || endIdx === -1) return null; // markers not found

  const before = content.slice(0, startIdx + startMarker.length);
  const after = content.slice(endIdx);
  return `${before}\n${newContent}\n${after}`;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  if (!fs.existsSync(STEERING_FILE)) {
    console.error(`Steering file not found: ${STEERING_FILE}`);
    process.exit(1);
  }

  let content = fs.readFileSync(STEERING_FILE, 'utf-8');
  let changed = false;

  const tree = buildDirectoryTree();
  const updated1 = replaceSection(content, '<!-- AUTO-TREE:START -->', '<!-- AUTO-TREE:END -->', `\`\`\`\n${tree}\`\`\``);
  if (updated1 !== null) {
    content = updated1;
    changed = true;
    console.log('  Updated directory tree section');
  } else {
    console.log('  No AUTO-TREE markers found — skipping directory tree update');
  }

  const migrationList = buildMigrationList();
  const updated2 = replaceSection(content, '<!-- AUTO-MIGRATIONS:START -->', '<!-- AUTO-MIGRATIONS:END -->', migrationList);
  if (updated2 !== null) {
    content = updated2;
    changed = true;
    console.log('  Updated migrations list section');
  } else {
    console.log('  No AUTO-MIGRATIONS markers found — skipping migrations list update');
  }

  if (changed) {
    fs.writeFileSync(STEERING_FILE, content, 'utf-8');
    console.log(`  Written ${path.relative(ROOT, STEERING_FILE)}`);
  } else {
    console.log('  No sentinel markers found in structure.md — add markers to enable auto-update.');
    console.log('  See scripts/update-steering.mjs header for marker syntax.');
  }

  console.log('Done.');
}

main();

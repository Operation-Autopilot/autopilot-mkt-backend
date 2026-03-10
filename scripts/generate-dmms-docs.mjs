#!/usr/bin/env node

/**
 * generate-dmms-docs.mjs
 *
 * 1. Syncs feature statuses in the DMMS database by detecting file presence.
 * 2. Generates status pages under docs/status/ from the DMMS database.
 * 3. Generates docs/status/migrations.md from supabase/migrations/*.sql.
 * 4. Generates docs/status/services.md from service file docstrings.
 * 5. Writes JSON data files (docs/.vitepress/data/) for Vue components.
 *
 * Usage:
 *   node scripts/generate-dmms-docs.mjs
 *   npm run docs:generate
 */

import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';

const require = createRequire(import.meta.url);
const Database = require('better-sqlite3');

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');
const DB_PATH = path.resolve(ROOT, 'dmms', 'dmms.db');
const OUT_DIR = path.resolve(ROOT, 'docs', 'status');
const STATS_DIR = path.resolve(ROOT, 'docs', '.vitepress', 'data');

// Backend source root (same repo)
const BACKEND_SRC = path.resolve(ROOT, 'src');
// Frontend source root (sibling repo)
const FRONTEND_SRC = path.resolve(ROOT, '..', 'Autopilot-Marketplace-Discovery-to-Greenlight-', 'src');
// Supabase migrations
const MIGRATIONS_DIR = path.resolve(ROOT, 'supabase', 'migrations');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function timestamp() {
  return new Date().toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
}

function escapeCell(value) {
  if (value == null) return '';
  return String(value).replace(/\|/g, '\\|').replace(/\n/g, ' ');
}

function severityBadge(severity) {
  return `<span class="badge-${severity}">${severity}</span>`;
}

function statusBadge(status) {
  return `<span class="badge-${status}">${status}</span>`;
}

function confidenceBadge(confidence) {
  const mapping = { high: 'resolved', medium: 'medium', low: 'high' };
  const cls = mapping[confidence] || 'medium';
  return `<span class="badge-${cls}">${confidence}</span>`;
}

function writePage(filename, content) {
  const dest = path.join(OUT_DIR, filename);
  fs.writeFileSync(dest, content, 'utf-8');
  console.log(`  Generated ${path.relative(ROOT, dest)}`);
}

// ---------------------------------------------------------------------------
// Feature / File-Presence Sync
// ---------------------------------------------------------------------------

/**
 * Features that can be auto-detected from file presence.
 * - files: at least one must exist to mark as 'completed'
 * - project: 'Backend' or 'Frontend' (matched against projects table name)
 */
const FEATURE_PRESENCE_MAP = [
  // Backend — services
  {
    name: 'Gynger B2B Financing',
    project: 'Backend',
    files: ['src/services/gynger_service.py'],
    priority: 1,
    description: 'Gynger B2B financing application flow and webhook processing',
  },
  {
    name: 'Floor Plan Analysis',
    project: 'Backend',
    files: ['src/services/floor_plan_service.py', 'src/api/routes/floor_plans.py'],
    priority: 1,
    description: 'Floor plan upload and GPT-4o Vision analysis for sqft extraction',
  },
  {
    name: 'ROI Engine',
    project: 'Backend',
    files: ['src/services/roi_service.py', 'src/api/routes/roi.py'],
    priority: 1,
    description: 'ROI v2.1.0 formula-based calculation and greenlight recommendations',
  },
  {
    name: 'Recommendation Cache',
    project: 'Backend',
    files: ['src/services/recommendation_cache.py'],
    priority: 2,
    description: 'In-memory recommendation cache with TTL-based invalidation',
  },
  {
    name: 'Admin Layer',
    project: 'Backend',
    files: ['src/api/routes/admin.py'],
    priority: 2,
    description: 'Admin-only endpoints for HubSpot, Fireflies, and share link management',
  },
  {
    name: 'HubSpot Integration',
    project: 'Backend',
    files: ['src/services/hubspot_service.py'],
    priority: 2,
    description: 'HubSpot OAuth, contact/company lookup, and meeting context retrieval',
  },
  {
    name: 'Fireflies Integration',
    project: 'Backend',
    files: ['src/services/fireflies_service.py'],
    priority: 2,
    description: 'Fireflies GraphQL API for meeting transcripts and field extraction',
  },
  {
    name: 'Share Links',
    project: 'Backend',
    files: ['src/api/routes/shares.py'],
    priority: 2,
    description: 'Public share link endpoints for ROI snapshots',
  },
  // Frontend
  {
    name: 'Admin Panel',
    project: 'Frontend',
    files: ['../Autopilot-Marketplace-Discovery-to-Greenlight-/src/components/admin/AdminPanel.tsx'],
    priority: 2,
    description: 'Tabbed admin UI: Prep-call (HubSpot/Fireflies) and Post-call tabs',
  },
  {
    name: 'Presentation Mode',
    project: 'Frontend',
    files: ['../Autopilot-Marketplace-Discovery-to-Greenlight-/src/components/admin/PresentationModeToggle.tsx'],
    priority: 3,
    description: 'Cmd+Shift+\\ shortcut hides chat and admin band for screen-share demos',
  },
  {
    name: 'Shared ROI Page',
    project: 'Frontend',
    files: ['../Autopilot-Marketplace-Discovery-to-Greenlight-/src/pages/SharedROIPage.tsx'],
    priority: 2,
    description: 'Public share page for ROI snapshots at /share/{token}',
  },
  {
    name: 'Floor Plan Upload UI',
    project: 'Frontend',
    files: ['../Autopilot-Marketplace-Discovery-to-Greenlight-/src/components/FloorPlanUpload.tsx'],
    priority: 2,
    description: 'Drag-and-drop floor plan upload with auto-fill sqft from vision analysis',
  },
  {
    name: 'E2E Playwright Suite',
    project: 'Frontend',
    files: ['../Autopilot-Marketplace-Discovery-to-Greenlight-/e2e/fixtures/sku_data.ts'],
    priority: 2,
    description: 'Playwright E2E suite: journeys, nonlinear, payment, procurement, multiuser',
  },
];

function syncFeatureStatuses(db) {
  const existing = db.prepare('SELECT id, name, status, project_id FROM features').all();
  const byName = {};
  for (const f of existing) byName[f.name.toLowerCase()] = f;

  const projects = db.prepare('SELECT id, name FROM projects').all();
  const projectByKeyword = {};
  for (const p of projects) {
    // "Frontend (React SPA)" → keyword 'frontend'
    // "Backend (FastAPI API)" → keyword 'backend'
    const keyword = p.name.split(' ')[0].toLowerCase();
    projectByKeyword[keyword] = p.id;
  }

  let updated = 0;
  let inserted = 0;

  for (const spec of FEATURE_PRESENCE_MAP) {
    const detected = spec.files.some(f => fs.existsSync(path.resolve(ROOT, f)));
    const detectedStatus = detected ? 'completed' : 'planned';

    const existing = byName[spec.name.toLowerCase()];
    if (existing) {
      if (detectedStatus === 'completed' && existing.status !== 'completed') {
        db.prepare("UPDATE features SET status = 'completed' WHERE id = ?").run(existing.id);
        updated++;
      }
    } else {
      const projectKeyword = (spec.project || 'backend').toLowerCase();
      const project_id = projectByKeyword[projectKeyword] || 2;
      db.prepare(
        'INSERT INTO features (project_id, name, status, priority, description) VALUES (?, ?, ?, ?, ?)'
      ).run(project_id, spec.name, detectedStatus, spec.priority, spec.description);
      inserted++;
      // Add to local map so duplicates in FEATURE_PRESENCE_MAP don't double-insert
      byName[spec.name.toLowerCase()] = { name: spec.name, status: detectedStatus, project_id };
    }
  }

  if (updated + inserted > 0) {
    console.log(`  Feature sync: ${updated} updated, ${inserted} inserted`);
  }
}

// ---------------------------------------------------------------------------
// Service Docstring Scanner
// ---------------------------------------------------------------------------

function scanServiceDocstrings() {
  const servicesDir = path.join(BACKEND_SRC, 'services');
  const descriptions = {};
  if (!fs.existsSync(servicesDir)) return descriptions;

  for (const f of fs.readdirSync(servicesDir)) {
    if (!f.endsWith('.py') || f === '__init__.py') continue;
    const content = fs.readFileSync(path.join(servicesDir, f), 'utf-8');
    // Match module-level triple-quoted docstring (possibly after # comments)
    const m = content.match(/^(?:#[^\n]*\n)*\s*"""([\s\S]*?)"""/);
    if (m) {
      const firstLine = m[1].trim().split('\n')[0].trim();
      if (firstLine) descriptions[f] = firstLine;
    }
  }
  return descriptions;
}

// ---------------------------------------------------------------------------
// Stats Computation
// ---------------------------------------------------------------------------

function countFilesAndLines(dir, extensions) {
  let files = 0;
  let lines = 0;
  if (!fs.existsSync(dir)) return { files, lines };
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      const sub = countFilesAndLines(full, extensions);
      files += sub.files;
      lines += sub.lines;
    } else if (extensions.some(ext => entry.name.endsWith(ext))) {
      files++;
      lines += fs.readFileSync(full, 'utf-8').split('\n').length;
    }
  }
  return { files, lines };
}

function countTestCases(content) {
  let count = 0;
  const lines = content.split('\n');
  for (const line of lines) {
    const trimmed = line.trimStart();
    if (trimmed.startsWith('//') || trimmed.startsWith('#') || trimmed.startsWith('*') || trimmed.startsWith('/*')) continue;
    // Python test functions
    if (/\bdef test_/.test(trimmed)) count++;
    // JS/TS test functions (vitest + playwright)
    if (/\b(it|test)\s*\(/.test(trimmed)) count++;
  }
  return count;
}

function computeServiceInventory() {
  const servicesDir = path.join(BACKEND_SRC, 'services');
  const inventory = [];
  if (!fs.existsSync(servicesDir)) return inventory;

  const docstrings = scanServiceDocstrings();
  const files = fs.readdirSync(servicesDir).filter(f => f.endsWith('.py') && f !== '__init__.py');
  for (const f of files) {
    const content = fs.readFileSync(path.join(servicesDir, f), 'utf-8');
    const lines = content.split('\n').length;
    const description = docstrings[f] || '(undocumented)';
    inventory.push({ file: f, lines, description });
  }
  inventory.sort((a, b) => b.lines - a.lines);
  return inventory;
}

function computeBackendStats() {
  const pyExts = ['.py'];
  const routes = countFilesAndLines(path.join(BACKEND_SRC, 'api', 'routes'), pyExts);
  const services = countFilesAndLines(path.join(BACKEND_SRC, 'services'), pyExts);
  const schemas = countFilesAndLines(path.join(BACKEND_SRC, 'schemas'), pyExts);
  const models = countFilesAndLines(path.join(BACKEND_SRC, 'models'), pyExts);
  const core = countFilesAndLines(path.join(BACKEND_SRC, 'core'), pyExts);

  return {
    routeFiles: routes.files,
    routeLines: routes.lines,
    serviceFiles: services.files,
    serviceLines: services.lines,
    schemaFiles: schemas.files,
    schemaLines: schemas.lines,
    modelFiles: models.files,
    modelLines: models.lines,
    coreFiles: core.files,
    coreLines: core.lines,
    serviceInventory: computeServiceInventory(),
  };
}

function computeFrontendStats() {
  const jsExts = ['.ts', '.tsx', '.js', '.jsx'];
  const components = countFilesAndLines(path.join(FRONTEND_SRC, 'components'), jsExts);
  const hooks = countFilesAndLines(path.join(FRONTEND_SRC, 'state', 'hooks'), jsExts);
  const state = countFilesAndLines(path.join(FRONTEND_SRC, 'state'), jsExts);

  return {
    componentFiles: components.files,
    componentLines: components.lines,
    hookFiles: hooks.files,
    hookLines: hooks.lines,
    stateFiles: state.files,
    stateLines: state.lines,
  };
}

function computeTestStats() {
  const pyTestsDir = path.resolve(ROOT, 'tests');
  const e2eDir = path.resolve(ROOT, '..', 'Autopilot-Marketplace-Discovery-to-Greenlight-', 'e2e');
  const pyExts = ['.py'];
  const jsExts = ['.ts', '.js'];

  const pyTotal = countFilesAndLines(pyTestsDir, pyExts);
  const e2eTotal = countFilesAndLines(e2eDir, jsExts);

  let testCaseCount = 0;

  if (fs.existsSync(pyTestsDir)) {
    const walk = (dir) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) walk(full);
        else if (entry.name.endsWith('.py')) testCaseCount += countTestCases(fs.readFileSync(full, 'utf-8'));
      }
    };
    walk(pyTestsDir);
  }

  let e2eTestCaseCount = 0;
  if (fs.existsSync(e2eDir)) {
    const walk = (dir) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) walk(full);
        else if (entry.name.endsWith('.ts') || entry.name.endsWith('.js')) {
          e2eTestCaseCount += countTestCases(fs.readFileSync(full, 'utf-8'));
        }
      }
    };
    walk(e2eDir);
  }

  return {
    totalTestFiles: pyTotal.files,
    totalTestLines: pyTotal.lines,
    testCaseCount,
    e2eTestFiles: e2eTotal.files,
    e2eTestCaseCount,
  };
}

// ---------------------------------------------------------------------------
// JSON Data Writers
// ---------------------------------------------------------------------------

function writeHierarchyJson(db) {
  const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('products','projects')").all();
  if (tables.length < 2) {
    console.log('  Skipping hierarchy JSON (tables not yet created)');
    return;
  }

  const products = db.prepare('SELECT id, name, description, status FROM products ORDER BY id').all();

  for (const product of products) {
    product.projects = db.prepare('SELECT id, name, description, status FROM projects WHERE product_id = ? ORDER BY id').all(product.id);

    for (const project of product.projects) {
      project.features = db.prepare(
        'SELECT id, name, status FROM features WHERE project_id = ? ORDER BY id'
      ).all(project.id);

      let projectTaskCount = 0;
      let projectCompletedTasks = 0;

      for (const feature of project.features) {
        const counts = db.prepare(
          "SELECT COUNT(*) AS total, COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) AS completed FROM tasks WHERE feature_id = ?"
        ).get(feature.id);
        feature.taskCount = counts.total;
        feature.completedTasks = counts.completed;
        projectTaskCount += counts.total;
        projectCompletedTasks += counts.completed;
      }

      project.taskCount = projectTaskCount;
      project.completedTasks = projectCompletedTasks;
    }
  }

  const totalTasks = db.prepare('SELECT COUNT(*) AS c FROM tasks').get().c;
  const completedTasks = db.prepare("SELECT COUNT(*) AS c FROM tasks WHERE status = 'completed'").get().c;
  const totalFeatures = db.prepare('SELECT COUNT(*) AS c FROM features').get().c;
  const totalIssues = db.prepare('SELECT COUNT(*) AS c FROM issues').get().c;
  const resolvedIssues = db.prepare("SELECT COUNT(*) AS c FROM issues WHERE status IN ('resolved','closed')").get().c;

  const hierarchy = {
    generatedAt: new Date().toISOString(),
    products,
    stats: { totalTasks, completedTasks, totalFeatures, totalIssues, resolvedIssues },
  };

  fs.mkdirSync(STATS_DIR, { recursive: true });
  const dest = path.join(STATS_DIR, 'product-hierarchy.json');
  fs.writeFileSync(dest, JSON.stringify(hierarchy, null, 2), 'utf-8');
  console.log(`  Generated ${path.relative(ROOT, dest)}`);
}

function writeStatsJson(db) {
  const issueCount = db.prepare('SELECT count(*) AS c FROM issues').get().c;
  const taskCount = db.prepare('SELECT count(*) AS c FROM tasks').get().c;
  const sessionCount = db.prepare('SELECT count(*) AS c FROM sessions').get().c;
  const researchCount = db.prepare('SELECT count(*) AS c FROM research').get().c;

  const backend = computeBackendStats();
  const frontend = computeFrontendStats();
  const tests = computeTestStats();

  const stats = {
    generatedAt: new Date().toISOString(),
    dmms: { issues: issueCount, tasks: taskCount, sessions: sessionCount, research: researchCount },
    backend,
    frontend,
    tests,
  };

  fs.mkdirSync(STATS_DIR, { recursive: true });
  const dest = path.join(STATS_DIR, 'project-stats.json');
  fs.writeFileSync(dest, JSON.stringify(stats, null, 2), 'utf-8');
  console.log(`  Generated ${path.relative(ROOT, dest)}`);
}

// ---------------------------------------------------------------------------
// Page Generators
// ---------------------------------------------------------------------------

function generateIssues(db, ts) {
  const total = db.prepare('SELECT count(*) AS c FROM issues').get().c;
  const open = db.prepare("SELECT count(*) AS c FROM issues WHERE status IN ('open','in_progress')").get().c;
  const resolved = db.prepare("SELECT count(*) AS c FROM issues WHERE status IN ('resolved','closed')").get().c;
  const critical = db.prepare("SELECT count(*) AS c FROM issues WHERE severity='critical'").get().c;
  const high = db.prepare("SELECT count(*) AS c FROM issues WHERE severity='high'").get().c;
  const medium = db.prepare("SELECT count(*) AS c FROM issues WHERE severity='medium'").get().c;
  const low = db.prepare("SELECT count(*) AS c FROM issues WHERE severity='low'").get().c;

  const openRows = db.prepare(
    "SELECT id, title, severity, category, files FROM issues WHERE status IN ('open','in_progress') ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, id"
  ).all();

  const resolvedRows = db.prepare(
    "SELECT id, title, severity, category, files FROM issues WHERE status IN ('resolved','closed') ORDER BY id"
  ).all();

  function issueTable(rows) {
    if (rows.length === 0) return '_None._\n';
    let t = '| ID | Title | Severity | Category | Files |\n';
    t += '|---|---|---|---|---|\n';
    for (const r of rows) {
      t += `| ${escapeCell(r.id)} | ${escapeCell(r.title)} | ${severityBadge(r.severity)} | ${escapeCell(r.category)} | ${escapeCell(r.files) || '--'} |\n`;
    }
    return t;
  }

  const md = `---
title: Issues Tracker
---

<!-- Auto-generated by scripts/generate-dmms-docs.mjs on ${ts} -->
<!-- Do not edit manually — run \`npm run docs:generate\` to update. -->

# Issues Tracker

<div class="stats-grid">
  <div class="stat-card"><div class="stat-value">${total}</div><div class="stat-label">Total</div></div>
  <div class="stat-card"><div class="stat-value">${open}</div><div class="stat-label">Open</div></div>
  <div class="stat-card"><div class="stat-value">${resolved}</div><div class="stat-label">Resolved</div></div>
  <div class="stat-card"><div class="stat-value">${critical}</div><div class="stat-label">Critical</div></div>
  <div class="stat-card"><div class="stat-value">${high}</div><div class="stat-label">High</div></div>
  <div class="stat-card"><div class="stat-value">${medium}</div><div class="stat-label">Medium</div></div>
  <div class="stat-card"><div class="stat-value">${low}</div><div class="stat-label">Low</div></div>
</div>

## Open Issues

${issueTable(openRows)}

## Resolved Issues

<details>
<summary>Show ${resolvedRows.length} resolved issues</summary>

${issueTable(resolvedRows)}

</details>
`;

  writePage('issues.md', md);
}

function generateSprints(db, ts) {
  const tasks = db.prepare(
    "SELECT id, sprint, title, status, description FROM tasks ORDER BY sprint, id"
  ).all();

  const groups = {};
  for (const t of tasks) {
    const key = t.sprint || 'unassigned';
    if (!groups[key]) groups[key] = [];
    groups[key].push(t);
  }

  let body = '';
  for (const [sprint, rows] of Object.entries(groups)) {
    body += `<div class="sprint-card">\n\n### ${sprint}\n\n`;
    body += '| ID | Title | Status | Description |\n';
    body += '|---|---|---|---|\n';
    for (const r of rows) {
      body += `| ${r.id} | ${escapeCell(r.title)} | ${statusBadge(r.status)} | ${escapeCell(r.description) || '--'} |\n`;
    }
    body += '\n</div>\n\n';
  }

  const md = `---
title: Sprints
---

<!-- Auto-generated by scripts/generate-dmms-docs.mjs on ${ts} -->
<!-- Do not edit manually — run \`npm run docs:generate\` to update. -->

# Sprints

${body}`;

  writePage('sprints.md', md);
}

function generateSessions(db, ts) {
  const rows = db.prepare(
    'SELECT created_at, session_type, summary, issues_logged, tasks_created FROM sessions ORDER BY created_at DESC'
  ).all();

  let table = '| Date | Type | Summary | Issues | Tasks |\n';
  table += '|---|---|---|---|---|\n';
  for (const r of rows) {
    const date = r.created_at ? r.created_at.split(' ')[0] : '--';
    table += `| ${date} | ${escapeCell(r.session_type)} | ${escapeCell(r.summary)} | ${r.issues_logged} | ${r.tasks_created} |\n`;
  }

  const md = `---
title: Audit Sessions
---

<!-- Auto-generated by scripts/generate-dmms-docs.mjs on ${ts} -->
<!-- Do not edit manually — run \`npm run docs:generate\` to update. -->

# Audit Sessions

${table}`;

  writePage('sessions.md', md);
}

function generateResearch(db, ts) {
  const rows = db.prepare(
    'SELECT topic, section, subsection, confidence, source FROM research ORDER BY section, id'
  ).all();

  const groups = {};
  for (const r of rows) {
    const key = r.section || 'Uncategorized';
    if (!groups[key]) groups[key] = [];
    groups[key].push(r);
  }

  let body = '';
  if (Object.keys(groups).length === 0) {
    body = '_No research entries yet._\n';
  } else {
    for (const [section, items] of Object.entries(groups)) {
      body += `<details>\n<summary>${escapeCell(section)} (${items.length} entries)</summary>\n\n`;
      body += '| Topic | Subsection | Confidence | Source |\n';
      body += '|---|---|---|---|\n';
      for (const r of items) {
        body += `| ${escapeCell(r.topic)} | ${escapeCell(r.subsection) || '--'} | ${confidenceBadge(r.confidence || 'medium')} | ${escapeCell(r.source) || '--'} |\n`;
      }
      body += '\n</details>\n\n';
    }
  }

  const md = `---
title: Research Database
---

<!-- Auto-generated by scripts/generate-dmms-docs.mjs on ${ts} -->
<!-- Do not edit manually — run \`npm run docs:generate\` to update. -->

# Research Database

${body}`;

  writePage('research.md', md);
}

function generateMigrationsPage(ts) {
  if (!fs.existsSync(MIGRATIONS_DIR)) {
    console.log('  Skipping migrations page (no supabase/migrations directory)');
    return;
  }

  const files = fs.readdirSync(MIGRATIONS_DIR)
    .filter(f => f.endsWith('.sql'))
    .sort();

  const migrations = files.map(f => {
    const content = fs.readFileSync(path.join(MIGRATIONS_DIR, f), 'utf-8');
    const basename = path.basename(f, '.sql');
    const numMatch = basename.match(/^(\d+)_(.+)$/);
    const num = numMatch ? numMatch[1] : '?';
    // First non-empty -- comment line as description
    const commentMatch = content.match(/^--\s*(.+)/m);
    const description = commentMatch
      ? commentMatch[1].replace(/^Migration \d+:\s*/i, '').trim()
      : basename.replace(/_/g, ' ');
    return { num, basename, filename: f, description };
  });

  const last = migrations.length > 0 ? migrations[migrations.length - 1] : null;

  let table = '| # | Migration | Description |\n';
  table += '|---|-----------|-------------|\n';
  for (const m of migrations) {
    table += `| ${m.num} | \`${m.basename}\` | ${escapeCell(m.description)} |\n`;
  }

  const md = `---
title: Database Migrations
---

<!-- Auto-generated by scripts/generate-dmms-docs.mjs on ${ts} -->
<!-- Do not edit manually — run \`npm run docs:generate\` to update. -->

# Database Migrations

> **Last applied:** ${last ? `\`${last.basename}\`` : '_none_'} &nbsp;·&nbsp; **Total:** ${migrations.length}

${table}

## Applying Migrations

\`\`\`bash
# Apply all pending migrations
supabase db push

# Create a new migration
supabase migration new <name>
\`\`\`

See [Database schema](../backend/database.md) for column-level documentation.
`;

  writePage('migrations.md', md);
}

function generateServicesPage(inventory, ts) {
  let table = '| Service File | Lines | Description |\n';
  table += '|--------------|-------|-------------|\n';
  for (const s of inventory) {
    table += `| \`${s.file}\` | ${s.lines} | ${escapeCell(s.description)} |\n`;
  }

  const md = `---
title: Service Inventory
---

<!-- Auto-generated by scripts/generate-dmms-docs.mjs on ${ts} -->
<!-- Do not edit manually — run \`npm run docs:generate\` to update. -->

# Service Inventory

${table}

> Descriptions extracted from module-level docstrings. Sorted by file size descending.
`;

  writePage('services.md', md);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  if (!fs.existsSync(DB_PATH)) {
    console.error(`DMMS database not found at ${DB_PATH}`);
    console.error('Run: npm run dmms:migrate');
    process.exit(1);
  }

  // Open writable — needed to sync feature statuses
  const db = new Database(DB_PATH);
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const ts = timestamp();
  console.log(`Generating DMMS docs (${ts})...`);

  // 1. Sync feature statuses from file presence
  console.log('  Syncing feature statuses...');
  syncFeatureStatuses(db);

  // 2. Generate standard status pages from DMMS
  generateIssues(db, ts);
  generateSprints(db, ts);
  generateSessions(db, ts);
  generateResearch(db, ts);

  // 3. Generate source-derived pages
  generateMigrationsPage(ts);
  const inventory = computeServiceInventory();
  generateServicesPage(inventory, ts);

  // 4. Write JSON data for Vue components
  writeStatsJson(db);
  writeHierarchyJson(db);

  db.close();
  console.log('Done.');
}

main();

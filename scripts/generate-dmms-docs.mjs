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
const TESTING_DIR = path.resolve(ROOT, 'docs', 'testing');
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
  // Live data is served by the /_dmms/issues API (dmms-plugin.mjs).
  // This stub keeps frontmatter + component tag; actual content loads at runtime.
  const md = `---
title: Issues Tracker
---

# Issues Tracker

<IssuesPage />
`;

  writePage('issues.md', md);
}

function generateSprints(db, ts) {
  // Live data is served by the /_dmms/sprints API (dmms-plugin.mjs).
  // This stub keeps frontmatter + component tag; actual content loads at runtime.
  const md = `---
title: Sprints
---

# Sprints

<SprintsPage />
`;

  writePage('sprints.md', md);
}

function generateSessions(db, ts) {
  // Live data is served by the /_dmms/sessions API (dmms-plugin.mjs).
  // This stub keeps frontmatter + component tag; actual content loads at runtime.
  const md = `---
title: Audit Sessions
---

# Audit Sessions

<SessionsPage />
`;

  writePage('sessions.md', md);
}

function generateResearch(db, ts) {
  // Live data is served by the /_dmms/research API (dmms-plugin.mjs).
  // This stub keeps frontmatter + component tag; actual content loads at runtime.
  const md = `---
title: Research Database
---

# Research Database

<ResearchPage />
`;

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
// Priority Matrix Generator
// ---------------------------------------------------------------------------

/**
 * Scoring weights for the priority matrix formula.
 * Score = (Revenue × 0.30) + (BugDensity × 0.25) + (BlastRadius × 0.20) + (UserFrequency × 0.15) + (RegressionRisk × 0.10)
 */
const SCORE_WEIGHTS = {
  revenue: 0.30,
  bugDensity: 0.25,
  blastRadius: 0.20,
  userFrequency: 0.15,
  regressionRisk: 0.10,
};

const SMOKE_THRESHOLD = 70;
const REGRESSION_THRESHOLD = 45;

/**
 * Static factor scores for each TC. These represent Revenue Impact, Blast Radius,
 * User Frequency, and base Regression Risk. Bug Density is computed dynamically.
 *
 * Format: tcNumber → { revenue, blastRadius, userFrequency, regressionRisk }
 */
const TC_FACTORS = {
  1:  { revenue: 25, blastRadius: 100, userFrequency: 100, regressionRisk: 20 },
  2:  { revenue: 25, blastRadius: 80, userFrequency: 90, regressionRisk: 60 },
  3:  { revenue: 10, blastRadius: 60, userFrequency: 90, regressionRisk: 40 },
  4:  { revenue: 5, blastRadius: 30, userFrequency: 80, regressionRisk: 10 },
  5:  { revenue: 10, blastRadius: 40, userFrequency: 60, regressionRisk: 10 },
  6:  { revenue: 30, blastRadius: 70, userFrequency: 85, regressionRisk: 80 },
  7:  { revenue: 30, blastRadius: 60, userFrequency: 30, regressionRisk: 40 },
  8:  { revenue: 30, blastRadius: 60, userFrequency: 30, regressionRisk: 30 },
  9:  { revenue: 25, blastRadius: 50, userFrequency: 20, regressionRisk: 10 },
  10: { revenue: 25, blastRadius: 50, userFrequency: 20, regressionRisk: 10 },
  11: { revenue: 50, blastRadius: 90, userFrequency: 90, regressionRisk: 60 },
  12: { revenue: 30, blastRadius: 60, userFrequency: 85, regressionRisk: 30 },
  13: { revenue: 40, blastRadius: 55, userFrequency: 40, regressionRisk: 60 },
  14: { revenue: 40, blastRadius: 55, userFrequency: 40, regressionRisk: 50 },
  15: { revenue: 25, blastRadius: 40, userFrequency: 25, regressionRisk: 10 },
  16: { revenue: 25, blastRadius: 50, userFrequency: 40, regressionRisk: 20 },
  17: { revenue: 15, blastRadius: 55, userFrequency: 30, regressionRisk: 30 },
  18: { revenue: 30, blastRadius: 50, userFrequency: 60, regressionRisk: 30 },
  19: { revenue: 35, blastRadius: 45, userFrequency: 40, regressionRisk: 40 },
  20: { revenue: 15, blastRadius: 35, userFrequency: 30, regressionRisk: 10 },
  21: { revenue: 10, blastRadius: 25, userFrequency: 15, regressionRisk: 10 },
  22: { revenue: 25, blastRadius: 55, userFrequency: 90, regressionRisk: 20 },
  23: { revenue: 10, blastRadius: 30, userFrequency: 40, regressionRisk: 10 },
  24: { revenue: 10, blastRadius: 30, userFrequency: 35, regressionRisk: 10 },
  25: { revenue: 20, blastRadius: 40, userFrequency: 60, regressionRisk: 20 },
  26: { revenue: 30, blastRadius: 50, userFrequency: 60, regressionRisk: 10 },
  27: { revenue: 5, blastRadius: 20, userFrequency: 20, regressionRisk: 10 },
  28: { revenue: 45, blastRadius: 65, userFrequency: 80, regressionRisk: 80 },
  29: { revenue: 40, blastRadius: 50, userFrequency: 75, regressionRisk: 60 },
  30: { revenue: 35, blastRadius: 40, userFrequency: 60, regressionRisk: 30 },
  31: { revenue: 40, blastRadius: 50, userFrequency: 70, regressionRisk: 20 },
  32: { revenue: 35, blastRadius: 45, userFrequency: 50, regressionRisk: 20 },
  33: { revenue: 25, blastRadius: 40, userFrequency: 40, regressionRisk: 20 },
  34: { revenue: 20, blastRadius: 25, userFrequency: 15, regressionRisk: 30 },
  35: { revenue: 80, blastRadius: 65, userFrequency: 50, regressionRisk: 40 },
  36: { revenue: 100, blastRadius: 75, userFrequency: 50, regressionRisk: 70 },
  37: { revenue: 100, blastRadius: 80, userFrequency: 50, regressionRisk: 80 },
  38: { revenue: 95, blastRadius: 60, userFrequency: 40, regressionRisk: 60 },
  39: { revenue: 100, blastRadius: 65, userFrequency: 40, regressionRisk: 50 },
  40: { revenue: 60, blastRadius: 35, userFrequency: 20, regressionRisk: 10 },
  41: { revenue: 40, blastRadius: 30, userFrequency: 20, regressionRisk: 20 },
  42: { revenue: 20, blastRadius: 20, userFrequency: 15, regressionRisk: 10 },
  43: { revenue: 80, blastRadius: 85, userFrequency: 60, regressionRisk: 60 },
  44: { revenue: 80, blastRadius: 85, userFrequency: 60, regressionRisk: 60 },
  45: { revenue: 50, blastRadius: 40, userFrequency: 30, regressionRisk: 10 },
  46: { revenue: 85, blastRadius: 80, userFrequency: 50, regressionRisk: 80 },
  47: { revenue: 90, blastRadius: 75, userFrequency: 50, regressionRisk: 60 },
  48: { revenue: 50, blastRadius: 55, userFrequency: 30, regressionRisk: 50 },
  49: { revenue: 30, blastRadius: 60, userFrequency: 50, regressionRisk: 50 },
  50: { revenue: 40, blastRadius: 65, userFrequency: 45, regressionRisk: 60 },
  51: { revenue: 55, blastRadius: 55, userFrequency: 30, regressionRisk: 30 },
  52: { revenue: 20, blastRadius: 40, userFrequency: 30, regressionRisk: 10 },
  53: { revenue: 15, blastRadius: 30, userFrequency: 15, regressionRisk: 10 },
  54: { revenue: 25, blastRadius: 45, userFrequency: 60, regressionRisk: 30 },
  55: { revenue: 30, blastRadius: 50, userFrequency: 55, regressionRisk: 20 },
  56: { revenue: 50, blastRadius: 45, userFrequency: 40, regressionRisk: 10 },
  57: { revenue: 10, blastRadius: 25, userFrequency: 30, regressionRisk: 10 },
  58: { revenue: 30, blastRadius: 40, userFrequency: 50, regressionRisk: 10 },
  59: { revenue: 15, blastRadius: 30, userFrequency: 10, regressionRisk: 20 },
  60: { revenue: 20, blastRadius: 35, userFrequency: 25, regressionRisk: 10 },
  61: { revenue: 90, blastRadius: 70, userFrequency: 30, regressionRisk: 40 },
  62: { revenue: 10, blastRadius: 25, userFrequency: 10, regressionRisk: 20 },
};

function generatePriorityMatrix(db, ts) {
  const mappingPath = path.join(TESTING_DIR, 'bug-tc-mapping.json');
  if (!fs.existsSync(mappingPath)) {
    console.log('  Skipping priority matrix (no bug-tc-mapping.json)');
    return;
  }

  const bugTcMapping = JSON.parse(fs.readFileSync(mappingPath, 'utf-8'));

  // Build reverse mapping: TC → [bugIds]
  const tcBugs = {};
  for (const [bugId, tcs] of Object.entries(bugTcMapping)) {
    for (const tc of tcs) {
      if (!tcBugs[tc]) tcBugs[tc] = [];
      tcBugs[tc].push(bugId);
    }
  }

  // Query DMMS DB for open bug counts by category prefix
  const openBugCounts = {};
  try {
    const issues = db.prepare(
      "SELECT title, status FROM issues WHERE status NOT IN ('resolved', 'closed')"
    ).all();
    // Count open bugs per category prefix (A, B, C, D, E, F, G)
    for (const issue of issues) {
      const match = issue.title.match(/^([A-G])-\d+/);
      if (match) {
        const prefix = match[1];
        openBugCounts[prefix] = (openBugCounts[prefix] || 0) + 1;
      }
    }
  } catch {
    // Issues table may use different schema — fall back to mapping counts
  }

  // Compute bug density score for each TC based on open bugs in its area
  function computeBugDensity(tcNum) {
    const bugs = tcBugs[tcNum] || [];
    // Count how many of those bugs are still open (not resolved in mapping status)
    // Use a simple heuristic: more mapped bugs = higher density
    const count = bugs.length;
    if (count >= 5) return 100;
    if (count >= 3) return 75;
    if (count >= 2) return 50;
    if (count >= 1) return 25;
    return 0;
  }

  // Compute scores for all 62 TCs
  const scored = [];
  for (let tc = 1; tc <= 62; tc++) {
    const factors = TC_FACTORS[tc];
    if (!factors) continue;

    const bugDensity = computeBugDensity(tc);
    const score = Math.round(
      factors.revenue * SCORE_WEIGHTS.revenue +
      bugDensity * SCORE_WEIGHTS.bugDensity +
      factors.blastRadius * SCORE_WEIGHTS.blastRadius +
      factors.userFrequency * SCORE_WEIGHTS.userFrequency +
      factors.regressionRisk * SCORE_WEIGHTS.regressionRisk
    );

    let tier = 'Full';
    if (score >= SMOKE_THRESHOLD) tier = 'Smoke';
    else if (score >= REGRESSION_THRESHOLD) tier = 'Regression';

    scored.push({
      tc,
      score,
      tier,
      bugs: (tcBugs[tc] || []).sort(),
    });
  }

  scored.sort((a, b) => b.score - a.score);

  const smokeTCs = scored.filter(s => s.tier === 'Smoke');
  const regressionTCs = scored.filter(s => s.tier === 'Regression');
  const totalBugsCovered = new Set(scored.flatMap(s => s.bugs)).size;
  const allMappedBugs = new Set(Object.keys(bugTcMapping));
  const bugsWithCoverage = new Set();
  for (const s of scored) {
    for (const b of s.bugs) bugsWithCoverage.add(b);
  }
  const uncoveredBugs = [...allMappedBugs].filter(b => !bugsWithCoverage.has(b));

  // Write summary JSON for Vue components
  const summaryData = {
    generatedAt: new Date().toISOString(),
    totalTCs: scored.length,
    smokeTCs: smokeTCs.length,
    regressionTCs: smokeTCs.length + regressionTCs.length,
    totalBugsCovered,
    scores: scored.map(s => ({ tc: s.tc, score: s.score, tier: s.tier, bugs: s.bugs })),
  };

  fs.mkdirSync(STATS_DIR, { recursive: true });
  const jsonDest = path.join(STATS_DIR, 'priority-matrix.json');
  fs.writeFileSync(jsonDest, JSON.stringify(summaryData, null, 2), 'utf-8');
  console.log(`  Generated ${path.relative(ROOT, jsonDest)}`);
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

  // 4. Generate priority matrix
  generatePriorityMatrix(db, ts);

  // 5. Write JSON data for Vue components
  writeStatsJson(db);
  writeHierarchyJson(db);

  db.close();
  console.log('Done.');
}

main();

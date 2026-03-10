#!/usr/bin/env node

/**
 * generate-dmms-docs.mjs
 *
 * Reads the DMMS database (dmms/dmms.db) and generates status pages
 * under docs/status/ plus JSON data files for Vue components.
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
    // JS/TS test functions
    if (/\b(it|test)\s*\(/.test(trimmed)) count++;
  }
  return count;
}

const SERVICE_DESCRIPTIONS = {
  'auth_service.py': 'Authentication logic — signup, login, token refresh, password reset',
  'profile_service.py': 'User profile CRUD operations',
  'company_service.py': 'Company creation, member management, role assignments',
  'conversation_service.py': 'Conversation and message CRUD, context reconstruction',
  'agent_service.py': 'OpenAI GPT-4o agent orchestration for chat responses',
  'rag_service.py': 'Pinecone vector search for product recommendations',
  'profile_extraction_service.py': 'AI-powered discovery profile extraction from conversations',
  'discovery_profile_service.py': 'Discovery data storage and retrieval',
  'session_service.py': 'Anonymous session management and linking',
  'checkout_service.py': 'Stripe checkout session creation and order management',
  'robot_catalog_service.py': 'Robot product catalog management',
  'recommendation_service.py': 'ROI-based robot recommendations',
  'recommendation_cache.py': 'Caching layer for recommendation results',
  'floor_plan_service.py': 'Floor plan upload and processing',
  'floor_plan_prompts.py': 'AI prompts for floor plan analysis',
  'recommendation_prompts.py': 'AI prompts for generating recommendations',
  'sales_knowledge_service.py': 'Sales knowledge base for agent context',
  'email_service.py': 'Email delivery for invitations and notifications',
  'invitation_service.py': 'Company invitation management',
};

function computeServiceInventory() {
  const servicesDir = path.join(BACKEND_SRC, 'services');
  const inventory = [];
  if (!fs.existsSync(servicesDir)) return inventory;

  const files = fs.readdirSync(servicesDir).filter(f => f.endsWith('.py') && f !== '__init__.py');
  for (const f of files) {
    const content = fs.readFileSync(path.join(servicesDir, f), 'utf-8');
    const lines = content.split('\n').length;
    const description = SERVICE_DESCRIPTIONS[f] || '(undocumented)';
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
  const testsDir = path.resolve(ROOT, 'tests');
  const pyExts = ['.py'];
  const total = countFilesAndLines(testsDir, pyExts);

  let testCaseCount = 0;
  if (fs.existsSync(testsDir)) {
    const walk = (dir) => {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) walk(full);
        else if (entry.name.endsWith('.py')) {
          testCaseCount += countTestCases(fs.readFileSync(full, 'utf-8'));
        }
      }
    };
    walk(testsDir);
  }

  return {
    totalTestFiles: total.files,
    totalTestLines: total.lines,
    testCaseCount,
  };
}

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

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  if (!fs.existsSync(DB_PATH)) {
    console.error(`DMMS database not found at ${DB_PATH}`);
    console.error('Run: npm run dmms:migrate');
    process.exit(1);
  }

  const db = new Database(DB_PATH, { readonly: true });
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const ts = timestamp();
  console.log(`Generating DMMS docs (${ts})...`);

  generateIssues(db, ts);
  generateSprints(db, ts);
  generateSessions(db, ts);
  generateResearch(db, ts);
  writeStatsJson(db);
  writeHierarchyJson(db);

  db.close();
  console.log('Done.');
}

main();

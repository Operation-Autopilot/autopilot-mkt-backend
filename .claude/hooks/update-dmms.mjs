#!/usr/bin/env node

/**
 * update-dmms.mjs — Claude Code PostToolUse hook
 *
 * Fires after every Bash tool call. When a git commit is detected,
 * calls Claude (Haiku) to analyze the diff and updates the DMMS
 * SQLite database with new tasks, resolved issues, and feature status changes.
 *
 * Works from either the backend repo or the frontend repo — it auto-detects
 * the DMMS path based on __dirname.
 *
 * Required env var: ANTHROPIC_API_KEY (already present in Claude Code sessions)
 */

import { execSync } from 'child_process';
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ---------------------------------------------------------------------------
// Entrypoint — read stdin from Claude Code, then dispatch
// ---------------------------------------------------------------------------

let rawInput = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { rawInput += chunk; });
process.stdin.on('end', () => { main().catch(() => {}).finally(() => process.exit(0)); });

async function main() {
  const data = JSON.parse(rawInput || '{}');
  const command = (data?.tool_input?.command || '').trim();

  // Only act on actual git commit commands
  if (!isGitCommit(command)) return;

  // Locate the DMMS database (works from backend or frontend repo)
  const dmmsPath = findDmmsPath(__dirname);
  if (!dmmsPath) return;

  // Get commit details
  const commitInfo = getCommitInfo();
  if (!commitInfo) return;

  // Open DB + build context for the LLM
  const db = openDatabase(dmmsPath);
  if (!db) return;

  try {
    const context = getDmmsContext(db);
    const updates = await analyzeWithClaude(commitInfo, context);
    if (updates) applyUpdates(db, updates);
  } finally {
    db.close();
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isGitCommit(command) {
  // Match `git commit` but exclude --dry-run, echo strings, comments, --amend-only checks
  return (
    /\bgit\s+commit\b/.test(command) &&
    !command.includes('--dry-run') &&
    !command.trimStart().startsWith('#') &&
    !command.trimStart().startsWith('echo')
  );
}

function findDmmsPath(hooksDir) {
  // Case 1: Running from within the backend repo
  //   hooksDir = autopilot-mkt-backend/.claude/hooks/
  //   DMMS    = autopilot-mkt-backend/dmms/dmms.db
  const backendLocal = path.resolve(hooksDir, '../../dmms/dmms.db');
  if (fs.existsSync(backendLocal)) return backendLocal;

  // Case 2: Running from the frontend repo (backend is a sibling directory)
  //   hooksDir = Autopilot-Marketplace-Discovery-to-Greenlight-/.claude/hooks/
  //   DMMS    = ../autopilot-mkt-backend/dmms/dmms.db
  const frontendSibling = path.resolve(hooksDir, '../../../autopilot-mkt-backend/dmms/dmms.db');
  if (fs.existsSync(frontendSibling)) return frontendSibling;

  return null;
}

function getCommitInfo() {
  try {
    const hash = execSync('git rev-parse HEAD', { encoding: 'utf8' }).trim();
    const message = execSync('git log -1 --format=%B HEAD', { encoding: 'utf8' }).trim();
    const stat = execSync('git diff HEAD~1 HEAD --stat --no-color', {
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'ignore'],
    }).trim();

    let diff = '';
    try {
      diff = execSync('git diff HEAD~1 HEAD --no-color', {
        encoding: 'utf8',
        maxBuffer: 400 * 1024,
        stdio: ['pipe', 'pipe', 'ignore'],
      }).trim();
    } catch {
      // First commit or diff too large — stat alone is sufficient
    }

    return { hash, message, stat, diff: diff.slice(0, 6000) };
  } catch {
    return null;
  }
}

function openDatabase(dmmsPath) {
  try {
    // Resolve better-sqlite3 from the backend's own node_modules.
    // This works even when the script is called from the frontend repo because
    // __dirname always points to the backend's .claude/hooks/ directory.
    const backendPkgDir = path.resolve(path.dirname(dmmsPath), '..');
    const backendPkg = path.join(backendPkgDir, 'package.json');
    const req = fs.existsSync(backendPkg)
      ? createRequire(backendPkg)
      : createRequire(import.meta.url);
    const Database = req('better-sqlite3');
    return new Database(dmmsPath);
  } catch {
    return null;
  }
}

function getDmmsContext(db) {
  try {
    const features = db.prepare(`
      SELECT f.id, f.name, f.status, p.name AS project
      FROM features f JOIN projects p ON p.id = f.project_id
      ORDER BY p.name, f.name
    `).all();

    const tasks = db.prepare(`
      SELECT t.id, t.title, t.status, f.name AS feature
      FROM tasks t LEFT JOIN features f ON f.id = t.feature_id
      WHERE t.status != 'completed'
      ORDER BY t.feature_id LIMIT 50
    `).all();

    const issues = db.prepare(`
      SELECT id, title, severity, status
      FROM issues WHERE status = 'open'
      ORDER BY CASE severity
        WHEN 'critical' THEN 0 WHEN 'high' THEN 1
        WHEN 'medium' THEN 2 ELSE 3 END
      LIMIT 20
    `).all();

    return { features, tasks, issues };
  } catch {
    return { features: [], tasks: [], issues: [] };
  }
}

async function analyzeWithClaude(commitInfo, context) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return null;

  const systemPrompt = `You are a development tracker. Analyze a git commit and return a JSON object describing what should be updated in the project's DMMS (Development Management & Milestone System) database.

DMMS tracks:
- features: name, status (planned/in_progress/completed/blocked)
- tasks: title, status (planned/in_progress/completed), linked to a feature, description
- issues: title, severity (critical/high/medium/low), status (open/resolved), category, description

Return ONLY valid JSON (no markdown fences, no explanation) with these optional keys:
{
  "new_tasks": [{"title": "...", "description": "...", "feature_name": "...", "status": "completed"}],
  "completed_tasks": ["partial or exact task title string"],
  "new_issues": [{"title": "...", "severity": "medium", "category": "...", "description": "..."}],
  "resolved_issues": ["partial or exact issue title string"],
  "feature_updates": [{"name": "feature name", "status": "completed"}]
}

Rules:
- Only include entries where there is clear evidence from the commit diff.
- Prefer completing existing tasks over creating new ones for the same work.
- Keep titles under 80 chars.
- "feature_updates" should only change status if the commit clearly completes or starts a feature.
- If nothing should change, return {}.`;

  const featureLines = context.features
    .map(f => `  [${f.id}] ${f.project}: ${f.name} (${f.status})`)
    .join('\n');
  const taskLines = context.tasks.length
    ? context.tasks.map(t => `  [${t.id}] ${t.feature || 'unlinked'}: ${t.title}`).join('\n')
    : '  (none)';
  const issueLines = context.issues.length
    ? context.issues.map(i => `  [${i.id}] [${i.severity}] ${i.title}`).join('\n')
    : '  (none)';

  const userPrompt = `Current DMMS state:

Features (${context.features.length}):
${featureLines}

Open tasks (${context.tasks.length}):
${taskLines}

Open issues (${context.issues.length}):
${issueLines}

---
Commit: ${commitInfo.hash.slice(0, 8)}
Message: ${commitInfo.message}

Changed files:
${commitInfo.stat}

Diff:
${commitInfo.diff}`;

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 1024,
        system: systemPrompt,
        messages: [{ role: 'user', content: userPrompt }],
      }),
    });

    if (!response.ok) return null;

    const result = await response.json();
    const text = (result?.content?.[0]?.text || '').trim();

    // Extract JSON — strip markdown fences if present
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) return null;

    return JSON.parse(jsonMatch[0]);
  } catch {
    return null;
  }
}

function applyUpdates(db, updates) {
  if (!updates || typeof updates !== 'object') return;

  let changed = 0;

  // Complete existing tasks
  for (const title of (updates.completed_tasks || [])) {
    if (!title) continue;
    const r = db.prepare(
      "UPDATE tasks SET status='completed' WHERE title LIKE ? AND status != 'completed'"
    ).run(`%${title}%`);
    changed += r.changes;
  }

  // Insert new tasks
  for (const task of (updates.new_tasks || [])) {
    if (!task?.title) continue;
    let featureId = null;
    if (task.feature_name) {
      const f = db.prepare("SELECT id FROM features WHERE name LIKE ? LIMIT 1")
        .get(`%${task.feature_name}%`);
      if (f) featureId = f.id;
    }
    db.prepare(
      'INSERT INTO tasks (feature_id, title, status, description) VALUES (?, ?, ?, ?)'
    ).run(featureId, task.title.slice(0, 200), task.status || 'completed', task.description || '');
    changed++;
  }

  // Resolve existing issues
  for (const title of (updates.resolved_issues || [])) {
    if (!title) continue;
    const r = db.prepare(
      "UPDATE issues SET status='resolved' WHERE title LIKE ? AND status='open'"
    ).run(`%${title}%`);
    changed += r.changes;
  }

  // Insert new issues
  for (const issue of (updates.new_issues || [])) {
    if (!issue?.title) continue;
    db.prepare(
      "INSERT INTO issues (title, severity, status, category, description) VALUES (?, ?, 'open', ?, ?)"
    ).run(
      issue.title.slice(0, 200),
      issue.severity || 'medium',
      issue.category || null,
      issue.description || ''
    );
    changed++;
  }

  // Update feature statuses
  for (const f of (updates.feature_updates || [])) {
    if (!f?.name || !f?.status) continue;
    const r = db.prepare("UPDATE features SET status=? WHERE name LIKE ?")
      .run(f.status, `%${f.name}%`);
    changed += r.changes;
  }

  if (changed > 0) {
    process.stderr.write(`[DMMS] Updated ${changed} record(s) from commit ${'\n'}`);
  }
}

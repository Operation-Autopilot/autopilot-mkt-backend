import { createRequire } from 'module'
import { fileURLToPath } from 'url'
import path from 'path'

const _require = createRequire(import.meta.url)
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DB_PATH = path.resolve(__dirname, '..', '..', 'dmms', 'dmms.db')

function respond(res, status, data) {
  res.writeHead(status, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify(data))
}

function getDb() {
  const Database = _require('better-sqlite3')
  return new Database(DB_PATH, { readonly: true })
}

function buildStats(db) {
  return {
    issues: db.prepare('SELECT count(*) AS c FROM issues').get().c,
    tasks: db.prepare('SELECT count(*) AS c FROM tasks').get().c,
    sessions: db.prepare('SELECT count(*) AS c FROM sessions').get().c,
    research: db.prepare('SELECT count(*) AS c FROM research').get().c,
  }
}

function buildHierarchy(db) {
  const tables = db.prepare(
    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('products','projects')"
  ).all()
  if (tables.length < 2) {
    return { products: [], stats: { totalTasks: 0, completedTasks: 0, totalFeatures: 0, totalIssues: 0, resolvedIssues: 0 } }
  }

  const products = db.prepare('SELECT id, name, description, status FROM products ORDER BY id').all()

  for (const product of products) {
    product.projects = db.prepare(
      'SELECT id, name, description, status FROM projects WHERE product_id = ? ORDER BY id'
    ).all(product.id)

    for (const project of product.projects) {
      project.features = db.prepare(
        'SELECT id, name, status FROM features WHERE project_id = ? ORDER BY id'
      ).all(project.id)

      let projectTaskCount = 0
      let projectCompletedTasks = 0

      for (const feature of project.features) {
        const counts = db.prepare(
          "SELECT COUNT(*) AS total, COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) AS completed FROM tasks WHERE feature_id = ?"
        ).get(feature.id)
        feature.taskCount = counts.total
        feature.completedTasks = counts.completed
        projectTaskCount += counts.total
        projectCompletedTasks += counts.completed
      }

      project.taskCount = projectTaskCount
      project.completedTasks = projectCompletedTasks
    }
  }

  const totalTasks = db.prepare('SELECT COUNT(*) AS c FROM tasks').get().c
  const completedTasks = db.prepare("SELECT COUNT(*) AS c FROM tasks WHERE status = 'completed'").get().c
  const totalFeatures = db.prepare('SELECT COUNT(*) AS c FROM features').get().c
  const totalIssues = db.prepare('SELECT COUNT(*) AS c FROM issues').get().c
  const resolvedIssues = db.prepare("SELECT COUNT(*) AS c FROM issues WHERE status IN ('resolved','closed')").get().c

  return {
    generatedAt: new Date().toISOString(),
    products,
    stats: { totalTasks, completedTasks, totalFeatures, totalIssues, resolvedIssues },
  }
}

function buildIssues(db) {
  const total = db.prepare('SELECT count(*) AS c FROM issues').get().c
  const open = db.prepare("SELECT count(*) AS c FROM issues WHERE status IN ('open','in_progress')").get().c
  const resolved = db.prepare("SELECT count(*) AS c FROM issues WHERE status IN ('resolved','closed')").get().c
  const critical = db.prepare("SELECT count(*) AS c FROM issues WHERE severity='critical'").get().c
  const high = db.prepare("SELECT count(*) AS c FROM issues WHERE severity='high'").get().c
  const medium = db.prepare("SELECT count(*) AS c FROM issues WHERE severity='medium'").get().c
  const low = db.prepare("SELECT count(*) AS c FROM issues WHERE severity='low'").get().c

  const openRows = db.prepare(
    "SELECT id, title, severity, category, files, description FROM issues WHERE status IN ('open','in_progress') ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, id"
  ).all()

  const resolvedRows = db.prepare(
    "SELECT id, title, severity, category, files, description FROM issues WHERE status IN ('resolved','closed') ORDER BY id"
  ).all()

  return { total, open, resolved, critical, high, medium, low, openRows, resolvedRows }
}

function buildSprints(db) {
  const tasks = db.prepare(
    'SELECT id, sprint, title, status, description FROM tasks ORDER BY sprint, id'
  ).all()

  const groupMap = new Map()
  for (const t of tasks) {
    const key = t.sprint || 'unassigned'
    if (!groupMap.has(key)) groupMap.set(key, [])
    groupMap.get(key).push(t)
  }

  const sprints = []
  for (const [name, sprintTasks] of groupMap) {
    sprints.push({ name, tasks: sprintTasks })
  }

  return { sprints }
}

function buildSessions(db) {
  return {
    rows: db.prepare(
      'SELECT created_at, session_type, summary, issues_logged, tasks_created FROM sessions ORDER BY created_at DESC'
    ).all(),
  }
}

function buildResearch(db) {
  const rows = db.prepare(
    'SELECT topic, section, subsection, confidence, source FROM research ORDER BY section, id'
  ).all()

  const groupMap = new Map()
  for (const r of rows) {
    const key = r.section || 'Uncategorized'
    if (!groupMap.has(key)) groupMap.set(key, [])
    groupMap.get(key).push(r)
  }

  const groups = []
  for (const [section, items] of groupMap) {
    groups.push({ section, items })
  }

  return { groups }
}

export function dmmsApiPlugin() {
  return {
    name: 'vitepress-dmms-api',
    configureServer(server) {
      server.middlewares.use('/_dmms', (req, res, next) => {
        let db
        try {
          db = getDb()
        } catch (e) {
          return respond(res, 503, { error: 'DB unavailable' })
        }
        try {
          const route = req.url?.split('?')[0] ?? '/'
          if (route === '/stats' || route === '' || route === '/') {
            return respond(res, 200, buildStats(db))
          }
          if (route === '/hierarchy') {
            return respond(res, 200, buildHierarchy(db))
          }
          if (route === '/issues') {
            return respond(res, 200, buildIssues(db))
          }
          if (route === '/sprints') {
            return respond(res, 200, buildSprints(db))
          }
          if (route === '/sessions') {
            return respond(res, 200, buildSessions(db))
          }
          if (route === '/research') {
            return respond(res, 200, buildResearch(db))
          }
          next()
        } catch (e) {
          respond(res, 500, { error: e.message })
        } finally {
          db?.close()
        }
      })
    },
  }
}

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const STATS_PATH = path.resolve(__dirname, '..', 'data', 'project-stats.json')

const FALLBACK = {
  generatedAt: null,
  dmms: { issues: 0, tasks: 0, sessions: 0, research: 0 },
  backend: { routeFiles: 0, serviceFiles: 0, schemaFiles: 0, modelFiles: 0, coreFiles: 0, serviceInventory: [] },
  frontend: { componentFiles: 0, hookFiles: 0, stateFiles: 0 },
  tests: { totalTestFiles: 0, totalTestLines: 0, testCaseCount: 0 },
}

export default {
  load() {
    if (!fs.existsSync(STATS_PATH)) return FALLBACK
    try {
      return JSON.parse(fs.readFileSync(STATS_PATH, 'utf-8'))
    } catch {
      return FALLBACK
    }
  },
}

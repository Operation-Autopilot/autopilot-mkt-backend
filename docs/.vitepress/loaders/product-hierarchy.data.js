import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const HIERARCHY_PATH = path.resolve(__dirname, '..', 'data', 'product-hierarchy.json')

const FALLBACK = {
  generatedAt: null,
  products: [],
  stats: {
    totalTasks: 0,
    completedTasks: 0,
    totalFeatures: 0,
    totalIssues: 0,
    resolvedIssues: 0,
  },
}

export default {
  load() {
    if (!fs.existsSync(HIERARCHY_PATH)) return FALLBACK
    try {
      return JSON.parse(fs.readFileSync(HIERARCHY_PATH, 'utf-8'))
    } catch {
      return FALLBACK
    }
  },
}

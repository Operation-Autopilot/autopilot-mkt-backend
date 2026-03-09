#!/usr/bin/env node

/**
 * migrate-dmms-hierarchy.mjs
 *
 * Creates the DMMS database from scratch with product/project hierarchy
 * for the Autopilot Marketplace documentation site.
 *
 * Usage:
 *   node scripts/migrate-dmms-hierarchy.mjs
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

function main() {
  fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });

  const db = new Database(DB_PATH);
  console.log('Creating DMMS database...');

  const migrate = db.transaction(() => {
    // -------------------------------------------------------------------
    // 1. Create all tables
    // -------------------------------------------------------------------
    console.log('  Creating tables...');

    db.exec(`
      CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL REFERENCES products(id),
        name TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'planned',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS features (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER REFERENCES projects(id),
        name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'planned',
        priority INTEGER DEFAULT 3,
        description TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        feature_id INTEGER REFERENCES features(id),
        sprint TEXT,
        title TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'planned',
        description TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        severity TEXT NOT NULL DEFAULT 'medium',
        status TEXT NOT NULL DEFAULT 'open',
        category TEXT,
        files TEXT,
        description TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_type TEXT,
        summary TEXT,
        issues_logged INTEGER DEFAULT 0,
        tasks_created INTEGER DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS research (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        section TEXT,
        subsection TEXT,
        confidence TEXT DEFAULT 'medium',
        source TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
    `);

    // -------------------------------------------------------------------
    // 2. Seed product
    // -------------------------------------------------------------------
    console.log('  Seeding product...');
    const productExists = db.prepare('SELECT COUNT(*) AS c FROM products WHERE id = 1').get();
    if (productExists.c === 0) {
      db.prepare(`
        INSERT INTO products (id, name, description, status) VALUES (?, ?, ?, ?)
      `).run(
        1,
        'Autopilot Marketplace',
        'Agent-led procurement platform for enterprise buyers evaluating robotic cleaning solutions',
        'active'
      );
    }

    // -------------------------------------------------------------------
    // 3. Seed projects
    // -------------------------------------------------------------------
    console.log('  Seeding projects...');
    const projectExists = db.prepare('SELECT COUNT(*) AS c FROM projects').get();
    if (projectExists.c === 0) {
      const insertProject = db.prepare(`
        INSERT INTO projects (product_id, name, description, status) VALUES (?, ?, ?, ?)
      `);
      insertProject.run(1, 'Frontend (React SPA)', 'React 18 + TypeScript + Vite frontend with AI chat, ROI visualization, and checkout', 'active');
      insertProject.run(1, 'Backend (FastAPI API)', 'Python FastAPI backend with Supabase, OpenAI, Pinecone, and Stripe integrations', 'active');
      console.log('    Inserted 2 projects');
    }

    // -------------------------------------------------------------------
    // 4. Seed features
    // -------------------------------------------------------------------
    console.log('  Seeding features...');
    const featureExists = db.prepare('SELECT COUNT(*) AS c FROM features').get();
    if (featureExists.c === 0) {
      const insertFeature = db.prepare(`
        INSERT INTO features (project_id, name, status, priority, description) VALUES (?, ?, ?, ?, ?)
      `);

      // Backend features (project_id = 2)
      insertFeature.run(2, 'Authentication', 'completed', 1, 'JWT auth via Supabase with signup, login, password reset');
      insertFeature.run(2, 'Checkout & Stripe', 'completed', 1, 'Stripe checkout sessions, order management, webhooks');
      insertFeature.run(2, 'Conversations', 'completed', 1, 'Conversation CRUD with OpenAI GPT-4o agent integration');
      insertFeature.run(2, 'Core Infrastructure', 'completed', 1, 'FastAPI app, config, Supabase/OpenAI/Pinecone clients, health checks');
      insertFeature.run(2, 'Profiles & Companies', 'completed', 2, 'User profiles, company accounts, member management, invitations');
      insertFeature.run(2, 'RAG Integration', 'completed', 2, 'Pinecone vector search for product recommendations');
      insertFeature.run(2, 'Sessions & Discovery', 'completed', 2, 'Anonymous session management and discovery profile storage');

      // Frontend features (project_id = 1)
      insertFeature.run(1, 'UI Phase System', 'completed', 1, 'Discovery → ROI → Greenlight phase transitions');
      insertFeature.run(1, 'State Management', 'completed', 1, 'SessionContext, AuthContext, React Query hooks');
      insertFeature.run(1, 'Mobile Responsive', 'completed', 2, 'MobileBottomSheet, ChatFAB, breakpoint detection');

      console.log('    Inserted 10 features');
    }

    // -------------------------------------------------------------------
    // 5. Seed tasks from spec areas
    // -------------------------------------------------------------------
    console.log('  Seeding tasks...');
    const taskExists = db.prepare('SELECT COUNT(*) AS c FROM tasks').get();
    if (taskExists.c === 0) {
      const insertTask = db.prepare(`
        INSERT INTO tasks (feature_id, sprint, title, status, description) VALUES (?, ?, ?, ?, ?)
      `);

      // Auth tasks (feature 1)
      insertTask.run(1, 'mvp-auth', 'JWT verification middleware', 'completed', 'Verify Supabase JWT tokens on protected routes');
      insertTask.run(1, 'mvp-auth', 'Signup endpoint', 'completed', 'POST /api/v1/auth/signup');
      insertTask.run(1, 'mvp-auth', 'Login endpoint', 'completed', 'POST /api/v1/auth/login');
      insertTask.run(1, 'mvp-auth', 'Password reset flow', 'completed', 'Password reset request and confirmation');
      insertTask.run(1, 'mvp-auth', 'Token refresh endpoint', 'completed', 'POST /api/v1/auth/refresh');

      // Checkout tasks (feature 2)
      insertTask.run(2, 'mvp-checkout', 'Robot catalog endpoint', 'completed', 'GET /api/v1/robots with filters');
      insertTask.run(2, 'mvp-checkout', 'Stripe checkout session', 'completed', 'Create Stripe checkout session for robot lease');
      insertTask.run(2, 'mvp-checkout', 'Order management', 'completed', 'Order CRUD and status tracking');
      insertTask.run(2, 'mvp-checkout', 'Webhook handler', 'completed', 'Process Stripe webhook events');
      insertTask.run(2, 'mvp-checkout', 'Test account support', 'completed', 'Stripe test mode for test accounts in production');

      // Conversations tasks (feature 3)
      insertTask.run(3, 'mvp-conversations', 'Conversation CRUD', 'completed', 'Create, read, list conversations');
      insertTask.run(3, 'mvp-conversations', 'Message endpoints', 'completed', 'Send and list messages within conversations');
      insertTask.run(3, 'mvp-conversations', 'Agent integration', 'completed', 'OpenAI GPT-4o agent for conversation responses');
      insertTask.run(3, 'mvp-conversations', 'Context reconstruction', 'completed', 'Rebuild conversation context for agent');
      insertTask.run(3, 'mvp-conversations', 'Profile extraction', 'completed', 'Extract discovery profile from conversation using structured output');
      insertTask.run(3, 'mvp-conversations', 'Phase tracking', 'completed', 'Track conversation phase (discovery/roi/greenlight)');

      // Core infra tasks (feature 4)
      insertTask.run(4, 'mvp-core', 'FastAPI app setup', 'completed', 'Main app with CORS, middleware, router mounting');
      insertTask.run(4, 'mvp-core', 'Configuration module', 'completed', 'Environment-based config with validation');
      insertTask.run(4, 'mvp-core', 'Supabase client', 'completed', 'Two-client pattern (singleton + auth)');
      insertTask.run(4, 'mvp-core', 'OpenAI client', 'completed', 'OpenAI client singleton');
      insertTask.run(4, 'mvp-core', 'Pinecone client', 'completed', 'Pinecone client singleton');
      insertTask.run(4, 'mvp-core', 'Health check endpoints', 'completed', 'GET /health and /api/v1/health');
      insertTask.run(4, 'mvp-core', 'Error handling middleware', 'completed', 'Standardized error responses');
      insertTask.run(4, 'mvp-core', 'Docker setup', 'completed', 'Dockerfile and docker-compose for deployment');

      // Profiles tasks (feature 5)
      insertTask.run(5, 'mvp-profiles', 'Profile CRUD', 'completed', 'User profile create/read/update');
      insertTask.run(5, 'mvp-profiles', 'Company management', 'completed', 'Company CRUD with owner/member roles');
      insertTask.run(5, 'mvp-profiles', 'Invitation system', 'completed', 'Company member invitations');

      // RAG tasks (feature 6)
      insertTask.run(6, 'mvp-rag', 'Pinecone integration', 'completed', 'Vector database connection and querying');
      insertTask.run(6, 'mvp-rag', 'Product indexing', 'completed', 'Index robot products with embeddings');
      insertTask.run(6, 'mvp-rag', 'Context injection', 'completed', 'Inject relevant products into agent prompts');

      // Sessions tasks (feature 7)
      insertTask.run(7, 'mvp-sessions', 'Anonymous sessions', 'completed', 'Session CRUD for unauthenticated users');
      insertTask.run(7, 'mvp-sessions', 'Discovery profiles', 'completed', 'Store discovery data per session');
      insertTask.run(7, 'mvp-sessions', 'Session-to-user linking', 'completed', 'Link anonymous session to authenticated user');

      // Frontend tasks (features 8-10)
      insertTask.run(8, 'mvp-ui', 'Phase routing', 'completed', 'Discovery → ROI → Greenlight transitions');
      insertTask.run(8, 'mvp-ui', 'Agent chat component', 'completed', 'AgentChat with message display and input');
      insertTask.run(8, 'mvp-ui', 'ROI visualization', 'completed', 'ROIView with savings calculations');
      insertTask.run(8, 'mvp-ui', 'Greenlight view', 'completed', 'GreenlightView with Stripe checkout');
      insertTask.run(8, 'mvp-ui', 'Robot marketplace', 'completed', 'RobotMarketplace with filters and cards');

      insertTask.run(9, 'mvp-state', 'SessionContext', 'completed', 'Phase, answers, robot selection state');
      insertTask.run(9, 'mvp-state', 'AuthContext', 'completed', 'Auth state with Supabase integration');
      insertTask.run(9, 'mvp-state', 'React Query setup', 'completed', 'QueryProvider with default config');

      insertTask.run(10, 'mvp-mobile', 'MobileBottomSheet', 'completed', 'Slide-up chat overlay');
      insertTask.run(10, 'mvp-mobile', 'ChatFAB', 'completed', 'Floating action button with unread badge');
      insertTask.run(10, 'mvp-mobile', 'Mobile tab navigation', 'completed', 'MobileTabBar for view switching');

      console.log('    Inserted tasks');
    }

    // -------------------------------------------------------------------
    // 6. Seed one audit session
    // -------------------------------------------------------------------
    console.log('  Seeding initial session...');
    const sessionExists = db.prepare('SELECT COUNT(*) AS c FROM sessions').get();
    if (sessionExists.c === 0) {
      db.prepare(`
        INSERT INTO sessions (session_type, summary, issues_logged, tasks_created, created_at)
        VALUES (?, ?, ?, ?, ?)
      `).run('initial-setup', 'DMMS database created with product hierarchy, features, and MVP tasks', 0, 43, datetime());
    }
  });

  migrate();

  // Verify
  console.log('\nVerification:');
  const products = db.prepare('SELECT id, name, status FROM products').all();
  console.log(`  Products: ${products.length}`);
  for (const p of products) console.log(`    ${p.id}. ${p.name} (${p.status})`);

  const projects = db.prepare('SELECT id, name, status, product_id FROM projects').all();
  console.log(`  Projects: ${projects.length}`);
  for (const p of projects) console.log(`    ${p.id}. ${p.name} (${p.status})`);

  const features = db.prepare('SELECT id, name, status, project_id FROM features').all();
  console.log(`  Features: ${features.length}`);
  for (const f of features) console.log(`    ${f.id}. ${f.name} → project ${f.project_id} (${f.status})`);

  const taskCount = db.prepare('SELECT COUNT(*) AS c FROM tasks').get().c;
  console.log(`  Tasks: ${taskCount}`);

  db.close();
  console.log('\nMigration complete.');
}

function datetime() {
  return new Date().toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
}

main();

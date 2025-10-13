/**
 * SQLite-based session management with idempotency
 * Handles persistence and prevents duplicate task creation
 */

import sqlite3 from 'sqlite3';
import crypto from 'crypto';
import { Session, ParsedTask } from '../types/core';

export class SessionService {
  private db: sqlite3.Database;
  
  constructor(dbPath: string = './flowcoach.db') {
    this.db = new sqlite3.Database(dbPath);
    this.initializeTables();
  }
  
  private initializeTables(): void {
    const createSessionsTable = `
      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        input_text TEXT NOT NULL,
        parsed_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_task_ids TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
      )
    `;
    
    const createTasksTable = `
      CREATE TABLE IF NOT EXISTS created_tasks (
        session_id TEXT NOT NULL,
        title_hash TEXT NOT NULL,
        todoist_id TEXT,
        task_data TEXT,
        created_at INTEGER NOT NULL,
        PRIMARY KEY (session_id, title_hash),
        FOREIGN KEY (session_id) REFERENCES sessions(id)
      )
    `;
    
    const createIndexes = `
      CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
      CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
      CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at);
    `;
    
    this.db.serialize(() => {
      this.db.run(createSessionsTable);
      this.db.run(createTasksTable);
      this.db.run(createIndexes);
    });
  }
  
  /**
   * Create a new session
   */
  async createSession(userId: string, inputText: string, parsed: ParsedTask[]): Promise<Session> {
    const session: Session = {
      id: this.generateSessionId(),
      userId,
      inputText,
      parsed,
      status: 'pending',
      createdAt: Date.now(),
      updatedAt: Date.now()
    };
    
    return new Promise((resolve, reject) => {
      const stmt = this.db.prepare(`
        INSERT INTO sessions (id, user_id, input_text, parsed_json, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
      `);
      
      stmt.run([
        session.id,
        session.userId,
        session.inputText,
        JSON.stringify(session.parsed),
        session.status,
        session.createdAt,
        session.updatedAt
      ], function(err) {
        if (err) {
          reject(err);
        } else {
          resolve(session);
        }
      });
      
      stmt.finalize();
    });
  }
  
  /**
   * Update session status and add created task IDs
   */
  async updateSession(sessionId: string, status: Session['status'], createdTaskIds?: string[]): Promise<void> {
    return new Promise((resolve, reject) => {
      const stmt = this.db.prepare(`
        UPDATE sessions 
        SET status = ?, created_task_ids = ?, updated_at = ?
        WHERE id = ?
      `);
      
      stmt.run([
        status,
        createdTaskIds ? JSON.stringify(createdTaskIds) : null,
        Date.now(),
        sessionId
      ], function(err) {
        if (err) {
          reject(err);
        } else {
          resolve();
        }
      });
      
      stmt.finalize();
    });
  }
  
  /**
   * Get the last pending session for a user
   */
  async getLastPendingSession(userId: string): Promise<Session | null> {
    return new Promise((resolve, reject) => {
      this.db.get(`
        SELECT * FROM sessions 
        WHERE user_id = ? AND status = 'pending'
        ORDER BY updated_at DESC 
        LIMIT 1
      `, [userId], (err, row: any) => {
        if (err) {
          reject(err);
        } else if (row) {
          resolve(this.rowToSession(row));
        } else {
          resolve(null);
        }
      });
    });
  }
  
  /**
   * Get session by ID
   */
  async getSession(sessionId: string): Promise<Session | null> {
    return new Promise((resolve, reject) => {
      this.db.get(`
        SELECT * FROM sessions WHERE id = ?
      `, [sessionId], (err, row: any) => {
        if (err) {
          reject(err);
        } else if (row) {
          resolve(this.rowToSession(row));
        } else {
          resolve(null);
        }
      });
    });
  }
  
  /**
   * Check if a task was already created to prevent duplicates
   */
  async isTaskAlreadyCreated(sessionId: string, task: ParsedTask): Promise<boolean> {
    const hash = this.generateTaskHash(task, sessionId);
    
    return new Promise((resolve, reject) => {
      this.db.get(`
        SELECT 1 FROM created_tasks 
        WHERE session_id = ? AND title_hash = ?
      `, [sessionId, hash], (err, row) => {
        if (err) {
          reject(err);
        } else {
          resolve(!!row);
        }
      });
    });
  }
  
  /**
   * Record that a task was created
   */
  async recordTaskCreated(sessionId: string, task: ParsedTask, todoistId?: string): Promise<void> {
    const hash = this.generateTaskHash(task, sessionId);
    
    return new Promise((resolve, reject) => {
      const stmt = this.db.prepare(`
        INSERT OR REPLACE INTO created_tasks 
        (session_id, title_hash, todoist_id, task_data, created_at)
        VALUES (?, ?, ?, ?, ?)
      `);
      
      stmt.run([
        sessionId,
        hash,
        todoistId || null,
        JSON.stringify(task),
        Date.now()
      ], function(err) {
        if (err) {
          reject(err);
        } else {
          resolve();
        }
      });
      
      stmt.finalize();
    });
  }
  
  /**
   * Get user session history
   */
  async getUserSessions(userId: string, limit: number = 10): Promise<Session[]> {
    return new Promise((resolve, reject) => {
      this.db.all(`
        SELECT * FROM sessions 
        WHERE user_id = ?
        ORDER BY updated_at DESC 
        LIMIT ?
      `, [userId, limit], (err, rows: any[]) => {
        if (err) {
          reject(err);
        } else {
          resolve(rows.map(row => this.rowToSession(row)));
        }
      });
    });
  }
  
  /**
   * Clean up old sessions (keep last 50 per user)
   */
  async cleanupOldSessions(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.db.run(`
        DELETE FROM sessions 
        WHERE id NOT IN (
          SELECT id FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY updated_at DESC) as rn
            FROM sessions
          ) WHERE rn <= 50
        )
      `, (err) => {
        if (err) {
          reject(err);
        } else {
          resolve();
        }
      });
    });
  }
  
  private generateSessionId(): string {
    return `fc_${Date.now()}_${crypto.randomBytes(4).toString('hex')}`;
  }
  
  private generateTaskHash(task: ParsedTask, sessionId: string): string {
    const content = `${sessionId}:${task.title}:${task.duration_bucket}`;
    return crypto.createHash('md5').update(content).digest('hex');
  }
  
  private rowToSession(row: any): Session {
    return {
      id: row.id,
      userId: row.user_id,
      inputText: row.input_text,
      parsed: JSON.parse(row.parsed_json),
      status: row.status,
      createdTaskIds: row.created_task_ids ? JSON.parse(row.created_task_ids) : undefined,
      createdAt: row.created_at,
      updatedAt: row.updated_at
    };
  }
  
  /**
   * Clear all pending sessions for a user
   */
  async clearAllPendingSessions(userId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.db.run(`
        UPDATE sessions SET status = 'discarded', updated_at = ?
        WHERE user_id = ? AND status = 'pending'
      `, [Date.now(), userId], function(err) {
        if (err) {
          reject(err);
        } else {
          console.log(`Cleared ${this.changes} pending sessions for user ${userId}`);
          resolve();
        }
      });
    });
  }

  /**
   * Close database connection
   */
  close(): void {
    this.db.close();
  }
}
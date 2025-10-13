/**
 * Thread state service for conversation memory
 */

import { Database } from 'sqlite3';
import { ThreadState, ThreadStateUpdate } from '../types/threadState';

export class ThreadStateService {
  private db: Database;
  private stateCache: Map<string, ThreadState> = new Map();
  private readonly EXPIRY_MS = 30 * 60 * 1000; // 30 minutes
  
  constructor(dbPath?: string) {
    this.db = new Database(dbPath || ':memory:');
    this.initialize();
  }
  
  private initialize(): void {
    const createTable = `
      CREATE TABLE IF NOT EXISTS thread_state (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        channel_id TEXT NOT NULL,
        last_intent TEXT,
        last_created_task_id TEXT,
        last_session_id TEXT,
        last_task_title TEXT,
        last_topic TEXT,
        context TEXT,
        updated_at INTEGER NOT NULL,
        UNIQUE(user_id, channel_id)
      )
    `;
    
    const createIndex = `
      CREATE INDEX IF NOT EXISTS idx_thread_state_user_channel 
      ON thread_state(user_id, channel_id);
    `;
    
    this.db.serialize(() => {
      this.db.run(createTable);
      this.db.run(createIndex);
    });
  }
  
  private getThreadKey(userId: string, channelId: string): string {
    return `${userId}:${channelId}`;
  }
  
  async getThreadState(userId: string, channelId: string): Promise<ThreadState | null> {
    const key = this.getThreadKey(userId, channelId);
    
    // Check cache first
    const cached = this.stateCache.get(key);
    if (cached) {
      // Check if expired
      if (Date.now() - cached.updatedAt > this.EXPIRY_MS) {
        this.stateCache.delete(key);
        await this.clearThreadState(userId, channelId);
        return null;
      }
      return cached;
    }
    
    // Load from DB
    return new Promise((resolve, reject) => {
      this.db.get(`
        SELECT * FROM thread_state 
        WHERE user_id = ? AND channel_id = ?
      `, [userId, channelId], (err, row: any) => {
        if (err) {
          reject(err);
        } else if (row) {
          const state: ThreadState = {
            userId: row.user_id,
            channelId: row.channel_id,
            lastIntent: row.last_intent,
            lastCreatedTaskId: row.last_created_task_id,
            lastSessionId: row.last_session_id,
            lastTaskTitle: row.last_task_title,
            lastTopic: row.last_topic,
            context: row.context ? JSON.parse(row.context) : undefined,
            updatedAt: row.updated_at
          };
          
          // Check expiry
          if (Date.now() - state.updatedAt > this.EXPIRY_MS) {
            this.clearThreadState(userId, channelId);
            resolve(null);
          } else {
            this.stateCache.set(key, state);
            resolve(state);
          }
        } else {
          resolve(null);
        }
      });
    });
  }
  
  async updateThreadState(
    userId: string, 
    channelId: string, 
    update: ThreadStateUpdate
  ): Promise<void> {
    const key = this.getThreadKey(userId, channelId);
    const now = Date.now();
    
    // Get existing state
    const existing = await this.getThreadState(userId, channelId);
    
    const newState: ThreadState = {
      userId,
      channelId,
      lastIntent: update.lastIntent !== undefined ? update.lastIntent : existing?.lastIntent || null,
      lastCreatedTaskId: update.lastCreatedTaskId !== undefined ? update.lastCreatedTaskId : existing?.lastCreatedTaskId,
      lastSessionId: update.lastSessionId !== undefined ? update.lastSessionId : existing?.lastSessionId,
      lastTaskTitle: update.lastTaskTitle !== undefined ? update.lastTaskTitle : existing?.lastTaskTitle,
      lastTopic: update.lastTopic !== undefined ? update.lastTopic : existing?.lastTopic || null,
      context: update.context !== undefined ? update.context : existing?.context,
      updatedAt: now
    };
    
    // Update cache
    this.stateCache.set(key, newState);
    
    // Update DB
    return new Promise((resolve, reject) => {
      this.db.run(`
        INSERT OR REPLACE INTO thread_state (
          id, user_id, channel_id, last_intent, last_created_task_id,
          last_session_id, last_task_title, last_topic, context, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `, [
        key,
        userId,
        channelId,
        newState.lastIntent,
        newState.lastCreatedTaskId,
        newState.lastSessionId,
        newState.lastTaskTitle,
        newState.lastTopic,
        newState.context ? JSON.stringify(newState.context) : null,
        now
      ], (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }
  
  async clearThreadState(userId: string, channelId: string): Promise<void> {
    const key = this.getThreadKey(userId, channelId);
    this.stateCache.delete(key);
    
    return new Promise((resolve, reject) => {
      this.db.run(`
        DELETE FROM thread_state 
        WHERE user_id = ? AND channel_id = ?
      `, [userId, channelId], (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }
  
  close(): void {
    this.db.close();
  }
}
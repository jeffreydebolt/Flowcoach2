/**
 * Thread state types for conversation memory
 */

export interface ThreadState {
  userId: string;
  channelId: string;
  lastIntent: 'organize' | 'gtd_help' | 'calendar_check' | 'prioritize' | 'task_created' | 'task_updated' | null;
  lastCreatedTaskId?: string;  // Todoist task ID
  lastSessionId?: string;       // Session ID for organize flow
  lastTaskTitle?: string;       // For "actually make that 45 mins"
  lastTopic?: 'GTD' | 'Calendar' | 'Todoist' | null;
  context?: any;                // Flexible context object
  updatedAt: number;
}

export interface ThreadStateUpdate {
  lastIntent?: ThreadState['lastIntent'];
  lastCreatedTaskId?: string;
  lastSessionId?: string;
  lastTaskTitle?: string;
  lastTopic?: ThreadState['lastTopic'];
  context?: any;
}
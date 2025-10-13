/**
 * Core data types for FlowCoach v2
 * Following the build brief specifications
 */

export type DurationBucket = '2min' | '10min' | '30plus' | null;

export interface ParsedTask {
  raw: string;                 // original line
  title: string;               // cleaned title (no numbering/bullets)
  explicit_minutes?: number;   // if specified by user, e.g., 20
  duration_bucket: DurationBucket;
  is_project_candidate: boolean;
  subtasks?: ParsedTask[];     // only when breakdown requested
}

export interface Session {
  id: string;
  userId: string;
  inputText: string;
  parsed: ParsedTask[];
  status: 'pending' | 'accepted' | 'pushed' | 'discarded';
  createdTaskIds?: string[];   // Todoist IDs
  createdAt: number;
  updatedAt: number;
}

export interface TimeParseResult {
  explicit_minutes?: number;
  duration_bucket: DurationBucket;
  cleaned_text: string;
  matched_expression?: string; // The time expression we extracted (for Claude context)
}

export interface UserContext {
  timezone?: string;           // "America/New_York"
  workHours?: { start: number; end: number }; // 9, 17
  defaultProject?: string;     // Todoist project ID
  labelMode?: 'labels' | 'prefix'; // @t_2min vs [2min]
}

export interface CalendarSuggestion {
  free_minutes: number;
  next_event_start?: Date;
  suggested_tasks: ParsedTask[];
  message: string;
}

export interface TodoistTask {
  id: string;
  content: string;
  project_id: string;
  labels?: string[];
  parent_id?: string;
  due?: {
    date: string;
    datetime?: string;
  };
}

export interface FlowCoachResponse {
  type: 'preview' | 'success' | 'error' | 'suggestion' | 'needs_time' | 'warning';
  message: string;
  data?: {
    session?: Session;
    tasks?: ParsedTask[];
    suggestion?: CalendarSuggestion;
  };
  actions?: string[]; // Available follow-up commands
}
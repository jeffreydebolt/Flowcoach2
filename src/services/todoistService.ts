/**
 * Todoist integration with label/prefix support
 * Handles graceful degradation and idempotency
 */

import axios, { AxiosInstance } from 'axios';
import { ParsedTask, DurationBucket, TodoistTask, UserContext } from '../types/core';

export class TodoistService {
  private client: AxiosInstance;
  private config: UserContext;
  
  constructor(apiToken: string, config: UserContext = {}) {
    this.client = axios.create({
      baseURL: 'https://api.todoist.com/rest/v2',
      headers: {
        'Authorization': `Bearer ${apiToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    this.config = {
      labelMode: 'labels', // prefer labels over prefixes
      defaultProject: undefined,
      ...config
    };
  }
  
  /**
   * Create tasks in Todoist with proper formatting
   */
  async createTasks(tasks: ParsedTask[], sessionId: string): Promise<{ 
    created: TodoistTask[]; 
    failed: ParsedTask[]; 
    offline: boolean 
  }> {
    const created: TodoistTask[] = [];
    const failed: ParsedTask[] = [];
    let offline = false;
    
    try {
      // Test connection first
      await this.testConnection();
      
      // Create tasks one by one (Todoist doesn't have batch create)
      for (const task of tasks) {
        try {
          const todoistTask = await this.createSingleTask(task);
          created.push(todoistTask);
          
          // Create subtasks if they exist
          if (task.subtasks) {
            for (const subtask of task.subtasks) {
              try {
                const childTask = await this.createSingleTask(subtask, todoistTask.id);
                created.push(childTask);
              } catch (error) {
                console.error(`Failed to create subtask: ${subtask.title}`, error);
                failed.push(subtask);
              }
            }
          }
          
        } catch (error) {
          console.error(`Failed to create task: ${task.title}`, error);
          failed.push(task);
        }
      }
      
    } catch (connectionError) {
      console.error('Todoist connection failed:', connectionError);
      offline = true;
      failed.push(...tasks);
    }
    
    return { created, failed, offline };
  }
  
  /**
   * Create a single task
   */
  private async createSingleTask(task: ParsedTask, parentId?: string): Promise<TodoistTask> {
    const content = this.formatTaskContent(task);
    const labels = this.getTaskLabels(task);
    
    const payload: any = {
      content,
      project_id: this.config.defaultProject
    };
    
    if (labels.length > 0 && this.config.labelMode === 'labels') {
      payload.labels = labels;
    }
    
    if (parentId) {
      payload.parent_id = parentId;
    }
    
    const response = await this.client.post('/tasks', payload);
    
    return {
      id: response.data.id,
      content: response.data.content,
      project_id: response.data.project_id,
      labels: response.data.labels,
      parent_id: response.data.parent_id
    };
  }
  
  /**
   * Format task content based on label mode
   */
  private formatTaskContent(task: ParsedTask): string {
    if (this.config.labelMode === 'prefix' && task.duration_bucket) {
      return `[${task.duration_bucket}] ${task.title}`;
    }
    
    return task.title;
  }
  
  /**
   * Get appropriate labels for a task
   */
  private getTaskLabels(task: ParsedTask): string[] {
    if (this.config.labelMode !== 'labels' || !task.duration_bucket) {
      return [];
    }
    
    const labelMap: Record<string, string> = {
      '2min': 't_2min',
      '10min': 't_10min',
      '30plus': 't_30plus'
    };
    
    const label = task.duration_bucket ? labelMap[task.duration_bucket] : null;
    return label ? [label] : [];
  }
  
  /**
   * Test Todoist connection
   */
  private async testConnection(): Promise<void> {
    await this.client.get('/projects');
  }
  
  /**
   * Get available projects for configuration
   */
  async getProjects(): Promise<Array<{ id: string; name: string }>> {
    try {
      const response = await this.client.get('/projects');
      return response.data.map((project: any) => ({
        id: project.id,
        name: project.name
      }));
    } catch (error) {
      console.error('Failed to fetch projects:', error);
      return [];
    }
  }
  
  /**
   * Get or create time duration labels
   */
  async ensureTimeLabels(): Promise<void> {
    if (this.config.labelMode !== 'labels') return;
    
    try {
      const response = await this.client.get('/labels');
      const existingLabels = response.data.map((label: any) => label.name);
      
      const requiredLabels = ['t_2min', 't_10min', 't_30plus'];
      const missingLabels = requiredLabels.filter(label => !existingLabels.includes(label));
      
      // Create missing labels
      for (const labelName of missingLabels) {
        await this.client.post('/labels', {
          name: labelName,
          color: this.getLabelColor(labelName)
        });
      }
      
    } catch (error) {
      console.warn('Failed to ensure time labels exist:', error);
      // Fallback to prefix mode
      this.config.labelMode = 'prefix';
    }
  }
  
  private getLabelColor(labelName: string): string {
    const colorMap: Record<string, string> = {
      't_2min': 'green',     // Quick wins
      't_10min': 'yellow',   // Medium tasks  
      't_30plus': 'red'      // Projects
    };
    
    return colorMap[labelName] || 'grey';
  }
  
  /**
   * Update a task in Todoist
   */
  async updateTask(taskId: string, updates: { content?: string; due?: any; labels?: string[] }): Promise<void> {
    try {
      await this.client.post(`/tasks/${taskId}`, updates);
    } catch (error: any) {
      console.error('Failed to update task:', error);
      throw error;
    }
  }

  /**
   * Get tasks from Todoist
   */
  async getTasks(): Promise<TodoistTask[]> {
    try {
      console.log('DEBUG: Making Todoist API call to /tasks');
      const response = await this.client.get('/tasks');
      console.log('DEBUG: Todoist API response:', response.status, response.data?.length, 'tasks');
      return response.data;
    } catch (error: any) {
      console.error('Failed to fetch tasks:', error);
      if (error.response) {
        console.error('Response status:', error.response.status);
        console.error('Response data:', error.response.data);
      }
      return [];
    }
  }

  /**
   * Update service configuration
   */
  updateConfig(config: Partial<UserContext>): void {
    this.config = { ...this.config, ...config };
  }
}
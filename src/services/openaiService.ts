/**
 * OpenAI integration - restoring what was working
 */

import OpenAI from 'openai';
import { ParsedTask } from '../types/core';
import { parseTime, cleanTaskTitle } from '../parsers/timeParser';

export class OpenAIService {
  private client: OpenAI;
  
  constructor(apiKey: string) {
    this.client = new OpenAI({ apiKey });
  }
  
  async parseAndClassify(inputText: string): Promise<ParsedTask[]> {
    // First do deterministic parsing
    const lines = this.extractLines(inputText);
    const tasks: ParsedTask[] = [];
    
    for (const line of lines) {
      const timeResult = parseTime(line);
      const title = cleanTaskTitle(timeResult.cleaned_text);
      
      tasks.push({
        raw: line,
        title: title,
        explicit_minutes: timeResult.explicit_minutes,
        duration_bucket: timeResult.duration_bucket,
        is_project_candidate: timeResult.duration_bucket === '30plus'
      });
    }
    
    return tasks;
  }
  
  async breakdownProject(task: ParsedTask): Promise<ParsedTask> {
    const prompt = `Break down this task into 3-6 subtasks: "${task.title}"
Each subtask should be specific and actionable.
Return as JSON array with {title: string, duration_bucket: "2min"|"10min"|"30plus"}`;

    const response = await this.client.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.3
    });
    
    try {
      const content = response.choices[0].message.content || '[]';
      const subtasks = JSON.parse(content);
      
      task.subtasks = subtasks.map((st: any) => ({
        raw: st.title,
        title: st.title,
        duration_bucket: st.duration_bucket || '10min',
        explicit_minutes: undefined,
        is_project_candidate: false
      }));
      
      return task;
    } catch (error) {
      console.error('OpenAI breakdown error:', error);
      return task;
    }
  }
  
  private extractLines(text: string): string[] {
    // Split by newlines
    let lines = text.split(/\n+/).filter(l => l.trim());
    
    // If single line, check for multiple tasks
    if (lines.length === 1) {
      const single = lines[0];
      // Try numbered lists
      if (single.match(/\d+\)/)) {
        lines = single.split(/\d+\)/).slice(1).map(s => s.trim());
      }
      // Try semicolons or commas with clear task patterns
      else if (single.includes(';')) {
        lines = single.split(';').map(s => s.trim());
      }
    }
    
    return lines.filter(l => l.length > 2);
  }
}
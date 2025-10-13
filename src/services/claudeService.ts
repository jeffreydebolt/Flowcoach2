/**
 * Claude integration for parsing and task breakdown
 * Implements the exact prompts from the build brief
 */

import Anthropic from '@anthropic-ai/sdk';
import { ParsedTask } from '../types/core';
import { parseTime, cleanTaskTitle } from '../parsers/timeParser';

export class ClaudeService {
  private client: Anthropic;
  
  constructor(apiKey: string) {
    this.client = new Anthropic({ apiKey });
  }
  
  /**
   * Parse messy input into structured tasks
   * Uses deterministic time parsing + Claude for classification
   */
  async parseAndClassify(inputText: string): Promise<ParsedTask[]> {
    // First, split into candidate lines
    const lines = this.extractCandidateLines(inputText);
    
    // Apply deterministic time parsing to each line
    const preprocessed = lines.map(line => {
      const timeResult = parseTime(line);
      const cleanedTitle = cleanTaskTitle(timeResult.cleaned_text);
      
      console.log(`Parsing: "${line}"`);
      console.log(`Time result:`, timeResult);
      console.log(`Cleaned title: "${cleanedTitle}"`);
      
      return {
        raw: line,
        title: cleanedTitle,
        explicit_minutes: timeResult.explicit_minutes,
        duration_bucket: timeResult.duration_bucket,
        time_extracted: timeResult.matched_expression, // Tell Claude what we already found
        // Will be determined by Claude
        is_project_candidate: false
      };
    });
    
    // Use Claude to finalize classification and clean up titles
    const claudePrompt = this.buildParsePrompt(preprocessed);
    console.log('\n=== CLAUDE DEBUG ===');
    console.log('Sending to Claude:', claudePrompt);
    console.log('===================\n');
    
    const response = await this.client.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 2000,
      system: this.getParseSystemPrompt(),
      messages: [{ role: 'user', content: claudePrompt }]
    });
    
    try {
      const content = response.content[0];
      if (content.type !== 'text') {
        throw new Error('Expected text response from Claude');
      }
      console.log('Claude raw response:', content.text);
      const result = JSON.parse(content.text);
      console.log('Preprocessed tasks:', preprocessed);
      console.log('Claude result:', result);
      
      // Use Claude's improved titles but keep our time parsing
      const fixed = result.map((task: any, idx: number) => {
        const ourTask = preprocessed[idx];
        if (!ourTask) {
          console.error(`No preprocessed task at index ${idx}`);
          return task;
        }
        
        // Use Claude's improved title but our reliable time parsing
        return {
          raw: ourTask.raw,
          title: task.title || ourTask.title, // Claude's improved title
          explicit_minutes: ourTask.explicit_minutes, // Our time parsing
          duration_bucket: ourTask.duration_bucket, // Our time parsing
          is_project_candidate: task.is_project_candidate || ourTask.is_project_candidate
        };
      });
      
      console.log('Final fixed tasks:', fixed);
      return this.validateParsedTasks(fixed);
    } catch (error) {
      console.error('Claude parsing error:', error);
      console.error('Falling back to deterministic parsing');
      // Fallback to preprocessed results which should be better
      return preprocessed.map(task => ({
        ...task,
        is_project_candidate: task.duration_bucket === '30plus'
      }));
    }
  }
  
  /**
   * Break down a project-sized task into subtasks
   */
  async breakdownProject(task: ParsedTask): Promise<ParsedTask> {
    const prompt = this.buildBreakdownPrompt(task);
    
    const response = await this.client.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 1500,
      system: this.getBreakdownSystemPrompt(),
      messages: [{ role: 'user', content: prompt }]
    });
    
    try {
      const content = response.content[0];
      if (content.type !== 'text') {
        throw new Error('Expected text response from Claude');
      }
      const result = JSON.parse(content.text);
      return this.validateParsedTasks([result])[0];
    } catch (error) {
      console.error('Claude breakdown error:', error);
      throw new Error('Failed to generate subtasks');
    }
  }
  
  private extractCandidateLines(text: string): string[] {
    console.log('extractCandidateLines input:', JSON.stringify(text));
    
    // Split by newlines first
    let lines = text.split(/\n+/).map(l => l.trim()).filter(l => l.length > 0);
    console.log('After newline split:', lines);
    
    // If only one line, try to split by other markers
    if (lines.length === 1) {
      const singleLine = lines[0];
      console.log('Single line detected:', JSON.stringify(singleLine));
      
      // Try numbered patterns: "1) task 2) task"
      const numberedMatch = singleLine.match(/\d+\)/g);
      if (numberedMatch && numberedMatch.length > 1) {
        console.log('Numbered pattern detected');
        lines = singleLine.split(/\d+\)/).slice(1).map(s => s.trim()).filter(s => s);
      }
      // Try bullet patterns
      else if (singleLine.includes(' • ')) {
        console.log('Bullet pattern detected');
        lines = singleLine.split(/\s*•\s*/).slice(1);
      }
      // Try comma splitting if there are multiple time expressions OR multiple commas
      else if ((singleLine.match(/\d+\s*(m|mins?|minutes?|h|hours?)\b/gi) || []).length > 1 ||
               (singleLine.match(/,/g) || []).length >= 1) {
        console.log('Multiple tasks detected by commas or time expressions');
        // Smart comma split - but preserve commas within tasks
        lines = this.smartCommaSplit(singleLine);
      }
      else {
        console.log('No splitting pattern detected, keeping as single line');
      }
    }
    
    const result = lines.filter(line => line.length > 2);
    console.log('Final extracted lines:', result);
    return result;
  }

  private smartCommaSplit(text: string): string[] {
    // Split by commas, but try to be smart about task boundaries
    const parts = text.split(',').map(s => s.trim());
    const tasks: string[] = [];
    let currentTask = '';
    
    for (const part of parts) {
      // If this part looks like a new task (starts with verb or has time), 
      // and we have a current task, push it
      const hasTime = /\d+\s*(m|mins?|minutes?|h|hours?)\b/i.test(part);
      const startsWithVerb = /^(email|call|review|send|update|create|check|plan|draft|write|schedule|contact|ping|text|dm|file|pay)/i.test(part);
      
      if ((hasTime || startsWithVerb) && currentTask) {
        tasks.push(currentTask);
        currentTask = part;
      } else {
        // Continue building current task
        currentTask = currentTask ? `${currentTask}, ${part}` : part;
      }
    }
    
    // Don't forget the last task
    if (currentTask) {
      tasks.push(currentTask);
    }
    
    return tasks;
  }
  
  private getParseSystemPrompt(): string {
    return `You are FlowCoach. You turn messy input into clean, time-aware task plans.

CORE PRINCIPLE: Preserve user wording while making minimal GTD improvements.

Your job:
1) Take preprocessed tasks with time already extracted
2) PRESERVE the exact wording unless fixing obvious issues
3) Remove only meta-language: "add a task to", "remind me to", "I need to"
4) Fix typos and grammar only when obvious
5) Use duration_bucket to determine is_project_candidate

CRITICAL: 
- NEVER change time values or buckets (they're pre-calculated)
- NEVER duplicate time tokens that were already extracted
- If user says "track time block" keep it exactly as "track time block"
- Preserve all context and specifics the user included

Return JSON array only. No explanations or commentary.`;
  }
  
  private getBreakdownSystemPrompt(): string {
    return `You are a GTD-savvy task decomposer.

Given a single project-sized task and its context:
- Produce 3–6 logical subtasks that move from research → draft → review → finalize.
- Each subtask should be atomic, shippable, and assigned a duration bucket using the same rules.
- Titles must be short action phrases, preserving the parent's language.

Return JSON ONLY matching ParsedTask (with subtasks).`;
  }
  
  private buildParsePrompt(preprocessed: any[]): string {
    return `Here are tasks that have been preprocessed with deterministic time extraction:

${JSON.stringify(preprocessed, null, 2)}

CRITICAL RULES:
1. Return the SAME number of tasks in the SAME order
2. IMPROVE the 'title' field using GTD principles BUT preserve user wording
3. NEVER change the duration_bucket or explicit_minutes - these are already correct
4. NEVER duplicate time tokens that were already extracted
5. Set is_project_candidate=true for tasks with duration_bucket='30plus' OR multi-step nature

Title improvements ONLY:
- Remove meta-language: "add a task to", "remind me to", "I need to"
- Fix obvious typos and grammar
- Start with action verbs when natural
- Keep user's specific wording and context

Examples:
Input: "add a task to update cash flow forecast for LL Medico"
Output title: "update cash flow forecast for LL Medico"

Input: "remind me to call john about the meeting"  
Output title: "call John about meeting"

Input: "track time block"
Output title: "track time block" (preserve exact wording)

Return ONLY the JSON array. No explanations.`;
  }
  
  private buildBreakdownPrompt(task: ParsedTask): string {
    return `Break down this project task into 3-6 GTD-style subtasks:

Task: "${task.title}"
Duration: ${task.duration_bucket || 'unspecified'}
Context: ${task.raw}

Requirements:
- Each subtask should be atomic and actionable
- Follow research → draft → review → finalize flow
- Assign appropriate duration buckets
- Use short action phrases
- Preserve the original task's language/context

Return JSON ParsedTask object with subtasks array.`;
  }
  
  private validateParsedTasks(tasks: any[]): ParsedTask[] {
    return tasks.map(task => ({
      raw: task.raw || '',
      title: task.title || '',
      explicit_minutes: task.explicit_minutes,
      duration_bucket: task.duration_bucket,
      is_project_candidate: Boolean(task.is_project_candidate),
      subtasks: task.subtasks ? this.validateParsedTasks(task.subtasks) : undefined
    }));
  }
}
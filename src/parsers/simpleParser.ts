/**
 * Simple, working parser that doesn't suck
 */

import { ParsedTask, DurationBucket } from '../types/core';

export function parseTasksSimple(input: string): ParsedTask[] {
  // Split by common delimiters
  const lines = input.split(/[,;]|\d+\)/).filter(s => s.trim());
  
  const tasks: ParsedTask[] = [];
  
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    
    // Extract time
    let cleanText = trimmed;
    let duration: DurationBucket | null = null;
    let minutes: number | undefined;
    
    // Look for time patterns and remove them
    const timeMatch = trimmed.match(/\s*-?\s*(\d+)\s*min(?:ute)?s?\s*$/i);
    if (timeMatch) {
      cleanText = trimmed.replace(timeMatch[0], '').trim();
      minutes = parseInt(timeMatch[1]);
      
      if (minutes <= 5) duration = '2min';
      else if (minutes <= 15) duration = '10min';
      else duration = '30plus';
    }
    
    // Default 10min for action verbs
    if (!duration && /^(email|call|review|send|check|update)/i.test(cleanText)) {
      duration = '10min';
    }
    
    tasks.push({
      raw: trimmed,
      title: cleanText,
      explicit_minutes: minutes,
      duration_bucket: duration,
      is_project_candidate: duration === '30plus'
    });
  }
  
  return tasks;
}
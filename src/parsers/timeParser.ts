/**
 * Deterministic time parser - runs before LLM processing
 * Extracts explicit time durations from natural language
 */

import { DurationBucket, TimeParseResult } from '../types/core';

interface TimePattern {
  regex: RegExp;
  handler: 'minutes' | 'hours' | 'range' | 'fixed';
  fixed_minutes?: number;
}

const TIME_PATTERNS: TimePattern[] = [
  // Ranges (use upper bound) with typo tolerance
  { regex: /(\d+)\s*[-–]\s*(\d+)\s*(m|mins?|minutes?|min)\b/i, handler: 'range' },
  
  // Fixed expressions with typo tolerance
  { regex: /(half|hlf)\s*(hour|hr|hrs?)/i, handler: 'fixed', fixed_minutes: 30 },
  { regex: /(quarter|1\/4)\s*(hour|hr|hrs?)/i, handler: 'fixed', fixed_minutes: 15 },
  
  // Hours with typo tolerance
  { regex: /(\d+)\s*(h|hr|hrs?|hour|hours?)\b/i, handler: 'hours' },
  
  // Minutes with qualifiers and typo tolerance
  { regex: /~?(about|abt|around)\s+(\d+)\s*(m|mins?|minutes?|min)\b/i, handler: 'minutes' },
  { regex: /(roughly|rughly|aprox|approx)\s+(\d+)\s*(m|mins?|minutes?|min)\b/i, handler: 'minutes' },
  { regex: /(\d+)\s*(m|mins?|minutes?|min|minuts?)\b/i, handler: 'minutes' },
  
  // Short forms with typo tolerance
  { regex: /(\d+)(m|min)\b/i, handler: 'minutes' }
];

// Quick action verbs that default to 10min when no time specified (with typo tolerance)
const QUICK_ACTION_VERBS = [
  'email', 'emal', 'emial', 'mail',
  'call', 'cal', 'phone',
  'ping', 'pign', 
  'text', 'txt', 'msg',
  'dm', 'd.m',
  'reply', 'repli', 'respond',
  'send', 'snd', 'sent',
  'file', 'fil', 'save',
  'pay', 'pal', 'payment',
  'log', 'record',
  'check', 'chek', 'chck', 'verify',
  'review', 'reveiw', 'reviw', 'rev',
  'update', 'updat', 'updte'
];

export function parseTime(text: string): TimeParseResult {
  let explicit_minutes: number | undefined;
  let cleaned_text = text;
  let matched_expression = '';
  
  // Try each pattern
  for (const pattern of TIME_PATTERNS) {
    const match = text.match(pattern.regex);
    if (match) {
      matched_expression = match[0];
      
      switch (pattern.handler) {
        case 'minutes':
          explicit_minutes = parseInt(match[1]);
          break;
          
        case 'hours':
          explicit_minutes = parseInt(match[1]) * 60;
          break;
          
        case 'range':
          // Use upper bound for ranges like "15-30 mins"
          const lower = parseInt(match[1]);
          const upper = parseInt(match[2]);
          explicit_minutes = upper;
          // Also store that this was a range for Claude context
          matched_expression = `${lower}-${upper} minutes`;
          break;
          
        case 'fixed':
          explicit_minutes = pattern.fixed_minutes!;
          break;
      }
      
      // Remove the time expression from text
      cleaned_text = text.replace(pattern.regex, '').trim();
      // Clean up extra spaces and dashes
      cleaned_text = cleaned_text.replace(/\s*[-–]\s*$/, '').trim();
      break;
    }
  }
  
  const duration_bucket = getDurationBucket(explicit_minutes, cleaned_text);
  
  return {
    explicit_minutes,
    duration_bucket,
    cleaned_text,
    matched_expression // Pass this to Claude so it knows what we extracted
  };
}

function getDurationBucket(minutes?: number, text?: string): DurationBucket {
  if (minutes !== undefined) {
    if (minutes <= 5) return '2min';
    if (minutes <= 15) return '10min';
    return '30plus';
  }
  
  // If no explicit time, check for quick action verbs
  if (text) {
    const firstWord = text.split(' ')[0]?.toLowerCase();
    if (QUICK_ACTION_VERBS.includes(firstWord)) {
      return '10min';
    }
  }
  
  return null;
}

export function cleanTaskTitle(text: string): string {
  // Remove common list markers
  let cleaned = text.replace(/^\s*\d+[\.\)]\s*/, ''); // 1. or 1)
  cleaned = cleaned.replace(/^\s*[-•*]\s*/, '');      // bullets
  cleaned = cleaned.replace(/^\s*[a-zA-Z]\.\s*/, ''); // a. b. c.
  
  // Remove task creation prefixes
  const prefixes = [
    /^(create\s+a\s+task\s+to\s+)/i,
    /^(add\s+task\s+to\s+)/i,
    /^(remind\s+me\s+to\s+)/i,
    /^(need\s+to\s+)/i,
    /^(i\s+need\s+to\s+)/i
  ];
  
  for (const prefix of prefixes) {
    cleaned = cleaned.replace(prefix, '');
  }
  
  return cleaned.trim();
}

// Test cases for development
export const TEST_CASES = [
  { input: "email Aaron about invoice - 5 mins", expected: { minutes: 5, bucket: '2min' } },
  { input: "review contracts - 30 minutes", expected: { minutes: 30, bucket: '30plus' } },
  { input: "quick email (2m)", expected: { minutes: 2, bucket: '2min' } },
  { input: "half hour deck edits", expected: { minutes: 30, bucket: '30plus' } },
  { input: "budget thing ~20 minutes", expected: { minutes: 20, bucket: '30plus' } },
  { input: "15-30 mins to clean CRM", expected: { minutes: 30, bucket: '30plus' } },
  { input: "email team", expected: { minutes: undefined, bucket: '10min' } },
  { input: "call John", expected: { minutes: undefined, bucket: '10min' } },
  { input: "draft proposal for Smith", expected: { minutes: undefined, bucket: null } }
];
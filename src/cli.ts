#!/usr/bin/env node
/**
 * CLI interface for testing FlowCoach v2
 * Usage: npm run dev -- organize "1) email Aaron 2) review contract - 30 min"
 */

import dotenv from 'dotenv';
import { FlowCoach } from './core/flowcoach';

dotenv.config();

async function main() {
  const args = process.argv.slice(2);
  const command = args[0];
  const input = args.slice(1).join(' ');
  
  if (!process.env.CLAUDE_API_KEY || !process.env.TODOIST_API_TOKEN) {
    console.error('❌ Missing required environment variables: CLAUDE_API_KEY, TODOIST_API_TOKEN');
    process.exit(1);
  }
  
  const flowcoach = new FlowCoach(
    process.env.CLAUDE_API_KEY,
    process.env.TODOIST_API_TOKEN,
    process.env.FC_DB_PATH
  );
  
  const userId = 'cli_user';
  
  try {
    switch (command) {
      case 'organize':
        if (!input) {
          console.log('Usage: npm run dev -- organize "your tasks here"');
          return;
        }
        const organizeResult = await flowcoach.organize(input, userId);
        console.log(organizeResult.message);
        if (organizeResult.actions) {
          console.log('\nAvailable actions:', organizeResult.actions.join(', '));
        }
        break;
        
      case 'accept':
        const acceptResult = await flowcoach.accept(userId);
        console.log(acceptResult.message);
        break;
        
      case 'breakdown':
        if (!input) {
          console.log('Usage: npm run dev -- breakdown "#1" or "task name"');
          return;
        }
        const breakdownResult = await flowcoach.breakdown(input, userId);
        console.log(breakdownResult.message);
        if (breakdownResult.actions) {
          console.log('\nAvailable actions:', breakdownResult.actions.join(', '));
        }
        break;
        
      case 'resume':
        const resumeResult = await flowcoach.resume(userId);
        console.log(resumeResult.message);
        if (resumeResult.actions) {
          console.log('\nAvailable actions:', resumeResult.actions.join(', '));
        }
        break;
        
      case 'discard':
        const discardResult = await flowcoach.discard(userId);
        console.log(discardResult.message);
        break;
        
      case 'test':
        await runTests(flowcoach);
        break;
        
      default:
        console.log(`
FlowCoach v2 CLI

Commands:
  organize "<tasks>"  - Parse and organize tasks
  accept             - Create tasks in Todoist
  breakdown "#1"     - Break down a project task
  resume             - Resume last session
  discard            - Discard current session
  test               - Run test cases

Examples:
  npm run dev -- organize "1) email Aaron 2) review contract - 30 min"
  npm run dev -- breakdown "#2"
  npm run dev -- accept
        `);
    }
  } catch (error) {
    console.error('❌ Error:', error);
  } finally {
    flowcoach.close();
  }
}

async function runTests(flowcoach: FlowCoach) {
  console.log('🧪 Running FlowCoach tests...\n');
  
  const testCases = [
    {
      name: 'Mixed list with ranges',
      input: `1) email Aaron about invoice
- review contracts - 30 mins  
quick email (2m)
half hour deck edits
budget thing ~20 minutes
15-30 mins to clean CRM`
    },
    {
      name: 'No durations + quick verbs',
      input: 'email team; call John; draft proposal for Smith'
    },
    {
      name: 'Project candidate',
      input: 'build comprehensive financial model for new client - 45 mins'
    }
  ];
  
  for (const testCase of testCases) {
    console.log(`📋 Test: ${testCase.name}`);
    console.log(`Input: "${testCase.input}"`);
    
    try {
      const result = await flowcoach.organize(testCase.input, 'test_user');
      console.log('✅ Result:', result.message);
      
      if (result.data?.tasks) {
        console.log('📊 Parsed tasks:');
        result.data.tasks.forEach((task, i) => {
          console.log(`  ${i + 1}. [${task.duration_bucket || '??'}] ${task.title} ${task.is_project_candidate ? '🔄' : ''}`);
        });
      }
    } catch (error) {
      console.log('❌ Failed:', error);
    }
    
    console.log('---\n');
  }
  
  console.log('🧪 Tests completed!');
}

if (require.main === module) {
  main();
}
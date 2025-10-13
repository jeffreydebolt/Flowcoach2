import { parseTime, cleanTaskTitle } from './src/parsers/timeParser';
import { ClaudeService } from './src/services/claudeService';
import dotenv from 'dotenv';

dotenv.config();

async function testParser() {
  const testInputs = [
    "review Noah's tax return 10 mins",
    "email Sarah about proposal, call dentist - 2 mins, review Q4 budget",
    "track time block - 30 minutes",
    "plan company retreat - 2 hours",
    "15-30 mins to clean CRM",
    "add a task to update cash flow forecast for LL Medico",
    "half hour deck edits"
  ];

  console.log('Testing deterministic time parser:\n');
  
  for (const input of testInputs) {
    const timeResult = parseTime(input);
    const cleanedTitle = cleanTaskTitle(timeResult.cleaned_text);
    
    console.log(`Input: "${input}"`);
    console.log(`Time extracted: ${timeResult.matched_expression || 'none'}`);
    console.log(`Minutes: ${timeResult.explicit_minutes || 'none'}`);
    console.log(`Bucket: ${timeResult.duration_bucket || 'none'}`);
    console.log(`Cleaned title: "${cleanedTitle}"`);
    console.log('---');
  }

  // Test with Claude
  if (process.env.CLAUDE_API_KEY) {
    console.log('\nTesting full parsing with Claude:\n');
    const claude = new ClaudeService(process.env.CLAUDE_API_KEY);
    
    const multiTaskInput = "email Sarah about proposal, call dentist - 2 mins, review Q4 budget - 45 minutes";
    const parsed = await claude.parseAndClassify(multiTaskInput);
    
    console.log('Multi-task input:', multiTaskInput);
    console.log('Parsed result:', JSON.stringify(parsed, null, 2));
  }
}

testParser().catch(console.error);
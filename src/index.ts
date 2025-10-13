#!/usr/bin/env node
/**
 * FlowCoach v2 Entry Point
 * Routes to CLI or future Slack integration
 */

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function main() {
  const args = process.argv.slice(2);
  
  // For now, just route to CLI
  try {
    const { stdout, stderr } = await execAsync(`ts-node src/cli.ts ${args.join(' ')}`);
    if (stdout) console.log(stdout);
    if (stderr) console.error(stderr);
  } catch (error: any) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}
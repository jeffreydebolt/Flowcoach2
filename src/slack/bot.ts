/**
 * Slack Bot integration for FlowCoach v2
 * Connects to your existing Slack app using Socket Mode
 */

import { App } from '@slack/bolt';
import dotenv from 'dotenv';
import { FlowCoach } from '../core/flowcoach';

dotenv.config();

// Initialize FlowCoach
const flowcoach = new FlowCoach(
  process.env.CLAUDE_API_KEY!,
  process.env.TODOIST_API_TOKEN!,
  process.env.FC_DB_PATH
);

// Initialize Slack app
const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  signingSecret: process.env.SLACK_SIGNING_SECRET,
  socketMode: true,
  appToken: process.env.SLACK_APP_TOKEN
});

// Listen for app mentions
app.event('app_mention', async ({ event, context, client, say }) => {
  const userId = event.user || 'unknown';
  const text = event.text.replace(/<@[A-Z0-9]+>/g, '').trim(); // Remove @mentions
  
  console.log(`Received: "${text}" from ${userId}`);
  
  try {
    // Process commands
    if (text.toLowerCase().startsWith('accept')) {
      const result = await flowcoach.accept(userId);
      await say(result.message);
      
    } else if (text.toLowerCase().startsWith('breakdown')) {
      const match = text.match(/breakdown\s+(.+)/i);
      if (match) {
        const result = await flowcoach.breakdown(match[1], userId);
        await say(result.message);
      }
      
    } else if (text.toLowerCase().startsWith('discard')) {
      const result = await flowcoach.discard(userId);
      await say(result.message);
      
    } else if (text.toLowerCase().startsWith('resume')) {
      const result = await flowcoach.resume(userId);
      await say(result.message);
      
    } else {
      // Default to organize command
      const result = await flowcoach.organize(text, userId);
      await say(result.message);
    }
    
  } catch (error) {
    console.error('Error processing message:', error);
    await say('Sorry, I encountered an error. Please try again.');
  }
});

// Handle direct messages
app.message(async ({ message, say, client }) => {
  console.log('Message received:', message);
  
  // Type guard for message
  if (message.subtype || !('text' in message) || !message.text || !('user' in message)) {
    console.log('Message filtered out - subtype:', message.subtype);
    return;
  }
  
  const userId = message.user as string;
  const text = message.text;
  
  console.log(`DM from ${userId}: "${text}"`);
  
  try {
    // Get user info for personalized responses
    let userName = '';
    try {
      const userInfo = await client.users.info({ user: userId });
      userName = userInfo.user?.profile?.first_name || userInfo.user?.real_name || '';
    } catch (e) {
      console.log('Could not fetch user info');
    }
    
    // Handle greetings and casual conversation
    if (text.match(/^(hi|hello|hey|sup|what's up)\b/i)) {
      const greetings = [
        `Hey${userName ? ' ' + userName : ''}! What can I help you organize today?`,
        `Hi${userName ? ' ' + userName : ''}! Ready to turn some chaos into clarity?`,
        `Hello${userName ? ' ' + userName : ''}! Got any tasks you want to capture?`
      ];
      await say(greetings[Math.floor(Math.random() * greetings.length)]);
      return;
    }
    
    // Handle thanks/acknowledgments 
    if (text.match(/^(thanks|thank you|ty|thx|cheers|cool|great|awesome|perfect)$/i)) {
      const result = await flowcoach.handleThanks(userId, message.channel);
      await say(result.message);
      return;
    }
    
    // Handle GTD questions with typo tolerance
    if (text.match(/gtd|g\.t\.d|getting things done|geting things done|productivity|productivty|organize|organiz|organise|focus|focuss/i)) {
      const result = await flowcoach.handleGTDQuestion(text, userId, message.channel);
      await say(result.message);
      return;
    }
    
    // Handle "yes" responses to show pending tasks
    if (text.match(/^(yes|yeah|yep|sure|show me)$/i)) {
      const result = await flowcoach.resume(userId);
      await say(result.message);
      return;
    }
    
    // Handle time estimate responses (like "30 mins", "2min", or just "10")
    if (text.match(/^\d+(\s*(m|mins?|minutes?|h|hours?))?$/i)) {
      // If just a number, assume minutes
      const timeText = text.match(/^\d+$/) ? `${text} mins` : text;
      const result = await flowcoach.updateTimeEstimate(timeText, userId, message.channel);
      await say(result.message);
      return;
    }
    
    // Handle time updates with typo tolerance
    if (text.match(/^(actually\s+|actualy\s+)?(can you\s+|cna you\s+)?(make (that|it|tht)|chang[e]? (that|it|tht) to|updat[e]? (that|it|tht) to)\s+(\d+)(\s*(m|mins?|minutes?|min|h|hrs?|hours?|hour))?\s*(\?)?$/i)) {
      // If just a number without units, add "mins"
      const updatedText = text.match(/\d+\s*$/) ? text + ' mins' : text;
      const result = await flowcoach.updateLastTaskTime(updatedText, userId, message.channel);
      await say(result.message);
      return;
    }
    
    // Process commands
    if (text.toLowerCase().startsWith('accept')) {
      const result = await flowcoach.accept(userId);
      await say(result.message);
      
    } else if (text.toLowerCase().startsWith('breakdown')) {
      const match = text.match(/breakdown\s+(.+)/i);
      if (match) {
        const result = await flowcoach.breakdown(match[1], userId);
        await say(result.message);
      }
      
    } else if (text.toLowerCase().startsWith('discard')) {
      const result = await flowcoach.discard(userId);
      await say(result.message);
      
    } else if (text.toLowerCase().startsWith('resume')) {
      const result = await flowcoach.resume(userId);
      await say(result.message);
      
    } else if (text.match(/clear|reset|start over/i)) {
      const result = await flowcoach.clearAll(userId);
      await say(result.message);
      
    } else if (text.match(/calendar|schedule|meeting|what does.*today|what's.*today|busy.*today|free time|time for.*task|do I have.*time|have time for/i)) {
      const result = await flowcoach.getCalendarSummary(userId, text);
      await say(result.message);
      
    } else if (text.match(/status|statu|show.*my.*(tasks|todo|list)|what.*(do i have|on my list|my tasks)|whats on my list|what.*on.*(my\s)?(list|lst)|pending|pendin|my tasks|list my tasks|my todo|todo list|show.*todo/i)) {
      const result = await flowcoach.getStatus(userId);
      await say(result.message);
      
    } else if (text.match(/^(snooze|snooz|snoz)\s+(.+?)\s+(tomorrow|tommorow|tomorow|tmrw)$/i)) {
      const match = text.match(/^(?:snooze|snooz|snoz)\s+(.+?)\s+(?:tomorrow|tommorow|tomorow|tmrw)$/i);
      if (match) {
        const result = await flowcoach.snoozeTask(match[1], 'tomorrow', userId);
        await say(result.message);
      }
      
    } else if (text.match(/^(do\s+today|do\s+tday|today)\s+(.+)$/i)) {
      const match = text.match(/^(?:do\s+today|do\s+tday|today)\s+(.+)$/i);
      if (match) {
        const result = await flowcoach.snoozeTask(match[1], 'today', userId);
        await say(result.message);
      }
      
    } else if (text.match(/^(undate|unddate|remove\s+date|clear\s+date)\s+(.+)$/i)) {
      const match = text.match(/^(?:undate|unddate|remove\s+date|clear\s+date)\s+(.+)$/i);
      if (match) {
        const result = await flowcoach.snoozeTask(match[1], 'undate', userId);
        await say(result.message);
      }
      
    } else {
      // Smart intent detection based on context
      const textLower = text.toLowerCase();
      
      // Check if this is asking to VIEW tasks/lists (not create them)
      const isViewingRequest = textLower.match(/\b(show|see|view|list|display|what are|what's|check)\b.*\b(my|the)\s*(tasks?|todos?|list|items)/i) ||
                              textLower.match(/\b(todo|task)\s*list/i) ||
                              textLower.match(/what.*(do i have|i need to do|on my plate|pending)/i);
      
      if (isViewingRequest) {
        const result = await flowcoach.getStatus(userId);
        await say(result.message);
        return;
      }
      
      // Check if asking what the bot can do
      const isHelpRequest = textLower.match(/\b(what can you do|how do you work|what do you do|help|how to use|what are you|who are you)/i) ||
                           textLower.match(/\b(capabilities|features|commands)/i);
      
      if (isHelpRequest) {
        await say(`I'm FlowCoach, your task organization assistant! Here's what I can do:

**📝 Task Management:**
• Just tell me what you need to do: "review budget docs 30 mins"
• I'll organize tasks by time: [2min], [10min], [30+min]
• Update times: "actually make that 45 mins"

**📅 Scheduling:**
• Check your calendar: "what's my day like?"
• Move tasks: "snooze budget review tomorrow"
• Find time slots: "do I have time for a 30 min task?"

**📊 Organization:**
• View your tasks: "show my todo list" or "status"
• Break down big tasks: "breakdown #1"
• Ask me about GTD productivity methods

Just talk naturally - I understand context!`);
        return;
      }
      
      // Check for GTD questions
      const isGTDQuestion = text.match(/\b(gtd|g\.t\.d|getting things done|geting things done|two minute|two min|next action|nxt action|weekly review|weakly review|someday|som day|capture|captur|clarify|clarfy|organize|organiz|organise|reflect|reflct|engage|engag)\b/i) ||
                           text.match(/what('s| is).*(two minute|two min|gtd|g\.t\.d|productivity|productivty|next action)/i) ||
                           text.match(/(tell|tel|explain|explan|teach|teac).*(gtd|g\.t\.d|productivity|productivty|two minute|two min)/i);
      
      if (isGTDQuestion) {
        const result = await flowcoach.handleGTDQuestion(text, userId, message.channel);
        await say(result.message);
        return;
      }
      
      // Improved task detection - look for action-oriented language
      const hasActionVerb = text.match(/^(review|reveiw|reviw|call|cal|email|emial|emal|send|snd|check|chek|update|updat|create|creat|write|writ|plan|pln|schedule|schdule|fix|compile|prepare|draft|submit|complete|finish|start|begin|do|get|talk|speak|meet|contact|research|analyze|build|design|test|debug|deploy|implement|setup|configure|install|migrate|refactor|optimize|document|report|present|discuss|coordinate|approve|ship|launch|publish)/i);
      const hasTimeIndicator = text.match(/\b(\d+\s*(m|mins?|minutes?|hours?|hrs?)|today|tomorrow|asap|urgent|quick|fast)\b/i);
      const hasTaskKeyword = text.match(/\b(task|taks|todo|to-do|remind|remember|need to|have to|must|should|gotta)\b/i);
      
      // If it looks like a task (action verb OR time indicator OR task keyword), treat it as one
      const isTaskRequest = hasActionVerb || hasTimeIndicator || hasTaskKeyword ||
                           text.match(/i need to|i ned to|need to do|need to|have to|hav to/i);
      
      if (isTaskRequest) {
        const result = await flowcoach.organize(text, userId, message.channel);
        await say(result.message);
      } else {
        // Check for follow-up responses after GTD questions
        const isFollowUp = text.match(/^\s*(organizing|clarifying|capturing)\s*(i guess|I suppose)?$/i);
        if (isFollowUp) {
          const result = await flowcoach.handleFollowUp(text, userId, message.channel);
          await say(result.message);
        } else {
          // Casual conversation
          const result = await flowcoach.handleConversation(text, userId, userName);
          await say(result.message);
        }
      }
    }
  } catch (error) {
    console.error('Error processing DM:', error);
    await say('Something went wrong on my end. Mind trying that again?');
  }
});

// Start your app
(async () => {
  await app.start();
  console.log('⚡️ FlowCoach is running!');
})();

// Graceful shutdown
process.on('SIGINT', () => {
  flowcoach.close();
  process.exit(0);
});
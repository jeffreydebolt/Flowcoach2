/**
 * Core FlowCoach engine - orchestrates parsing, sessions, and task creation
 */

import { ClaudeService } from '../services/claudeService';
import { SessionService } from '../services/sessionService';
import { TodoistService } from '../services/todoistService';
import { ThreadStateService } from '../services/threadStateService';
import { ParsedTask, Session, FlowCoachResponse, UserContext, TodoistTask } from '../types/core';

export class FlowCoach {
  private claude: ClaudeService;
  private sessions: SessionService;
  private todoist: TodoistService;
  private threadState: ThreadStateService;
  private previewMode: 'off' | 'soft' | 'on';
  
  constructor(
    claudeApiKey: string,
    todoistApiKey: string,
    dbPath?: string,
    userConfig?: UserContext
  ) {
    this.claude = new ClaudeService(claudeApiKey);
    this.sessions = new SessionService(dbPath);
    this.todoist = new TodoistService(todoistApiKey, userConfig);
    this.threadState = new ThreadStateService(dbPath);
    
    // Read preview mode from environment variable
    this.previewMode = (process.env.FC_PREVIEW_MODE as 'off' | 'soft' | 'on') || 'soft';
  }
  
  /**
   * Main entry point: organize messy input into structured tasks
   */
  async organize(inputText: string, userId: string, channelId: string = 'DM'): Promise<FlowCoachResponse> {
    try {
      // Parse input using Claude + deterministic time parsing
      const parsed = await this.claude.parseAndClassify(inputText);
      
      if (parsed.length === 0) {
        return {
          type: 'error',
          message: "I couldn't find any tasks in that input. Try something like '1) email Aaron 2) review contract - 30 min'"
        };
      }
      
      // Create session
      const session = await this.sessions.createSession(userId, inputText, parsed);
      
      // Group tasks for preview
      const quickWins = parsed.filter(t => t.duration_bucket === '2min' || t.duration_bucket === '10min');
      const projects = parsed.filter(t => t.duration_bucket === '30plus' || t.is_project_candidate);
      
      // Check if we have time estimates
      const needsTime = parsed.some(t => !t.explicit_minutes && !t.duration_bucket);
      
      if (needsTime) {
        return {
          type: 'needs_time',
          message: `Got it: "${parsed[0].title}"\n\nHow long do you think this will take?`,
          data: { session, tasks: parsed },
          actions: ['2min', '10min', '30min', 'other']
        };
      }
      
      // Check preview mode
      if (this.previewMode !== 'off') {
        // Show preview instead of auto-creating
        const preview = this.formatTaskPreview(quickWins, projects);
        return {
          type: 'preview',
          message: preview,
          data: { session, tasks: parsed }
        };
      }
      
      // Legacy behavior: auto-create in Todoist
      const todoistResult = await this.todoist.createTasks(parsed, session.id);
      
      if (todoistResult.created.length > 0) {
        // Save thread state for conversation memory
        const firstTask = todoistResult.created[0];
        await this.threadState.updateThreadState(userId, channelId, {
          lastIntent: 'task_created',
          lastCreatedTaskId: firstTask.id,
          lastTaskTitle: parsed[0].title,
          context: {
            duration_bucket: parsed[0].duration_bucket,
            explicit_minutes: parsed[0].explicit_minutes
          }
        });
        
        return {
          type: 'success',
          message: `✅ Added "${parsed[0].title}" [${parsed[0].duration_bucket}] to your inbox.`
        };
      } else {
        return {
          type: 'error',
          message: `I couldn't add that to Todoist right now. Want me to try again?`
        };
      }
      
    } catch (error) {
      console.error('Organization error:', error);
      return {
        type: 'error',
        message: 'Sorry, I encountered an error processing your input. Please try again.'
      };
    }
  }
  
  /**
   * Accept and create tasks in Todoist
   */
  async accept(userId: string, sessionId?: string): Promise<FlowCoachResponse> {
    try {
      // Get session
      const session = sessionId 
        ? await this.sessions.getSession(sessionId)
        : await this.sessions.getLastPendingSession(userId);
      
      if (!session) {
        return {
          type: 'error',
          message: 'No pending tasks found. Use **@flowcoach organize** first.'
        };
      }
      
      // Filter out tasks already created (idempotency)
      const tasksToCreate: ParsedTask[] = [];
      for (const task of session.parsed) {
        const alreadyCreated = await this.sessions.isTaskAlreadyCreated(session.id, task);
        if (!alreadyCreated) {
          tasksToCreate.push(task);
        }
      }
      
      if (tasksToCreate.length === 0) {
        return {
          type: 'success',
          message: 'All tasks from this session were already created.'
        };
      }
      
      // Create tasks in Todoist
      const result = await this.todoist.createTasks(tasksToCreate, session.id);
      
      if (result.offline) {
        await this.sessions.updateSession(session.id, 'pending'); // Keep pending for retry
        return {
          type: 'error',
          message: 'Todoist is down. Your tasks are staged. Run **@flowcoach push** later.',
          actions: ['@flowcoach push']
        };
      }
      
      // Record created tasks
      for (const task of tasksToCreate) {
        const todoistTask = result.created.find(t => 
          t.content.includes(task.title) || task.title.includes(t.content.replace(/^\[[^\]]+\]\s*/, ''))
        );
        await this.sessions.recordTaskCreated(session.id, task, todoistTask?.id);
      }
      
      // Update session status
      const createdIds = result.created.map(t => t.id);
      await this.sessions.updateSession(session.id, 'pushed', createdIds);
      
      let message = `✅ Created ${result.created.length} tasks in Todoist!`;
      
      if (result.failed.length > 0) {
        message += `\n\n⚠️ ${result.failed.length} tasks failed to create:`;
        result.failed.slice(0, 3).forEach(task => {
          message += `\n• ${task.title}`;
        });
        if (result.failed.length > 3) {
          message += `\n• ...and ${result.failed.length - 3} more`;
        }
        message += '\n\nTry checking your Todoist API token or network connection.';
      }
      
      return {
        type: result.failed.length === 0 ? 'success' : 'warning',
        message
      };
      
    } catch (error) {
      console.error('Accept error:', error);
      
      // Try to provide more specific error messages
      let errorMessage = 'Failed to create tasks in Todoist.';
      
      if (error instanceof Error) {
        if (error.message.includes('401') || error.message.includes('Unauthorized')) {
          errorMessage = 'Todoist API token is invalid or expired. Please check your .env file.';
        } else if (error.message.includes('403') || error.message.includes('Forbidden')) {
          errorMessage = 'Permission denied. Please check your Todoist API permissions.';
        } else if (error.message.includes('429') || error.message.includes('rate limit')) {
          errorMessage = 'Too many requests to Todoist. Please wait a moment and try again.';
        } else if (error.message.includes('network') || error.message.includes('connect')) {
          errorMessage = 'Network error connecting to Todoist. Check your internet connection.';
        }
      }
      
      return {
        type: 'error',
        message: errorMessage
      };
    }
  }
  
  /**
   * Break down a project task into subtasks
   */
  async breakdown(taskRef: string, userId: string): Promise<FlowCoachResponse> {
    try {
      const session = await this.sessions.getLastPendingSession(userId);
      if (!session) {
        return {
          type: 'error',
          message: 'No pending session found. Use **@flowcoach organize** first.'
        };
      }
      
      // Find task by index (#1, #2) or by text match
      const task = this.findTaskInSession(session, taskRef);
      if (!task) {
        return {
          type: 'error',
          message: `Task "${taskRef}" not found. Use **@flowcoach organize** to see numbered list.`
        };
      }
      
      // Generate breakdown using Claude
      const brokenDown = await this.claude.breakdownProject(task);
      
      if (!brokenDown.subtasks || brokenDown.subtasks.length === 0) {
        return {
          type: 'error',
          message: `Couldn't break down "${task.title}". It might already be specific enough.`
        };
      }
      
      // Update the task in the session
      const updatedParsed = session.parsed.map(t => 
        t.title === task.title ? brokenDown : t
      );
      
      // Update session with breakdown
      await this.sessions.updateSession(session.id, 'pending');
      
      const preview = brokenDown.subtasks.map((st, i) => 
        `  ${i + 1}. [${st.duration_bucket || '??'}] ${st.title}`
      ).join('\n');
      
      return {
        type: 'preview',
        message: `Broke down "${task.title}" into ${brokenDown.subtasks.length} subtasks:\n\n${preview}\n\nSay **@flowcoach accept** to create all tasks.`,
        data: { 
          session: { ...session, parsed: updatedParsed },
          tasks: updatedParsed 
        },
        actions: ['@flowcoach accept', '@flowcoach retry', '@flowcoach discard']
      };
      
    } catch (error) {
      console.error('Breakdown error:', error);
      return {
        type: 'error',
        message: 'Failed to break down task. Please try again.'
      };
    }
  }
  
  /**
   * Resume last pending session
   */
  async resume(userId: string): Promise<FlowCoachResponse> {
    const session = await this.sessions.getLastPendingSession(userId);
    
    if (!session) {
      return {
        type: 'error',
        message: 'No pending session found.',
        actions: ['@flowcoach organize <your tasks>']
      };
    }
    
    const quickWins = session.parsed.filter(t => t.duration_bucket === '2min' || t.duration_bucket === '10min');
    const projects = session.parsed.filter(t => t.duration_bucket === '30plus' || t.is_project_candidate);
    
    const preview = this.formatTaskPreview(quickWins, projects);
    
    return {
      type: 'preview',
      message: `Resuming session from ${new Date(session.createdAt).toLocaleString()}:\n\n${preview}`,
      data: { session, tasks: session.parsed },
      actions: ['@flowcoach accept', '@flowcoach breakdown #<number>', '@flowcoach discard']
    };
  }
  
  /**
   * Handle GTD and productivity questions
   */
  async handleGTDQuestion(question: string, userId: string, channelId: string = 'DM'): Promise<FlowCoachResponse> {
    // Save thread state for context
    await this.threadState.updateThreadState(userId, channelId, {
      lastIntent: 'gtd_help',
      lastTopic: 'GTD'
    });
    const gtdTopics = {
      capture: "The key to GTD is capturing everything that has your attention. Don't let thoughts bounce around in your head - get them into a trusted system. I can help you capture tasks right here!",
      clarify: "When you capture something, ask: Is it actionable? If yes, what's the very next physical action? If it takes less than 2 minutes, do it now. Otherwise, defer, delegate, or organize it.",
      organize: "Organize by context and energy. Group similar actions together - all your calls, all your computer work, etc. That's why I use time buckets like [2min], [10min], and [30+min].",
      reflect: "Regular reviews keep your system current. Weekly reviews are essential - what got done, what didn't, what's changed?",
      engage: "Trust your system so you can focus. When you know everything important is captured and organized, you can work with confidence.",
      "two minute": "If something takes less than 2 minutes, just do it now rather than tracking it. It takes longer to organize than to just handle it.",
      "next action": "Always define the very next physical action. Not 'plan vacation' but 'search flights to Portland'. Make it specific and actionable.",
      someday: "Someday/Maybe lists are for things you might want to do but aren't committed to. Review them regularly but don't let them clutter your active lists."
    };
    
    const topic = Object.keys(gtdTopics).find(key => question.toLowerCase().includes(key));
    const response = topic ? gtdTopics[topic as keyof typeof gtdTopics] : 
      "GTD is about capturing everything, clarifying what it means, organizing by context, reflecting regularly, and engaging with confidence. What specific part would you like to know more about?";
    
    return {
      type: 'success',
      message: response
    };
  }
  
  /**
   * Handle follow-up responses based on thread state
   */
  async handleFollowUp(text: string, userId: string, channelId: string = 'DM'): Promise<FlowCoachResponse> {
    const threadState = await this.threadState.getThreadState(userId, channelId);
    
    if (!threadState || !threadState.lastTopic) {
      return {
        type: 'success',
        message: "I'm not sure what you're referring to. What would you like to know about?"
      };
    }
    
    // If they said "organizing" after a GTD question
    if (text.match(/organizing/i) && threadState.lastTopic === 'GTD') {
      return {
        type: 'success',
        message: "Great choice! In GTD, organizing means putting things where they belong - by context, time available, and energy. Use lists like @calls, @computer, @errands. I organize your tasks by time buckets ([2min], [10min], [30+min]) so you can match tasks to your available time. Want to try capturing some tasks to organize?"
      };
    }
    
    // Add more follow-up handlers as needed
    return {
      type: 'success',
      message: "I understand! Let me know how I can help with that."
    };
  }

  /**
   * Handle thanks/acknowledgments based on context
   */
  async handleThanks(userId: string, channelId: string = 'DM'): Promise<FlowCoachResponse> {
    const threadState = await this.threadState.getThreadState(userId, channelId);
    
    if (threadState?.lastIntent === 'task_updated') {
      const responses = [
        "You're welcome! The task is all updated in Todoist.",
        "No problem! Time estimates make all the difference for planning.",
        "Glad I could help! Your tasks are looking organized.",
        "Anytime! Having the right time buckets helps with prioritization."
      ];
      return {
        type: 'success',
        message: responses[Math.floor(Math.random() * responses.length)]
      };
    }
    
    if (threadState?.lastIntent === 'task_created') {
      const responses = [
        "You bet! Your task is safely captured in Todoist.",
        "Happy to help! One more thing off your mind.",
        "No worries! I've got it organized for you."
      ];
      return {
        type: 'success',
        message: responses[Math.floor(Math.random() * responses.length)]
      };
    }
    
    if (threadState?.lastTopic === 'GTD') {
      return {
        type: 'success',
        message: "Glad that GTD info was helpful! Let me know if you want to organize some tasks."
      };
    }
    
    // Generic thanks
    const responses = [
      "You're very welcome!",
      "Anytime! I'm here when you need to organize.",
      "My pleasure! Let me know what else I can help with."
    ];
    
    return {
      type: 'success',
      message: responses[Math.floor(Math.random() * responses.length)]
    };
  }

  /**
   * Handle general conversation with clarification
   */
  async handleConversation(text: string, userId: string, userName: string): Promise<FlowCoachResponse> {
    // Try to understand what they might want based on keywords
    const textLower = text.toLowerCase();
    
    // Check for task-related words that might have been missed
    if (textLower.includes('task') || textLower.includes('todo') || textLower.includes('remind')) {
      return {
        type: 'success',
        message: `It sounds like you want to create a task! Try saying something like "add task to..." or "can you create a task to..." and I'll help organize it.`
      };
    }
    
    // Check for time/calendar related words
    if (textLower.includes('time') || textLower.includes('calendar') || textLower.includes('schedule') || textLower.includes('meeting')) {
      return {
        type: 'success',
        message: `Are you asking about your calendar or schedule? Try "what's my calendar like today" or "do I have time for a 30 minute task?"`
      };
    }
    
    // Check for list/status related words
    if (textLower.includes('list') || textLower.includes('tasks') || textLower.includes('status')) {
      return {
        type: 'success',
        message: `Want to see your tasks? Try "what's on my list" or "status" and I'll show you what you have in Todoist.`
      };
    }
    
    // Check for productivity/GTD related words
    if (textLower.includes('productiv') || textLower.includes('organiz') || textLower.includes('focus')) {
      return {
        type: 'success',
        message: `Interested in productivity tips? Ask me about GTD (Getting Things Done) or say "tell me about productivity" for some insights!`
      };
    }
    
    // Check for action words that might be tasks
    const actionWords = ['update', 'review', 'call', 'email', 'send', 'check', 'plan', 'write', 'create'];
    const hasActionWord = actionWords.some(word => textLower.includes(word));
    
    if (hasActionWord) {
      return {
        type: 'success',
        message: `It looks like you might want to create a task! Try rephrasing it like "add task to ${text}" or just "can you create a task to ${text}"`
      };
    }
    
    // Fallback with variety and clarification
    const clarificationResponses = [
      `I'm not quite sure what you're looking for${userName ? ', ' + userName : ''}. I can help you:\n• Create tasks ("add task to...")\n• Check your calendar ("what's my calendar like?")\n• Show your task list ("what's on my list?")\n• Answer GTD questions ("tell me about productivity")\n\nWhat would you like to do?`,
      
      `I didn't catch that! Here's what I'm great at:\n• **Task creation**: "can you add a task to..."\n• **Calendar checking**: "do I have time for..."\n• **Task status**: "what's on my list?"\n• **Productivity tips**: "tell me about GTD"\n\nTry one of those!`,
      
      `Hmm, I'm not sure what you meant. I specialize in:\n• Capturing tasks and organizing them by time\n• Checking your calendar for availability\n• Showing your current task list\n• Sharing GTD productivity advice\n\nWhat can I help you with?`,
      
      `I'm your task organization assistant! I might have missed what you're asking for. I can:\n• Turn messy thoughts into organized tasks\n• Check if you have time for something\n• Show what's already on your plate\n• Share productivity insights\n\nWhat would be most helpful right now?`,
      
      `Not sure I understood that one! I'm here to help with:\n• Creating and organizing tasks\n• Calendar and time management\n• Showing your current workload\n• GTD methodology questions\n\nCould you rephrase what you need?`
    ];
    
    return {
      type: 'success',
      message: clarificationResponses[Math.floor(Math.random() * clarificationResponses.length)]
    };
  }
  
  /**
   * Update the last created task with new time estimate
   */
  async updateLastTaskTime(timeText: string, userId: string, channelId: string = 'DM'): Promise<FlowCoachResponse> {
    const threadState = await this.threadState.getThreadState(userId, channelId);
    
    if (!threadState || threadState.lastIntent !== 'task_created' || !threadState.lastCreatedTaskId) {
      return {
        type: 'error',
        message: "I don't see a recent task to update. Try creating a task first!"
      };
    }
    
    // Parse the new time
    const timeMatch = timeText.match(/(\d+)\s*(m|mins?|minutes?|h|hours?)/i);
    if (!timeMatch) {
      return {
        type: 'error',
        message: "I didn't understand that time format. Try '45 mins' or '2 hours'."
      };
    }
    
    let minutes = parseInt(timeMatch[1]);
    if (timeMatch[2].toLowerCase().startsWith('h')) {
      minutes *= 60;
    }
    
    // Determine new bucket
    const newBucket = minutes <= 5 ? '2min' : minutes <= 15 ? '10min' : '30plus';
    const oldBucket = threadState.context?.duration_bucket || 'unknown';
    
    // Update the task in Todoist
    try {
      const newContent = `[${newBucket}] ${threadState.lastTaskTitle}`;
      await this.todoist.updateTask(threadState.lastCreatedTaskId, { content: newContent });
      
      // Update thread state with new time
      await this.threadState.updateThreadState(userId, channelId, {
        lastIntent: 'task_updated',
        context: {
          duration_bucket: newBucket,
          explicit_minutes: minutes,
          justUpdatedTask: true
        }
      });
      
      return {
        type: 'success',
        message: `✅ Updated "${threadState.lastTaskTitle}" from [${oldBucket}] to [${newBucket}]`
      };
    } catch (error) {
      console.error('Failed to update task:', error);
      return {
        type: 'error',
        message: `I couldn't update that task. It might have been deleted or moved.`
      };
    }
  }

  /**
   * Update time estimate for pending task
   */
  async updateTimeEstimate(timeText: string, userId: string, channelId: string = 'DM'): Promise<FlowCoachResponse> {
    const session = await this.sessions.getLastPendingSession(userId);
    
    console.log('updateTimeEstimate - session:', session);
    
    if (!session || !session.parsed.length) {
      return {
        type: 'error',
        message: "I don't have any pending tasks to update. Try adding a new task!"
      };
    }
    
    // Parse the time estimate
    const timeMatch = timeText.match(/(\d+)\s*(m|mins?|minutes?|h|hours?)/i);
    if (!timeMatch) {
      return {
        type: 'error',
        message: "I didn't understand that time format. Try '30 mins' or '2 hours'."
      };
    }
    
    let minutes = parseInt(timeMatch[1]);
    if (timeMatch[2].toLowerCase().startsWith('h')) {
      minutes *= 60; // Convert hours to minutes
    }
    
    // Determine duration bucket
    let duration_bucket: any = null;
    if (minutes <= 5) duration_bucket = '2min';
    else if (minutes <= 15) duration_bucket = '10min';
    else duration_bucket = '30plus';
    
    // Update the task
    const task = session.parsed[0];
    task.explicit_minutes = minutes;
    task.duration_bucket = duration_bucket;
    task.is_project_candidate = duration_bucket === '30plus';
    
    // Create in Todoist
    const todoistResult = await this.todoist.createTasks([task], session.id);
    
    if (todoistResult.created.length > 0) {
      // Mark session as completed
      const taskIds = todoistResult.created.map(t => t.id);
      await this.sessions.updateSession(session.id, 'accepted', taskIds);
      
      // Save thread state for conversation memory
      const firstTask = todoistResult.created[0];
      await this.threadState.updateThreadState(userId, channelId, {
        lastIntent: 'task_created',
        lastCreatedTaskId: firstTask.id,
        lastTaskTitle: task.title,
        context: {
          duration_bucket: task.duration_bucket,
          explicit_minutes: task.explicit_minutes
        }
      });
      
      return {
        type: 'success',
        message: `✅ Added "${task.title}" [${duration_bucket}] to your inbox.`
      };
    } else {
      return {
        type: 'error',
        message: `I couldn't add that to Todoist right now. Want me to try again?`
      };
    }
  }
  
  /**
   * Get calendar summary
   */
  async getCalendarSummary(userId: string, input?: string): Promise<FlowCoachResponse> {
    // Check if calendar is configured
    if (!process.env.GOOGLE_CLIENT_ID || !process.env.GOOGLE_REFRESH_TOKEN) {
      return {
        type: 'success',
        message: "I don't have access to your calendar yet. But I can help you organize tasks based on your schedule - just tell me when you're busy!"
      };
    }
    
    try {
      const { CalendarService } = await import('../services/calendarService');
      const calendar = new CalendarService({
        client_id: process.env.GOOGLE_CLIENT_ID,
        client_secret: process.env.GOOGLE_CLIENT_SECRET!,
        refresh_token: process.env.GOOGLE_REFRESH_TOKEN
      });
      
      // If asking about time for a specific task, check for time slots
      if (input && input.match(/time for.*task|do I have.*time|have time for.*(\d+).*min/i)) {
        const timeMatch = input.match(/(\d+)\s*(min|hour)/i);
        let requiredMinutes = 30; // default
        
        if (timeMatch) {
          requiredMinutes = parseInt(timeMatch[1]);
          if (timeMatch[2].toLowerCase().startsWith('hour')) {
            requiredMinutes *= 60;
          }
        }
        
        const context = await calendar.getContext(12);
        const availableSlots = context.freeSlots.filter(slot => slot.duration >= requiredMinutes);
        
        if (availableSlots.length > 0) {
          const nextSlot = availableSlots[0];
          const timeStr = nextSlot.start.toLocaleTimeString('en-US', { 
            hour: 'numeric', 
            minute: '2-digit',
            hour12: true 
          });
          return {
            type: 'success',
            message: `Yes! You have a ${Math.floor(nextSlot.duration / 60)} hour ${nextSlot.duration % 60} minute slot starting at ${timeStr}. Perfect for a ${requiredMinutes} minute task.`
          };
        } else {
          return {
            type: 'success',
            message: `Looking at your schedule, you don't have a clear ${requiredMinutes} minute block today. Your biggest free slot is ${Math.floor(context.freeSlots[0]?.duration / 60) || 0} hours. Maybe break it into smaller tasks?`
          };
        }
      }
      
      // Otherwise just show the summary
      const summary = await calendar.getTodaySummary();
      return {
        type: 'success',
        message: summary
      };
    } catch (error) {
      console.error('Calendar error:', error);
      return {
        type: 'success',
        message: "I'm having trouble connecting to your calendar right now. What time works best for you today?"
      };
    }
  }
  
  /**
   * Get user's current status
   */
  async getStatus(userId: string): Promise<FlowCoachResponse> {
    // First check pending session
    const session = await this.sessions.getLastPendingSession(userId);
    
    if (session && session.parsed.length > 0) {
      const count = session.parsed.length;
      const taskWord = count === 1 ? 'task' : 'tasks';
      return {
        type: 'success',
        message: `You have ${count} ${taskWord} waiting to be organized. Want me to show them to you?`
      };
    }
    
    // If no pending tasks, show Todoist tasks
    try {
      const tasks = await this.todoist.getTasks();
      
      if (tasks.length === 0) {
        return {
          type: 'success',
          message: "Your task list is completely clear! Ready to capture whatever's on your mind."
        };
      }
      
      // Group by time buckets and show recent tasks
      const todayTasks = tasks.filter((task: TodoistTask) => {
        if (!task.due) return false;
        const dueDate = new Date(task.due.date);
        const today = new Date();
        return dueDate.toDateString() === today.toDateString();
      });
      
      const recentTasks = tasks.slice(0, 5); // Show first 5 tasks
      
      let message = `You have ${tasks.length} tasks in Todoist.`;
      
      if (todayTasks.length > 0) {
        message += `\n\n**Due today (${todayTasks.length}):**`;
        todayTasks.slice(0, 3).forEach((task: TodoistTask) => {
          const prefix = task.content.match(/^\[(\w+)\]/)?.[1] || '';
          const cleanContent = task.content.replace(/^\[\w+\]\s*/, '');
          message += `\n• ${prefix ? `[${prefix}] ` : ''}${cleanContent}`;
        });
        if (todayTasks.length > 3) {
          message += `\n• ...and ${todayTasks.length - 3} more`;
        }
      } else if (recentTasks.length > 0) {
        message += `\n\n**Recent tasks:**`;
        recentTasks.forEach((task: TodoistTask) => {
          const prefix = task.content.match(/^\[(\w+)\]/)?.[1] || '';
          const cleanContent = task.content.replace(/^\[\w+\]\s*/, '');
          message += `\n• ${prefix ? `[${prefix}] ` : ''}${cleanContent}`;
        });
      }
      
      return {
        type: 'success',
        message
      };
      
    } catch (error) {
      console.error('Error fetching Todoist tasks:', error);
      
      let errorMessage = "I couldn't check your Todoist tasks right now.";
      
      if (error instanceof Error) {
        if (error.message.includes('401') || error.message.includes('Unauthorized')) {
          errorMessage = "Your Todoist API token seems to be invalid. Please check your .env file.";
        } else if (error.message.includes('network') || error.message.includes('connect')) {
          errorMessage = "I'm having trouble connecting to Todoist. Check your internet connection.";
        }
      }
      
      return {
        type: 'error',
        message: errorMessage
      };
    }
  }
  
  /**
   * Snooze/reschedule a task
   */
  async snoozeTask(taskRef: string, when: 'tomorrow' | 'today' | 'undate', userId: string): Promise<FlowCoachResponse> {
    try {
      // Get user's tasks
      const tasks = await this.todoist.getTasks();
      
      if (tasks.length === 0) {
        return {
          type: 'error',
          message: "You don't have any tasks to snooze."
        };
      }
      
      // Find task by reference (number or text match)
      let targetTask: TodoistTask | undefined;
      
      // Try index first (#1, #2, or just 1, 2)
      const indexMatch = taskRef.match(/^#?(\d+)$/);
      if (indexMatch) {
        const index = parseInt(indexMatch[1]) - 1;
        if (index >= 0 && index < tasks.length) {
          targetTask = tasks[index];
        }
      }
      
      // Try text match if no index match
      if (!targetTask) {
        const searchText = taskRef.toLowerCase();
        targetTask = tasks.find(task => {
          const cleanContent = task.content.replace(/^\[\w+\]\s*/, '').toLowerCase();
          return cleanContent.includes(searchText) || searchText.includes(cleanContent);
        });
      }
      
      if (!targetTask) {
        return {
          type: 'error',
          message: `I couldn't find a task matching "${taskRef}". Try using a task number or more specific text.`
        };
      }
      
      // Prepare the due date update
      let dueUpdate: any = null;
      let confirmMessage = '';
      const taskTitle = targetTask.content.replace(/^\[\w+\]\s*/, '');
      
      switch (when) {
        case 'tomorrow':
          const tomorrow = new Date();
          tomorrow.setDate(tomorrow.getDate() + 1);
          tomorrow.setHours(9, 30, 0, 0); // 9:30 AM
          dueUpdate = {
            date: tomorrow.toISOString().split('T')[0],
            string: 'tomorrow at 9:30am'
          };
          confirmMessage = `Move "${taskTitle}" to tomorrow at 9:30am?`;
          break;
          
        case 'today':
          const today = new Date();
          dueUpdate = {
            date: today.toISOString().split('T')[0],
            string: 'today'
          };
          confirmMessage = `Move "${taskTitle}" to today?`;
          break;
          
        case 'undate':
          dueUpdate = null; // This will clear the due date
          confirmMessage = `Remove the due date from "${taskTitle}"?`;
          break;
      }
      
      // For now, just do it (we can add confirmation flow later)
      await this.todoist.updateTask(targetTask.id, { due: dueUpdate });
      
      let successMessage = '';
      switch (when) {
        case 'tomorrow':
          successMessage = `✅ Moved "${taskTitle}" to tomorrow at 9:30am`;
          break;
        case 'today':
          successMessage = `✅ Moved "${taskTitle}" to today`;
          break;
        case 'undate':
          successMessage = `✅ Removed due date from "${taskTitle}"`;
          break;
      }
      
      return {
        type: 'success',
        message: successMessage
      };
      
    } catch (error) {
      console.error('Error snoozing task:', error);
      return {
        type: 'error',
        message: 'Failed to update the task. Please try again.'
      };
    }
  }

  /**
   * Discard current session
   */
  async discard(userId: string): Promise<FlowCoachResponse> {
    const session = await this.sessions.getLastPendingSession(userId);
    
    if (!session) {
      return {
        type: 'error',
        message: 'No pending session to discard.'
      };
    }
    
    await this.sessions.updateSession(session.id, 'discarded');
    
    return {
      type: 'success',
      message: 'Session discarded. Your tasks were not created.'
    };
  }

  /**
   * Clear all pending sessions for debugging
   */
  async clearAll(userId: string): Promise<FlowCoachResponse> {
    try {
      await this.sessions.clearAllPendingSessions(userId);
      return {
        type: 'success',
        message: 'All pending sessions cleared. Fresh start!'
      };
    } catch (error) {
      console.error('Error clearing sessions:', error);
      return {
        type: 'error',
        message: 'Failed to clear sessions.'
      };
    }
  }
  
  private formatTaskPreview(quickWins: ParsedTask[], projects: ParsedTask[]): string {
    let preview = "**Here's your chaos, cleaned up 👇**\n\n";
    let index = 1;
    
    if (quickWins.length > 0) {
      preview += "**Quick Wins:**\n";
      quickWins.forEach((task) => {
        preview += `${index}. [${task.duration_bucket}] ${task.title}\n`;
        index++;
      });
      preview += '\n';
    }
    
    if (projects.length > 0) {
      preview += "**Projects:**\n";
      projects.forEach((task) => {
        preview += `${index}. [${task.duration_bucket || '30+min'}] ${task.title}`;
        if (task.is_project_candidate) preview += ' 🔄';
        preview += '\n';
        
        if (task.subtasks) {
          task.subtasks.forEach(st => {
            preview += `   └ [${st.duration_bucket}] ${st.title}\n`;
          });
        }
        index++;
      });
      preview += '\n';
    }
    
    preview += "**Actions:** `accept`, `discard`, `edit #2 -> new title`, `breakdown #3`";
    
    return preview.trim();
  }
  
  private findTaskInSession(session: Session, taskRef: string): ParsedTask | null {
    // Try index first (#1, #2, etc.)
    const indexMatch = taskRef.match(/^#?(\d+)$/);
    if (indexMatch) {
      const index = parseInt(indexMatch[1]) - 1;
      return session.parsed[index] || null;
    }
    
    // Try text match
    return session.parsed.find(task => 
      task.title.toLowerCase().includes(taskRef.toLowerCase()) ||
      taskRef.toLowerCase().includes(task.title.toLowerCase())
    ) || null;
  }
  
  /**
   * Clean up resources
   */
  close(): void {
    this.sessions.close();
    this.threadState.close();
  }
}
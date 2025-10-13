/**
 * Calendar integration service for read-only context
 * Currently supports Google Calendar
 */

import { google, calendar_v3 } from 'googleapis';
import { OAuth2Client } from 'google-auth-library';

export interface CalendarEvent {
  id: string;
  summary: string;
  start: Date;
  end: Date;
  description?: string;
  location?: string;
  attendees?: string[];
}

export interface CalendarContext {
  upcomingEvents: CalendarEvent[];
  freeSlots: { start: Date; end: Date; duration: number }[];
  busyHours: number;
  meetingLoad: 'light' | 'moderate' | 'heavy';
}

export class CalendarService {
  private calendar: calendar_v3.Calendar;
  private auth: OAuth2Client;
  
  constructor(credentials: {
    client_id: string;
    client_secret: string;
    refresh_token: string;
  }) {
    this.auth = new google.auth.OAuth2(
      credentials.client_id,
      credentials.client_secret,
      'urn:ietf:wg:oauth:2.0:oob'
    );
    
    this.auth.setCredentials({
      refresh_token: credentials.refresh_token
    });
    
    this.calendar = google.calendar({ version: 'v3', auth: this.auth });
  }
  
  /**
   * Get calendar context for the next 24 hours
   */
  async getContext(hours = 24): Promise<CalendarContext> {
    const now = new Date();
    const endTime = new Date(now.getTime() + hours * 60 * 60 * 1000);
    
    try {
      // Fetch events
      const response = await this.calendar.events.list({
        calendarId: 'primary',
        timeMin: now.toISOString(),
        timeMax: endTime.toISOString(),
        singleEvents: true,
        orderBy: 'startTime'
      });
      
      const events = response.data.items || [];
      
      // Convert to our format
      const upcomingEvents = events.map(event => ({
        id: event.id || '',
        summary: event.summary || 'No title',
        start: new Date(event.start?.dateTime || event.start?.date || ''),
        end: new Date(event.end?.dateTime || event.end?.date || ''),
        description: event.description || undefined,
        location: event.location || undefined,
        attendees: event.attendees?.map(a => a.email || '').filter(e => e)
      }));
      
      // Calculate free slots and busy hours
      const freeSlots = this.calculateFreeSlots(upcomingEvents, now, endTime);
      const busyHours = this.calculateBusyHours(upcomingEvents);
      
      // Determine meeting load
      const meetingLoad = busyHours < 2 ? 'light' : 
                         busyHours < 4 ? 'moderate' : 'heavy';
      
      return {
        upcomingEvents,
        freeSlots,
        busyHours,
        meetingLoad
      };
      
    } catch (error) {
      console.error('Calendar fetch failed:', error);
      // Return empty context on error
      return {
        upcomingEvents: [],
        freeSlots: [{ start: now, end: endTime, duration: hours * 60 }],
        busyHours: 0,
        meetingLoad: 'light'
      };
    }
  }
  
  /**
   * Get a summary string of today's schedule
   */
  async getTodaySummary(): Promise<string> {
    const context = await this.getContext(12); // Next 12 hours
    
    if (context.upcomingEvents.length === 0) {
      return "Your calendar is clear for the rest of today - perfect time to tackle some tasks!";
    }
    
    const now = new Date();
    const upcomingToday = context.upcomingEvents
      .filter(e => e.start.toDateString() === now.toDateString())
      .slice(0, 5); // Show up to 5 events
    
    let summary = '';
    
    if (upcomingToday.length === 0) {
      summary = "No more meetings today! Your afternoon is wide open.";
    } else {
      const eventList = upcomingToday
        .map(e => `• ${this.formatTime(e.start)}: ${e.summary}`)
        .join('\n');
      
      summary = `Here's your schedule:\n\n${eventList}`;
      
      // Add meeting load context
      if (context.meetingLoad === 'heavy') {
        summary += '\n\nLooks like a busy day! Maybe save complex tasks for tomorrow?';
      } else if (context.meetingLoad === 'light') {
        summary += '\n\nPretty light schedule - good day for deep work!';
      }
    }
    
    // Find the biggest free slot
    const freeSlots = context.freeSlots
      .filter(s => s.duration >= 30) // Only show 30+ min slots
      .sort((a, b) => b.duration - a.duration);
    
    if (freeSlots.length > 0) {
      const bigSlot = freeSlots[0];
      summary += `\n\nBiggest free block: ${Math.floor(bigSlot.duration / 60)} hours at ${this.formatTime(bigSlot.start)}`;
    }
    
    return summary;
  }
  
  private calculateFreeSlots(
    events: CalendarEvent[], 
    start: Date, 
    end: Date
  ): { start: Date; end: Date; duration: number }[] {
    const slots: { start: Date; end: Date; duration: number }[] = [];
    let currentTime = new Date(start);
    
    // Sort events by start time
    const sorted = [...events].sort((a, b) => a.start.getTime() - b.start.getTime());
    
    for (const event of sorted) {
      if (event.start > currentTime) {
        const duration = Math.floor((event.start.getTime() - currentTime.getTime()) / 60000);
        if (duration >= 15) { // Only include slots 15+ minutes
          slots.push({ start: currentTime, end: event.start, duration });
        }
      }
      currentTime = event.end > currentTime ? event.end : currentTime;
    }
    
    // Check for slot after last event
    if (currentTime < end) {
      const duration = Math.floor((end.getTime() - currentTime.getTime()) / 60000);
      if (duration >= 15) {
        slots.push({ start: currentTime, end, duration });
      }
    }
    
    return slots;
  }
  
  private calculateBusyHours(events: CalendarEvent[]): number {
    let totalMinutes = 0;
    for (const event of events) {
      const duration = (event.end.getTime() - event.start.getTime()) / 60000;
      totalMinutes += duration;
    }
    return Math.round(totalMinutes / 60);
  }
  
  private formatTime(date: Date): string {
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  }
}

/**
 * Setup instructions for Google Calendar:
 * 
 * 1. Go to Google Cloud Console
 * 2. Enable Calendar API
 * 3. Create OAuth2 credentials
 * 4. Get refresh token using OAuth playground
 * 5. Add to .env:
 *    GOOGLE_CLIENT_ID=your_client_id
 *    GOOGLE_CLIENT_SECRET=your_client_secret  
 *    GOOGLE_REFRESH_TOKEN=your_refresh_token
 */
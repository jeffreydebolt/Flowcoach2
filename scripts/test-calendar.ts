/**
 * Test script for Google Calendar integration
 */

import dotenv from 'dotenv';
import { CalendarService } from '../src/services/calendarService';

dotenv.config();

async function testCalendar() {
  console.log('🗓️  Testing Google Calendar integration...\n');
  
  const calendarService = new CalendarService({
    client_id: process.env.GOOGLE_CLIENT_ID!,
    client_secret: process.env.GOOGLE_CLIENT_SECRET!,
    refresh_token: process.env.GOOGLE_REFRESH_TOKEN!
  });
  
  try {
    // Get calendar context
    const context = await calendarService.getContext(24);
    
    console.log(`📅 Calendar Context (next 24 hours):`);
    console.log(`- Upcoming events: ${context.upcomingEvents.length}`);
    console.log(`- Meeting load: ${context.meetingLoad}`);
    console.log(`- Busy hours: ${context.busyHours}`);
    console.log(`- Free slots: ${context.freeSlots.length}\n`);
    
    // Show upcoming events
    if (context.upcomingEvents.length > 0) {
      console.log('📌 Upcoming events:');
      context.upcomingEvents.slice(0, 5).forEach(event => {
        console.log(`  - ${event.start.toLocaleTimeString()}: ${event.summary}`);
      });
    }
    
    // Get today's summary
    console.log('\n📝 Today\'s Summary:');
    const summary = await calendarService.getTodaySummary();
    console.log(summary);
    
  } catch (error) {
    console.error('❌ Calendar test failed:', error);
  }
}

testCalendar();
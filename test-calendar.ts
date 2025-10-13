import { CalendarService } from './src/services/calendarService';
import dotenv from 'dotenv';

dotenv.config();

async function testCalendar() {
  console.log('🗓️  Testing Google Calendar integration...');
  
  const calendarService = new CalendarService({
    client_id: process.env.GOOGLE_CLIENT_ID!,
    client_secret: process.env.GOOGLE_CLIENT_SECRET!,
    refresh_token: process.env.GOOGLE_REFRESH_TOKEN!
  });
  
  try {
    const context = await calendarService.getContext(24);
    
    console.log('📅 Calendar Context (next 24 hours):');
    console.log('- Upcoming events:', context.upcomingEvents.length);
    console.log('- Meeting load:', context.meetingLoad);
    console.log('- Busy hours:', context.busyHours);
    console.log('- Free slots:', context.freeSlots.length);
    
    if (context.upcomingEvents.length > 0) {
      console.log('\n📌 Next few events:');
      context.upcomingEvents.slice(0, 3).forEach(event => {
        console.log(`  - ${event.start.toLocaleTimeString()}: ${event.summary}`);
      });
    }
    
    const summary = await calendarService.getTodaySummary();
    console.log('\n📝 Today\'s Summary:');
    console.log(summary);
    
  } catch (error) {
    console.error('❌ Calendar test failed:', error);
  }
}

testCalendar();
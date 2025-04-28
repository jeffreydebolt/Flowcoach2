"""
Calendar service for FlowCoach.

This module provides a service for interacting with Google Calendar.
"""

import logging
import os
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional, Union

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

class CalendarService:
    """Service for interacting with Google Calendar API."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Calendar service.
        
        Args:
            config: Calendar configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.creds = None
        self._calendar_service = None
        
        # Google Calendar API scopes
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        # Try to initialize the service
        self._initialize_service()
    
    def _initialize_service(self) -> None:
        """Initialize the Google Calendar service."""
        try:
            # Check for token file
            token_path = 'tokens/default_token.json'
            if os.path.exists(token_path):
                self.logger.info("Loading credentials from token file")
                try:
                    self.creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
                except Exception as e:
                    self.logger.error(f"Error loading credentials: {e}")
                    self.creds = None
            
            # If credentials are expired but have refresh token, refresh them
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.logger.info("Refreshing expired credentials")
                try:
                    self.creds.refresh(Request())
                    # Save refreshed credentials
                    with open(token_path, 'w') as token:
                        token.write(self.creds.to_json())
                except Exception as e:
                    self.logger.error(f"Error refreshing credentials: {e}")
                    self.creds = None
            
            # If no valid credentials, log warning
            if not self.creds or not self.creds.valid:
                self.logger.warning(
                    "No valid credentials found. Calendar functionality will be limited. "
                    "Run authenticate_calendar.py to set up Google Calendar access."
                )
                return
            
            # Build the service
            try:
                self._calendar_service = build('calendar', 'v3', credentials=self.creds)
                self.logger.info("Google Calendar service initialized successfully")
            except Exception as e:
                self.logger.error(f"Error building calendar service: {e}")
                self._calendar_service = None
                
        except Exception as e:
            self.logger.error(f"Error initializing Google Calendar service: {e}")
            self._calendar_service = None
    
    @property
    def calendar_service(self):
        """Get calendar service instance."""
        if not self._calendar_service:
            self.logger.error("Google Calendar service not initialized")
            raise ValueError("Google Calendar service not initialized")
        return self._calendar_service
    
    def get_events(
        self,
        user_id: str,
        start_date: Union[datetime, str],
        end_date: Union[datetime, str],
        calendar_id: str = 'primary'
    ) -> List[Dict[str, Any]]:
        """
        Get events from Google Calendar.
        
        Args:
            user_id: User ID (for future multi-user support)
            start_date: Start date/time
            end_date: End date/time
            calendar_id: Calendar ID
            
        Returns:
            List of processed calendar events
        """
        try:
            # Ensure we have a service
            if not self._calendar_service:
                self.logger.error("Calendar service not available")
                return []
            
            # Convert string dates to datetime if needed
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date)
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date)
            
            # Format dates for API
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
            
            # Call Google Calendar API
            events_result = self.calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=start_date_str,
                timeMax=end_date_str,
                singleEvents=True,
                orderBy='startTime',
                maxResults=100
            ).execute()
            
            events = []
            items = events_result.get('items', [])
            self.logger.info(f"Retrieved {len(items)} events from Google Calendar")
            
            # Process each event
            for event in items:
                # Skip events marked as 'transparent' (free) availability
                if event.get('transparency') == 'transparent':
                    continue
                
                # Process event based on type (all-day or timed)
                if 'date' in event['start']:
                    processed_event = self._process_all_day_event(event)
                else:
                    processed_event = self._process_timed_event(event)
                
                events.append(processed_event)
            
            return events
            
        except Exception as e:
            self.logger.error(f"Error getting events: {e}")
            return []
    
    def _process_all_day_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an all-day event.
        
        Args:
            event: Google Calendar event
            
        Returns:
            Processed event dictionary
        """
        # Parse the date strings
        start_date = datetime.fromisoformat(event['start']['date'])
        end_date = datetime.fromisoformat(event['end']['date'])
        
        # Google Calendar API returns the day after the end date for all-day events
        # So we need to subtract one day to get the actual end date
        end_date = end_date - timedelta(days=1)
        
        return {
            'id': event.get('id', ''),
            'summary': event.get('summary', 'No title'),
            'start_time': datetime.combine(start_date, time(0, 0)),
            'end_time': datetime.combine(end_date, time(23, 59, 59)),
            'duration_minutes': int(((end_date - start_date).days + 1) * 24 * 60),
            'is_all_day': True,
            'attendees': event.get('attendees', []),
            'description': event.get('description', '')
        }
    
    def _process_timed_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a timed event.
        
        Args:
            event: Google Calendar event
            
        Returns:
            Processed event dictionary
        """
        try:
            # Handle 'Z' UTC indicator by replacing with +00:00 for ISO format
            start_str = event['start']['dateTime'].replace('Z', '+00:00')
            end_str = event['end']['dateTime'].replace('Z', '+00:00')
            
            # Parse ISO format strings to datetime objects with timezone info
            start_time = datetime.fromisoformat(start_str)
            end_time = datetime.fromisoformat(end_str)
            
            return {
                'id': event.get('id', ''),
                'summary': event.get('summary', 'No title'),
                'start_time': start_time,
                'end_time': end_time,
                'duration_minutes': int((end_time - start_time).total_seconds() / 60),
                'is_all_day': False,
                'attendees': event.get('attendees', []),
                'description': event.get('description', '')
            }
        except Exception as e:
            self.logger.error(f"Error processing timed event: {e}")
            
            # Return a fallback event with minimal information
            return {
                'id': event.get('id', ''),
                'summary': event.get('summary', 'No title') + ' (Error processing time)',
                'start_time': datetime.now(),
                'end_time': datetime.now() + timedelta(minutes=30),
                'duration_minutes': 30,
                'is_all_day': False,
                'attendees': event.get('attendees', []),
                'description': event.get('description', '')
            }
    
    def create_event(
        self,
        user_id: str,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: str = '',
        calendar_id: str = 'primary'
    ) -> Optional[Dict[str, Any]]:
        """
        Create a calendar event.
        
        Args:
            user_id: User ID (for future multi-user support)
            summary: Event summary/title
            start_time: Start time
            end_time: End time
            description: Event description
            calendar_id: Calendar ID
            
        Returns:
            Created event or None if creation failed
        """
        try:
            # Ensure we have a service
            if not self._calendar_service:
                self.logger.error("Calendar service not available")
                return None
            
            # Format times for API
            start_time_str = start_time.isoformat()
            end_time_str = end_time.isoformat()
            
            # Create event
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time_str,
                    'timeZone': 'UTC'  # Use user's timezone in a real implementation
                },
                'end': {
                    'dateTime': end_time_str,
                    'timeZone': 'UTC'  # Use user's timezone in a real implementation
                }
            }
            
            created_event = self.calendar_service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            
            self.logger.info(f"Event created: {created_event.get('htmlLink')}")
            
            # Process the created event
            if 'date' in created_event['start']:
                return self._process_all_day_event(created_event)
            else:
                return self._process_timed_event(created_event)
            
        except Exception as e:
            self.logger.error(f"Error creating event: {e}")
            return None
    
    def find_focus_blocks(
        self,
        user_id: str,
        date: Optional[datetime] = None,
        work_start_hour: Optional[int] = None,
        work_end_hour: Optional[int] = None,
        min_block_minutes: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find available focus blocks in calendar.
        
        Args:
            user_id: User ID
            date: Date to find focus blocks for (defaults to today)
            work_start_hour: Start of work day (defaults to config value)
            work_end_hour: End of work day (defaults to config value)
            min_block_minutes: Minimum duration in minutes (defaults to config value)
            
        Returns:
            List of focus blocks
        """
        try:
            # Use defaults from config if not provided
            if work_start_hour is None:
                work_start_hour = self.config["work_start_hour"]
            if work_end_hour is None:
                work_end_hour = self.config["work_end_hour"]
            if min_block_minutes is None:
                min_block_minutes = self.config["min_focus_block_minutes"]
            
            # Use today if date not provided
            if date is None:
                date = datetime.now().date()
            elif isinstance(date, datetime):
                date = date.date()
            
            # Set time boundaries for the day
            start_datetime = datetime.combine(date, time(0, 0, 0))
            end_datetime = datetime.combine(date, time(23, 59, 59))
            
            # Get events for the day
            events = self.get_events(user_id, start_datetime, end_datetime)
            
            # Calculate focus blocks
            focus_blocks = self._calculate_focus_blocks(
                events,
                work_start_hour,
                work_end_hour,
                min_block_minutes
            )
            
            return focus_blocks
            
        except Exception as e:
            self.logger.error(f"Error finding focus blocks: {e}")
            return []
    
    def _calculate_focus_blocks(
        self,
        events: List[Dict[str, Any]],
        work_start_hour: int,
        work_end_hour: int,
        min_block_minutes: int
    ) -> List[Dict[str, Any]]:
        """
        Calculate available focus blocks based on calendar events.
        
        Args:
            events: List of calendar events
            work_start_hour: Start of work day (e.g., 9 for 9 AM)
            work_end_hour: End of work day (e.g., 17 for 5 PM)
            min_block_minutes: Minimum duration in minutes to consider a block
            
        Returns:
            List of focus blocks with start and end times
        """
        # Get the date from the first event, or use today if no events
        if events:
            day = events[0]["start_time"].date()
        else:
            day = datetime.now().date()
        
        # Set work day boundaries
        work_start = datetime.combine(day, time(hour=work_start_hour))
        work_end = datetime.combine(day, time(hour=work_end_hour))
        
        # Initialize available time with full work day
        available_blocks = [{"start": work_start, "end": work_end}]
        
        # Sort events by start time
        sorted_events = sorted(events, key=lambda x: x["start_time"])
        
        # Remove event times from available blocks
        for event in sorted_events:
            event_start = max(event["start_time"], work_start)
            event_end = min(event["end_time"], work_end)
            
            # Skip events outside work hours
            if event_end <= work_start or event_start >= work_end:
                continue
            
            new_blocks = []
            for block in available_blocks:
                # Event is completely outside this block
                if event_end <= block["start"] or event_start >= block["end"]:
                    new_blocks.append(block)
                # Event splits block in two
                elif event_start > block["start"] and event_end < block["end"]:
                    new_blocks.append({"start": block["start"], "end": event_start})
                    new_blocks.append({"start": event_end, "end": block["end"]})
                # Event removes start of block
                elif event_start <= block["start"] and event_end > block["start"] and event_end < block["end"]:
                    new_blocks.append({"start": event_end, "end": block["end"]})
                # Event removes end of block
                elif event_start > block["start"] and event_start < block["end"] and event_end >= block["end"]:
                    new_blocks.append({"start": block["start"], "end": event_start})
                # Event completely covers block
                elif event_start <= block["start"] and event_end >= block["end"]:
                    pass  # Block is completely covered, don't add anything
            
            available_blocks = new_blocks
        
        # Filter blocks to find focus time (blocks >= min duration)
        focus_blocks = []
        for block in available_blocks:
            duration_minutes = int((block["end"] - block["start"]).total_seconds() / 60)
            
            if duration_minutes >= min_block_minutes:
                focus_blocks.append({
                    "start": block["start"],
                    "end": block["end"],
                    "duration_minutes": duration_minutes
                })
        
        return focus_blocks

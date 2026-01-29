#!/usr/bin/env python3

import datetime
import os.path
import json
from zoneinfo import ZoneInfo
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

CALENDAR_ID = 'YOUR_CALENDAR_ID_HERE'

LOCAL_TIMEZONE = 'America/New_York'

ALARM_TIMES = {
    'AM': ['06:52', '06:57', '06:59'],
    'MIDDAY': ['08:37', '08:42', '08:57'],
    'PM': ['09:02', '09:07', '09:11']
}

def get_calendar_service():
    creds = None
    
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('calendar', 'v3', credentials=creds)

def get_todays_shift():
    try:
        service = get_calendar_service()
        
        tz = ZoneInfo(LOCAL_TIMEZONE)
        now = datetime.datetime.now(tz)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + datetime.timedelta(days=1)
        
        time_min = today.isoformat()
        time_max = tomorrow.isoformat()
        
        print(f"Searching for events between {time_min} and {time_max}")
        
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            print('No events found for today.')
            return None
        
        shift_keywords = ['work', 'shift']
        
        for event in events:
            summary = event.get('summary', '').lower()
            start = event['start'].get('dateTime', event['start'].get('date'))
            
            print(f"Found event: {event.get('summary')} at {start}")
            
            if any(keyword in summary for keyword in shift_keywords):
                shift_info = {
                    'summary': event.get('summary'),
                    'start': start,
                    'description': event.get('description', ''),
                    'shift_type': determine_shift_type(summary, start)
                }
                return shift_info
        
        print('No shift events found for today.')
        return None
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def determine_shift_type(summary, start_time):
    try:
        if 'T' in start_time:
            dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            
            hour = dt.hour
            minute = dt.minute
            
            if (hour == 8 and minute == 0) or (hour == 8 and minute == 30):
                return 'AM'
            elif hour == 9 and minute == 0:
                return 'WEEKEND'
            elif (hour == 10 and minute == 0) or (hour == 10 and minute == 30):
                return 'MIDDAY'
            elif hour == 12 and minute == 0:
                return 'PM'
            else:
                return 'UNKNOWN'
    except Exception as e:
        print(f"Error parsing time: {e}")
        pass
    
    return 'UNKNOWN'

def get_alarm_times_for_shift(shift_type):
    if shift_type in ALARM_TIMES:
        tz = ZoneInfo(LOCAL_TIMEZONE)
        today = datetime.datetime.now(tz).date()
        alarm_datetimes = []
        
        for time_str in ALARM_TIMES[shift_type]:
            hour, minute = map(int, time_str.split(':'))
            alarm_dt = datetime.datetime.combine(today, datetime.time(hour, minute))
            alarm_dt = alarm_dt.replace(tzinfo=tz)
            alarm_datetimes.append(alarm_dt)
        
        return alarm_datetimes
    return []

def save_alarm_schedule(shift_info):
    tz = ZoneInfo(LOCAL_TIMEZONE)
    
    if not shift_info or shift_info['shift_type'] == 'UNKNOWN':
        alarm_data = {
            'shift_date': datetime.datetime.now(tz).strftime('%Y-%m-%d'),
            'has_shift': False,
            'alarms': []
        }
    else:
        alarm_times = get_alarm_times_for_shift(shift_info['shift_type'])
        alarm_data = {
            'shift_date': datetime.datetime.now(tz).strftime('%Y-%m-%d'),
            'has_shift': True,
            'shift_type': shift_info['shift_type'],
            'shift_start': shift_info['start'],
            'alarms': [dt.strftime('%Y-%m-%d %H:%M:%S') for dt in alarm_times]
        }
    
    with open('alarm_schedule.json', 'w') as f:
        json.dump(alarm_data, f, indent=2)
    
    return alarm_data

def main():
    tz = ZoneInfo(LOCAL_TIMEZONE)
    print("Checking calendar for today's shift...")
    print(f"Date: {datetime.datetime.now(tz).strftime('%Y-%m-%d')}")
    print("-" * 50)
    
    shift = get_todays_shift()
    
    if shift:
        print(f"Shift found!")
        print(f"  Summary: {shift['summary']}")
        print(f"  Start time: {shift['start']}")
        print(f"  Shift type: {shift['shift_type']}")
        if shift['description']:
            print(f"  Description: {shift['description']}")
        
        if shift['shift_type'] != 'UNKNOWN' and shift['shift_type'] != 'WEEKEND':
            alarm_times = get_alarm_times_for_shift(shift['shift_type'])
            print(f"\nScheduled alarm calls:")
            for i, alarm_time in enumerate(alarm_times, 1):
                print(f"  Call {i}: {alarm_time.strftime('%I:%M %p')}")
            
            alarm_data = save_alarm_schedule(shift)
            print(f"\nAlarm schedule saved to alarm_schedule.json")
        else:
            print(f"\nNo alarms scheduled (shift type: {shift['shift_type']})")
            save_alarm_schedule(shift)
    else:
        print("No shift today - it's a day off!")
        save_alarm_schedule(None)
    
    return shift

if __name__ == '__main__':
    main()

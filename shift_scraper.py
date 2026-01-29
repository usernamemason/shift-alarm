#!/usr/bin/env python3

import json
import smtplib
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from zoneinfo import ZoneInfo

EMAIL_USER = 'your_email@gmail.com'
EMAIL_PASSWORD = 'your_app_password_here'
RECIPIENT_EMAIL = 'recipient_email@icloud.com'

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

LOCAL_TIMEZONE = 'America/New_York'
ALARM_SCHEDULE_FILE = 'alarm_schedule.json'

sent_alarms = set()

def load_alarm_schedule():
    try:
        with open(ALARM_SCHEDULE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {ALARM_SCHEDULE_FILE} not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: {ALARM_SCHEDULE_FILE} is not valid JSON.")
        return None

def send_alarm_email(alarm_time):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = 'ALARM TRIGGER'
        
        body = f"Alarm triggered at {alarm_time}"
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"Alarm email sent for {alarm_time}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def check_and_send_alarms():
    schedule = load_alarm_schedule()
    if not schedule or not schedule.get('has_shift', False):
        return
    
    tz = ZoneInfo(LOCAL_TIMEZONE)
    current_time = datetime.now(tz)
    current_time_str = current_time.strftime('%Y-%m-%d %H:%M')
    
    today = current_time.strftime('%Y-%m-%d')
    if schedule.get('shift_date') != today:
        return
    
    for alarm in schedule.get('alarms', []):
        alarm_dt = datetime.strptime(alarm, '%Y-%m-%d %H:%M:%S')
        alarm_time_str = alarm_dt.strftime('%Y-%m-%d %H:%M')
        
        if alarm_time_str == current_time_str and alarm not in sent_alarms:
            print(f"ALARM TIME! Sending email for {alarm}")
            if send_alarm_email(alarm):
                sent_alarms.add(alarm)

def is_within_alarm_window():
    tz = ZoneInfo(LOCAL_TIMEZONE)
    current_time = datetime.now(tz)
    current_hour = current_time.hour
    current_minute = current_time.minute
    
    if current_hour == 6 and current_minute >= 50:
        return True
    elif current_hour == 7 and current_minute <= 5:
        return True
    elif current_hour == 8 and current_minute >= 35:
        return True
    elif current_hour == 9 and current_minute <= 15:
        return True
    else:
        return False

def main():
    print("=== Alarm Email Sender Started ===")
    print(f"Email: {EMAIL_USER} → {RECIPIENT_EMAIL}")
    print("-" * 50)
    
    last_check_day = None
    while True:
        try:
            tz = ZoneInfo(LOCAL_TIMEZONE)
            current_day = datetime.now(tz).strftime('%Y-%m-%d')
            
            if last_check_day != current_day:
                sent_alarms.clear()
                last_check_day = current_day
            
            if is_within_alarm_window():
                check_and_send_alarms()
                time.sleep(60)
            else:
                time.sleep(300)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()

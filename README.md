# Automated Shift Alarm System

An intelligent alarm system that monitors a shared Google Calendar for shift schedules and automatically triggers wake-up calls via iOS Shortcuts and FaceTime. Built for high availability on a Proxmox cluster with persistent NFS storage.

## Overview

This system integrates multiple technologies to create a reliable, automated wake-up solution based on dynamic work schedules:

1. **Calendar Scraper** checks Google Calendar daily for shift information
2. **Alarm Sender** monitors the schedule and sends email triggers at precise times
3. **iOS Shortcuts** receives emails and initiates FaceTime calls automatically

## Architecture

```
┌─────────────────────┐
│  Google Calendar    │
│   (Shift Schedule)  │
└──────────┬──────────┘
           │
           │ OAuth 2.0 API
           ▼
┌─────────────────────┐      ┌──────────────────┐
│  shift_scraper.py   │─────▶│alarm_schedule.json│
│  (Runs at 12:01 AM) │      │  (Persistent NFS) │
└─────────────────────┘      └─────────┬─────────┘
                                       │
                                       │ Read
                                       ▼
                            ┌─────────────────────┐
                            │  alarm_sender.py    │
                            │ (Continuous Monitor)│
                            └──────────┬──────────┘
                                       │
                                       │ SMTP Email
                                       ▼
                            ┌─────────────────────┐
                            │   iCloud Email      │
                            │  (Push Delivery)    │
                            └──────────┬──────────┘
                                       │
                                       │ iOS Notification
                                       ▼
                            ┌─────────────────────┐
                            │   iOS Shortcuts     │
                            │ (Auto FaceTime Call)│
                            └─────────────────────┘
```

## Features

- **Dynamic Schedule Detection**: Automatically identifies AM, Midday, and PM shifts based on calendar event times
- **Multiple Alarm Times**: Sends 3 alarm emails per shift for redundancy
- **High Availability**: Deployed on Proxmox cluster with automatic failover
- **Persistent Storage**: All data stored on NFS-backed storage for reliability
- **Email Notifications**: Uses Gmail SMTP to trigger iOS Shortcuts
- **Timezone Aware**: Handles timezone conversions properly
- **Efficient Monitoring**: Only actively checks during alarm windows to conserve resources

## Technologies Used

- **Python 3.12**: Core scripting language
- **Google Calendar API**: Calendar integration via OAuth 2.0
- **Gmail SMTP**: Email delivery for notifications
- **Proxmox VE**: Virtualization and high availability
- **LXC Containers**: Lightweight containerization
- **Synology NAS**: NFS persistent storage
- **systemd**: Service management and scheduling
- **iOS Shortcuts**: Automation trigger on iPhone

## Requirements

### Hardware
- Proxmox VE cluster (or single node)
- NFS storage (Synology NAS or similar)
- iPhone with iOS 15+ (for Shortcuts automation)

### Software
- Python 3.12+
- Ubuntu 22.04 LXC container
- Google Cloud Project with Calendar API enabled

### Python Dependencies
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client tzdata
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/shift-alarm-system.git
cd shift-alarm-system
```

### 2. Set Up Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download credentials and save as `credentials.json`

### 3. Configure the Scripts

```bash
# Copy example config
cp credentials.example.json credentials.json

# Edit shift_scraper.py
# Set your CALENDAR_ID

# Edit alarm_sender.py
# Set EMAIL_USER, EMAIL_PASSWORD, and RECIPIENT_EMAIL
```

### 4. Generate Gmail App Password

1. Go to [Google Account App Passwords](https://myaccount.google.com/apppasswords)
2. Create app password for "Mail"
3. Use this password in `alarm_sender.py`

### 5. First Run (Authentication)

```bash
python3 shift_scraper.py
```

This will open a browser for OAuth authentication and create `token.json`.

### 6. Test the Alarm Sender

```bash
python3 alarm_sender.py
```

Press Ctrl+C to stop after verifying it starts correctly.

## Deployment on Proxmox

### Create LXC Container

1. Create Ubuntu 22.04 LXC container
2. Allocate: 512MB RAM, 1 CPU core, 4GB disk
3. Store container disk on NFS storage for HA
4. Configure networking (DHCP or static IP)

### Install Dependencies

```bash
apt update && apt install python3 python3-pip -y
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client tzdata --break-system-packages
```

### Transfer Files

```bash
scp shift_scraper.py root@container-ip:/opt/shift-alarm/
scp alarm_sender.py root@container-ip:/opt/shift-alarm/
scp credentials.json root@container-ip:/opt/shift-alarm/
scp token.json root@container-ip:/opt/shift-alarm/
```

### Set Up systemd Services

**Scraper Service** (`/etc/systemd/system/shift-scraper.service`):
```ini
[Unit]
Description=Shift Calendar Scraper
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/shift-alarm/shift_scraper.py
WorkingDirectory=/opt/shift-alarm

[Install]
WantedBy=multi-user.target
```

**Scraper Timer** (`/etc/systemd/system/shift-scraper.timer`):
```ini
[Unit]
Description=Run shift scraper daily at 12:01 AM

[Timer]
OnCalendar=00:01:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Alarm Sender Service** (`/etc/systemd/system/alarm-sender.service`):
```ini
[Unit]
Description=Alarm Email Sender
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/shift-alarm/alarm_sender.py
WorkingDirectory=/opt/shift-alarm
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start Services

```bash
systemctl daemon-reload
systemctl enable shift-scraper.timer
systemctl enable alarm-sender.service
systemctl start shift-scraper.timer
systemctl start alarm-sender.service
```

### Enable High Availability (Optional)

In Proxmox Web UI:
1. Datacenter → HA → Add
2. Select the container
3. Configure max restarts and relocations

## iOS Shortcuts Setup

### Create Email Automation

1. Open **Shortcuts** app on iPhone
2. Go to **Automation** tab
3. Create new **Personal Automation**
4. Select **Email** trigger
5. Configure:
   - **Sender**: Your alarm sender email
   - **Subject Contains**: "ALARM TRIGGER"
6. Enable **Run Immediately**
7. Add **FaceTime** action
8. Select contact to call
9. Save

**Note**: Recipient iPhone must use iCloud email for Push notifications. Gmail on iPhone Mail app only supports Fetch (15-60 min intervals).

## Configuration

### Shift Times

Edit `shift_scraper.py` to customize shift detection:

```python
def determine_shift_type(summary, start_time):
    # Customize these times based on your schedule
    if (hour == 8 and minute == 0) or (hour == 8 and minute == 30):
        return 'AM'
    elif (hour == 10 and minute == 0) or (hour == 10 and minute == 30):
        return 'MIDDAY'
    elif hour == 12 and minute == 0:
        return 'PM'
```

### Alarm Times

Edit `alarm_sender.py`:

```python
ALARM_TIMES = {
    'AM': ['06:52', '06:57', '06:59'],
    'MIDDAY': ['08:37', '08:42', '08:57'],
    'PM': ['09:02', '09:07', '09:11']
}
```

### Timezone

Change `LOCAL_TIMEZONE` in both scripts:

```python
LOCAL_TIMEZONE = 'America/New_York'  # Change to your timezone
```

## Monitoring

### Check Service Status

```bash
# Check if services are running
systemctl status alarm-sender.service
systemctl status shift-scraper.timer

# View logs
journalctl -u alarm-sender.service -f
journalctl -u shift-scraper.service -n 50
```

### Verify JSON Schedule

```bash
cat /opt/shift-alarm/alarm_schedule.json
```

Example output:
```json
{
  "shift_date": "2026-01-29",
  "has_shift": true,
  "shift_type": "MIDDAY",
  "shift_start": "2026-01-29T10:00:00-05:00",
  "alarms": [
    "2026-01-29 08:37:00",
    "2026-01-29 08:42:00",
    "2026-01-29 08:57:00"
  ]
}
```

## Troubleshooting

### Scraper Fails with Network Error

**Symptom**: `NameResolutionError` or can't reach `oauth2.googleapis.com`

**Solution**:
```bash
# Check DNS
ping google.com

# Fix DNS if needed
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf
```

### No Emails Being Sent

**Check**:
1. Verify `alarm_schedule.json` has today's date
2. Check alarm sender is running: `systemctl status alarm-sender.service`
3. Verify Gmail app password is correct
4. Check logs: `journalctl -u alarm-sender.service -n 50`

### iPhone Not Receiving Notifications

**Requirements**:
- Must use **iCloud email** (not Gmail) for Push delivery
- iOS Shortcuts automation must have **Run Immediately** enabled
- Notification settings must allow emails from sender

### Manual Testing

```bash
# Test scraper
cd /opt/shift-alarm
python3 shift_scraper.py

# Test sender (will run continuously)
python3 alarm_sender.py
# Press Ctrl+C to stop
```

## Future Improvements

- [ ] Add error email notifications when scraper fails
- [ ] Implement retry logic for network failures
- [ ] Add web dashboard for monitoring
- [ ] Support multiple users/calendars
- [ ] Add SMS backup option via Twilio
- [ ] Create Docker container version
- [ ] Add unit tests

## License

MIT License - feel free to use and modify for your own projects.

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

## Acknowledgments

- Built for personal use to solve a real-world scheduling problem
- Deployed on home Proxmox infrastructure
- Inspired by the need for a reliable, automated wake-up system

---

**Note**: This project requires access to a Google Calendar, Gmail account, and iPhone with iOS Shortcuts. All credentials must be kept secure and never committed to version control.

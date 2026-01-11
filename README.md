# Telegram Chat Backup Tool

A Python tool to backup Telegram chat history and media using the Telegram API.

## Features

- **Forum/Topic Support:** Automatically organizes messages into topic-specific folders for Telegram Groups with Forums enabled.
- **Protected Content:** Handles chats with restricted forwarding/downloads gracefully.
- **Flexible Identification:** Supports both `@username` and numeric `Chat ID` (e.g., `-100...`).
- **Media Download:** Optional media download with filtering by type (image, video, audio, etc.) and size.
- **IRC-style Logs:** Saves chat history in a clean, readable text format: `[timestamp] <username> message`.
- **Organized Output:** Creates a structured directory for each chat with a global log and topic logs.

## Installation

```bash
pip install -r requirements.txt
```

Requires Python 3.7 or later.

## Getting Telegram API Credentials

Before using this tool, you need to obtain API credentials from Telegram:

1. Go to https://my.telegram.org/auth
2. Log in with your phone number.
3. Click on "API development tools".
4. Fill in the application details.
5. Copy your `api_id` (numeric) and `api_hash` (hexadecimal string).

## Usage

```bash
python telegram_backup.py <api_id> <api_hash> <chat_input> [options]
```

### Examples

Download chat history only (using username):
```bash
python telegram_backup.py 12345678 abcdef1234567890 my_chat_username
```

Download using Chat ID and include media:
```bash
python telegram_backup.py 12345678 abcdef1234567890 -100123456789 --download-media
```

Download only images under 10MB:
```bash
python telegram_backup.py 12345678 abcdef1234567890 mychat --download-media --media-filter image --media-max-size 10485760
```

## Options

- `--download-media` - Enable media file downloads.
- `--media-filter TYPE` - Filter by type: `image`, `audio`, `video`, `other`, `all` (default: `all`).
- `--media-max-size BYTES` - Maximum file size in bytes.
- `--output-dir DIR` - Parent output directory (default: `backup`).

## Output Structure

The tool creates a dedicated folder for the chat:

```text
backup/
└── Chat_Name/
    ├── full_history.txt       # All messages from the chat
    └── topics/                # (For Forum Groups)
        └── Topic_Name/
            ├── history.txt    # Messages specific to this topic
            └── media/         # Media files for this topic
```

## Authentication

On first run, Telegram will send a verification code to your account. Enter it when prompted. A `session.session` file will be created to store your login. Keep this file secure.
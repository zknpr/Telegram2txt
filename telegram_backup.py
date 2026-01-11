#!/usr/bin/env python3
"""
Telegram Chat Backup Tool
Downloads chat history and media from a Telegram chat using the main Telegram API.
Supports Groups, Supergroups, Forums (Topics), and handles Protected Content.
"""

import os
import sys
import asyncio
import re
import mimetypes
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.errors import SecurityError
from telethon.errors.rpcerrorlist import (
    TimeoutError as TelegramTimeoutError,
    ChatForwardsRestrictedError,
)


def sanitize_filename(name):
    """
    Sanitize a string to be safe for filenames.
    Removes characters invalid in Windows/Unix filenames.
    """
    if not name:
        return "Unknown"
    # Remove invalid characters
    s = re.sub(r'[\\/*?:"<>|]', "", str(name))
    # Remove leading/trailing periods/spaces
    s = s.strip(". ")
    # Truncate if too long
    return s[:50] or "Unknown"


def get_media_type(message):
    """Determine the type of media in a message."""
    if not message.media:
        return None

    if isinstance(message.media, MessageMediaPhoto):
        return "image"

    if isinstance(message.media, MessageMediaDocument):
        doc = message.media.document
        if hasattr(doc, "mime_type") and doc.mime_type:
            mime = doc.mime_type.lower()
            if mime.startswith("image/"):
                return "image"
            elif mime.startswith("audio/"):
                return "audio"
            elif mime.startswith("video/"):
                return "video"

        for attr in doc.attributes:
            attr_type = type(attr).__name__
            if "Audio" in attr_type or "Voice" in attr_type:
                return "audio"
            elif "Video" in attr_type:
                return "video"
            elif "Photo" in attr_type:
                return "image"

        return "other"
    return "other"


def get_media_size(message):
    """Get the size of media in bytes."""
    if not message.media:
        return 0

    if isinstance(message.media, MessageMediaDocument):
        if hasattr(message.media.document, "size"):
            return message.media.document.size

    if isinstance(message.media, MessageMediaPhoto):
        if hasattr(message.media.photo, "sizes"):
            sizes = [s.size for s in message.media.photo.sizes if hasattr(s, "size")]
            return max(sizes) if sizes else 0

    return 0


def get_message_filename(message):
    """Generate a filename for the media in a message."""
    if not message.media:
        return None

    fname = f"msg_{message.id}"
    if isinstance(message.media, MessageMediaPhoto):
        return fname + ".jpg"

    if isinstance(message.media, MessageMediaDocument):
        for attr in message.media.document.attributes:
            if hasattr(attr, "file_name") and attr.file_name:
                fname = f"msg_{message.id}_{sanitize_filename(attr.file_name)}"
                break

        if "." not in fname:
            if hasattr(message.media.document, "mime_type"):
                ext = mimetypes.guess_extension(message.media.document.mime_type)
                if ext:
                    fname += ext
    return fname


def resolve_chat_input(chat_input):
    """Resolve the chat input to an ID or username."""
    s = str(chat_input).strip()
    if s.lstrip("-").isdigit():
        return int(s)
    return s


async def download_chat(
    api_id,
    api_hash,
    chat_input,
    output_dir="backup",
    download_media=False,
    media_filter="all",
    media_max_size=None,
):
    """
    Download chat history and media.
    """
    # Initialize client
    client = TelegramClient(
        "session", api_id, api_hash, timeout=60, request_retries=5, connection_retries=5
    )

    # Dictionary to keep track of open file handles for topics
    # Structure: { topic_id: file_handle }
    topic_files = {}
    # Structure: { topic_id: topic_name }
    topic_names = {}

    main_chat_file = None

    try:
        await client.start()
        print(f"Connected as {await client.get_me()}")

        # Resolve chat (handle ID or username)
        try:
            chat_entity = await client.get_entity(resolve_chat_input(chat_input))

            chat_title = getattr(
                chat_entity, "title", getattr(chat_entity, "username", "Chat")
            )
            print(f"Found chat: {chat_title} (ID: {chat_entity.id})")
        except Exception as e:
            print(f"Error: Could not find chat '{chat_input}': {e}")
            return

        # Prepare Main Output Directory
        safe_chat_title = sanitize_filename(chat_title)
        base_dir = os.path.join(output_dir, safe_chat_title)
        os.makedirs(base_dir, exist_ok=True)

        # Check if it's a forum (has topics)
        is_forum = getattr(chat_entity, "forum", False)
        if is_forum:
            print("Chat is a Forum. Fetching topic list...")
            try:
                async for topic in client.iter_forum_topics(chat_entity):
                    topic_names[topic.id] = sanitize_filename(topic.title)
                print(f"Found {len(topic_names)} topics.")
            except Exception as e:
                print(f"Warning: Could not fetch topic list: {e}")

        # Open main history file (Global Log)
        main_history_path = os.path.join(base_dir, "full_history.txt")
        main_chat_file = open(main_history_path, "w", encoding="utf-8")

        # Global counters
        stats = {
            "msg": 0,
            "media_ok": 0,
            "media_skip": 0,
            "media_filter": 0,
            "media_fail": 0,
            "media_protected": 0,
        }

        print(f"Starting download to '{base_dir}'...")
        if download_media:
            print(f"Media download enabled (Filter: {media_filter})")
        print("Press Ctrl+C to stop\n")

        async for message in client.iter_messages(chat_entity):
            stats["msg"] += 1

            # --- Identify Context (Topic vs General) ---
            topic_id = getattr(message, "topic_id", None)
            # Fallback for older messages in forums relying on reply_to
            if is_forum and not topic_id and message.reply_to:
                topic_id = (
                    getattr(message.reply_to, "forum_topic", False)
                    and message.reply_to.reply_to_msg_id
                )

            current_topic_name = "General"
            topic_subdir = base_dir  # Default to root

            if topic_id:
                # Get name or default to ID
                t_name = topic_names.get(topic_id, f"Topic_{topic_id}")
                current_topic_name = t_name

                # Create directory structure for this topic
                topic_subdir = os.path.join(base_dir, "topics", t_name)
                os.makedirs(topic_subdir, exist_ok=True)

                # Open/Get specific history file for this topic
                if topic_id not in topic_files:
                    tf_path = os.path.join(topic_subdir, "history.txt")
                    topic_files[topic_id] = open(tf_path, "w", encoding="utf-8")

            # --- Extract Sender and Time ---
            if message.sender:
                sender = getattr(message.sender, "username", None) or getattr(
                    message.sender, "first_name", "Unknown"
                )
            else:
                sender = "Unknown"

            timestamp = (
                message.date.strftime("%Y-%m-%d %H:%M:%S") if message.date else ""
            )

            # --- Format Log Line ---
            # Prefix with topic name in global log
            topic_tag = f" [Topic: {current_topic_name}]" if is_forum else ""
            log_line = f"[{timestamp}]{topic_tag} <{sender}> {message.message or ''}"

            # Write to Main Log
            main_chat_file.write(log_line + "\n")

            # Write to Topic Log (if applicable)
            if topic_id and topic_id in topic_files:
                # Remove the topic tag for the specific file as it's redundant there
                topic_log = f"[{timestamp}] <{sender}> {message.message or ''}"
                topic_files[topic_id].write(topic_log + "\n")

            # --- Handle Media ---
            if message.media:
                media_note = ""

                if not download_media:
                    stats["media_skip"] += 1
                    media_note = " [MEDIA: Not downloaded]"
                else:
                    m_type = get_media_type(message)
                    m_size = get_media_size(message)

                    # Filters
                    if media_filter != "all" and m_type != media_filter:
                        stats["media_filter"] += 1
                        media_note = f" [MEDIA: Filtered ({m_type})]"
                    elif media_max_size and m_size > media_max_size:
                        stats["media_filter"] += 1
                        media_note = f" [MEDIA: Too large ({m_size}b)]"
                    else:
                        # Attempt Download
                        media_folder = os.path.join(topic_subdir, "media")
                        os.makedirs(media_folder, exist_ok=True)

                        # Generate filename
                        fname = get_message_filename(message)
                        out_path = os.path.join(media_folder, fname)

                        try:
                            # Progress callback
                            print(
                                f"  DL: {fname} ({current_topic_name}) ",
                                end="",
                                flush=True,
                            )

                            await client.download_media(message, out_path)

                            print(" ✓")
                            stats["media_ok"] += 1
                            media_note = f" [MEDIA: {fname}]"

                        except (ChatForwardsRestrictedError, SecurityError):
                            print(" RESTRICTED")
                            stats["media_protected"] += 1
                            media_note = " [MEDIA: Protected Content - Download Denied]"
                        except Exception as e:
                            print(f" FAILED: {str(e)[:30]}")
                            stats["media_fail"] += 1
                            media_note = f" [MEDIA: Failed - {str(e)}]"

                # Append Media Note to logs
                main_chat_file.write(
                    f"[{timestamp}]{topic_tag} <{sender}>{media_note}\n"
                )
                if topic_id and topic_id in topic_files:
                    topic_files[topic_id].write(
                        f"[{timestamp}] <{sender}>{media_note}\n"
                    )

            # Console Status
            if stats["msg"] % 50 == 0:
                print(
                    f"Processed: {stats['msg']} msgs | Saved: {stats['media_ok']} | "
                    f"Protected: {stats['media_protected']} | Failed: {stats['media_fail']}"
                )

        # Final Summary
        print(f"\n{'='*60}")
        print("Backup Complete")
        print(f"Messages: {stats['msg']}")
        print(f"Media Saved: {stats['media_ok']}")
        print(f"Media Protected (Skipped): {stats['media_protected']}")
        print(f"Media Failed: {stats['media_fail']}")
        print(f"Location: {base_dir}")
        print(f"{'='*60}")

    finally:
        # Close all file handles
        if main_chat_file:
            main_chat_file.close()
        for f in topic_files.values():
            f.close()
        await client.disconnect()


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python backup.py <api_id> <api_hash> <chat_input> [options]")
        print("chat_input can be a @username or a numeric ID (e.g. -100123456)")
        sys.exit(0)

    if len(sys.argv) < 4:
        print("Error: Missing arguments. Use --help.")
        sys.exit(1)

    api_id = int(sys.argv[1])
    api_hash = sys.argv[2]
    chat_input = sys.argv[3]

    # Simple arg parsing for options
    download_media = "--download-media" in sys.argv

    media_filter = "all"
    if "--media-filter" in sys.argv:
        try:
            idx = sys.argv.index("--media-filter")
            media_filter = sys.argv[idx + 1]
        except:
            pass

    media_max_size = None
    if "--media-max-size" in sys.argv:
        try:
            idx = sys.argv.index("--media-max-size")
            media_max_size = int(sys.argv[idx + 1])
        except:
            pass

    output_dir = "backup"
    if "--output-dir" in sys.argv:
        try:
            idx = sys.argv.index("--output-dir")
            output_dir = sys.argv[idx + 1]
        except:
            pass

    asyncio.run(
        download_chat(
            api_id,
            api_hash,
            chat_input,
            output_dir,
            download_media,
            media_filter,
            media_max_size,
        )
    )


if __name__ == "__main__":
    main()

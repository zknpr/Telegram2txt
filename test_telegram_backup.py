import unittest
from unittest.mock import MagicMock
import os
import sys

# Import functions to test
from telegram_backup import (
    sanitize_filename,
    get_media_type,
    get_media_size,
    get_message_filename,
    resolve_chat_input
)

class TestTelegramBackup(unittest.TestCase):

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("Normal Name"), "Normal Name")
        self.assertEqual(sanitize_filename("Name/With/Slashes"), "NameWithSlashes")
        self.assertEqual(sanitize_filename("Name?With*Invalid:Chars|"), "NameWithInvalidChars")
        self.assertEqual(sanitize_filename("  Trim Me.  "), "Trim Me")
        self.assertEqual(sanitize_filename(""), "Unknown")
        self.assertEqual(sanitize_filename(None), "Unknown")

    def test_resolve_chat_input(self):
        self.assertEqual(resolve_chat_input("123456"), 123456)
        self.assertEqual(resolve_chat_input("-100123456"), -100123456)
        self.assertEqual(resolve_chat_input("@username"), "@username")
        self.assertEqual(resolve_chat_input("  @username  "), "@username")
        self.assertEqual(resolve_chat_input("chatname"), "chatname")

    def test_get_media_type_none(self):
        message = MagicMock()
        message.media = None
        self.assertIsNone(get_media_type(message))

    def test_get_media_type_photo(self):
        from telethon.tl.types import MessageMediaPhoto
        message = MagicMock()
        message.media = MagicMock(spec=MessageMediaPhoto)
        self.assertEqual(get_media_type(message), "image")

    def test_get_message_filename_photo(self):
        from telethon.tl.types import MessageMediaPhoto
        message = MagicMock()
        message.id = 123
        message.media = MagicMock(spec=MessageMediaPhoto)
        self.assertEqual(get_message_filename(message), "msg_123.jpg")

    def test_get_message_filename_document_with_name(self):
        from telethon.tl.types import MessageMediaDocument
        message = MagicMock()
        message.id = 456
        attr = MagicMock()
        attr.file_name = "test.pdf"
        doc = MagicMock()
        doc.attributes = [attr]
        message.media = MagicMock(spec=MessageMediaDocument)
        message.media.document = doc
        self.assertEqual(get_message_filename(message), "msg_456_test.pdf")

    def test_get_message_filename_document_guess_ext(self):
        from telethon.tl.types import MessageMediaDocument
        message = MagicMock()
        message.id = 789
        doc = MagicMock()
        doc.attributes = []
        doc.mime_type = "application/pdf"
        message.media = MagicMock(spec=MessageMediaDocument)
        message.media.document = doc
        # mimetypes.guess_extension might return .pdf or .pdf (system dependent but usually .pdf)
        fname = get_message_filename(message)
        self.assertTrue(fname.startswith("msg_789"))
        self.assertTrue(fname.endswith(".pdf"))

    def test_get_media_size_document(self):
        from telethon.tl.types import MessageMediaDocument
        message = MagicMock()
        doc = MagicMock()
        doc.size = 12345
        message.media = MagicMock(spec=MessageMediaDocument)
        message.media.document = doc
        self.assertEqual(get_media_size(message), 12345)

if __name__ == "__main__":
    unittest.main()
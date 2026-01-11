import unittest
from unittest.mock import MagicMock
import os
import sys

# Import functions to test
from telegram_backup import (
    sanitize_filename,
    get_media_type,
    get_media_size
)

class TestTelegramBackup(unittest.TestCase):

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("Normal Name"), "Normal Name")
        self.assertEqual(sanitize_filename("Name/With/Slashes"), "NameWithSlashes")
        self.assertEqual(sanitize_filename("Name?With*Invalid:Chars|"), "NameWithInvalidChars")
        self.assertEqual(sanitize_filename("  Trim Me.  "), "Trim Me")
        self.assertEqual(sanitize_filename(""), "Unknown")
        self.assertEqual(sanitize_filename(None), "Unknown")

    def test_get_media_type_none(self):
        message = MagicMock()
        message.media = None
        self.assertIsNone(get_media_type(message))

    def test_get_media_type_photo(self):
        from telethon.tl.types import MessageMediaPhoto
        message = MagicMock()
        message.media = MagicMock(spec=MessageMediaPhoto)
        self.assertEqual(get_media_type(message), "image")

    def test_get_media_type_document_video(self):
        from telethon.tl.types import MessageMediaDocument
        message = MagicMock()
        doc = MagicMock()
        doc.mime_type = "video/mp4"
        doc.attributes = []
        message.media = MagicMock(spec=MessageMediaDocument)
        message.media.document = doc
        self.assertEqual(get_media_type(message), "video")

    def test_get_media_type_document_audio(self):
        from telethon.tl.types import MessageMediaDocument
        message = MagicMock()
        doc = MagicMock()
        doc.mime_type = "audio/mpeg"
        doc.attributes = []
        message.media = MagicMock(spec=MessageMediaDocument)
        message.media.document = doc
        self.assertEqual(get_media_type(message), "audio")

    def test_get_media_size_document(self):
        from telethon.tl.types import MessageMediaDocument
        message = MagicMock()
        doc = MagicMock()
        doc.size = 12345
        message.media = MagicMock(spec=MessageMediaDocument)
        message.media.document = doc
        self.assertEqual(get_media_size(message), 12345)

    def test_get_media_size_photo(self):
        from telethon.tl.types import MessageMediaPhoto
        message = MagicMock()
        photo = MagicMock()
        size1 = MagicMock()
        size1.size = 100
        size2 = MagicMock()
        size2.size = 500
        photo.sizes = [size1, size2]
        message.media = MagicMock(spec=MessageMediaPhoto)
        message.media.photo = photo
        self.assertEqual(get_media_size(message), 500)

if __name__ == "__main__":
    unittest.main()

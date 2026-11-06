import os
import tempfile
import unittest
from unittest.mock import MagicMock

import requests

from put_esys.services.ekursy.draft_files import MoodleDraftFileManager


class TestDraftFileManager(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock(spec=requests.Session)
        self.manager = MoodleDraftFileManager(self.session)

    def test_upload_file_success(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"sample file content")
            tmp_path = tmp.name

        try:
            mock_resp = MagicMock()
            mock_resp.text = '{"event": "fileuploaded"}'
            mock_resp.raise_for_status = MagicMock()
            self.session.post.return_value = mock_resp

            result = self.manager.upload(
                file_path=tmp_path,
                itemid="12345",
                ctx_id="67890",
                sesskey="mock_sesskey",
                new_name="renamed.txt",
            )
            self.assertTrue(result)
            self.session.post.assert_called_once()
            call_kwargs = self.session.post.call_args[1]
            self.assertEqual(call_kwargs["data"]["itemid"], "12345")
            self.assertEqual(call_kwargs["data"]["title"], "renamed.txt")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_upload_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.manager.upload(
                file_path="nonexistent_file_path.xyz",
                itemid="123",
                ctx_id="456",
                sesskey="key",
            )

    def test_delete_file_success(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        self.session.get.return_value = mock_resp

        result = self.manager.delete(
            filename="test.pdf",
            itemid="12345",
            ctx_id="67890",
            sesskey="mock_key",
        )
        self.assertTrue(result)
        self.session.get.assert_called_once()
        params = self.session.get.call_args[1]["params"]
        self.assertEqual(params["action"], "deletedraft")
        self.assertEqual(params["filename"], "test.pdf")

    def test_rename_file_success(self):
        mock_resp = MagicMock()
        mock_resp.text = '{"result": "ok"}'
        mock_resp.raise_for_status = MagicMock()
        self.session.post.return_value = mock_resp

        result = self.manager.rename(
            filename="old.pdf",
            new_name="new.pdf",
            itemid="12345",
            ctx_id="67890",
            sesskey="mock_key",
        )
        self.assertTrue(result)
        self.session.post.assert_called_once()
        post_data = self.session.post.call_args[1]["data"]
        self.assertEqual(post_data["newfilename"], "new.pdf")
        self.assertEqual(post_data["filename"], "old.pdf")


if __name__ == "__main__":
    unittest.main()

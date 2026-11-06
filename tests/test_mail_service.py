import unittest

from put_esys.services.mail import decode_mime_header


class TestMailMimeDecoding(unittest.TestCase):
    def test_decode_plain_ascii(self):
        self.assertEqual(decode_mime_header("Simple subject"), "Simple subject")

    def test_decode_utf8_single_word(self):
        # =?UTF-8?B?xZtjacSFZ2E=?= is "ściąga"
        raw = "=?UTF-8?B?xZtjacSFZ2E=?="
        self.assertEqual(decode_mime_header(raw), "ściąga")

    def test_decode_multi_chunk_rfc2047(self):
        # Two consecutive encoded words
        raw = "=?UTF-8?B?W1dJUnQgSUldIA==?= =?UTF-8?B?T2fFgm9zemVuaWU=?="
        decoded = decode_mime_header(raw)
        self.assertIn("[WIRt II]", decoded)
        self.assertIn("Ogłoszenie", decoded)

    def test_decode_empty(self):
        self.assertEqual(decode_mime_header(""), "")
        self.assertEqual(decode_mime_header(None), "")


if __name__ == "__main__":
    unittest.main()

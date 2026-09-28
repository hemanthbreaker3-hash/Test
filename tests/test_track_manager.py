import unittest
from bot.helper.ext_utils.bot_utils import arg_parser
from bot.helper.ext_utils.track_manager import get_short_lang, format_tm_ui


class TestTrackManager(unittest.TestCase):
    def test_arg_parser(self):
        args = {"-trackmanager": False, "-tr": False, "-track": False, "-tm": False, "link": ""}
        items = ["http://example.com/file.mkv", "-tr"]
        arg_parser(items, args)
        self.assertTrue(args["-tr"])
        self.assertEqual(args["link"], "http://example.com/file.mkv")

        args2 = {"-trackmanager": False, "-tr": False, "-track": False, "-tm": False, "link": ""}
        items2 = ["http://example.com/file.mkv", "-trackmanager"]
        arg_parser(items2, args2)
        self.assertTrue(args2["-trackmanager"])

        args3 = {"-trackmanager": False, "-tr": False, "-track": False, "-tm": False, "link": ""}
        items3 = ["http://example.com/file.mkv", "-tm"]
        arg_parser(items3, args3)
        self.assertTrue(args3["-tm"])

        args4 = {"-trackmanager": False, "-tr": False, "-track": False, "-tm": False, "link": ""}
        items4 = ["http://example.com/file.mkv", "-track"]
        arg_parser(items4, args4)
        self.assertTrue(args4["-track"])

    def test_short_lang_formatting(self):
        self.assertEqual(get_short_lang({"tags": {"language": "telugu"}}), "Tel")
        self.assertEqual(get_short_lang({"tags": {"language": "tam"}}), "Tam")
        self.assertEqual(get_short_lang({"tags": {"language": "hindi"}}), "Hin")
        self.assertEqual(get_short_lang({"tags": {"language": "eng"}}), "Eng")
        self.assertEqual(get_short_lang({"tags": {"language": "kannada"}}), "Kan")

    def test_format_tm_ui_single(self):
        session = {
            "mid": 12345,
            "is_multi": False,
            "view_mode": "audio",
            "page": 1,
            "current_file_idx": 0,
            "files": [
                {
                    "path": "/tmp/test.mkv",
                    "name": "test.mkv",
                    "audio_tracks": [
                        {"index": 1, "short_lang": "Eng"},
                        {"index": 2, "short_lang": "Hin"},
                    ],
                    "sub_tracks": [
                        {"index": 3, "short_lang": "Eng"},
                    ],
                    "audio_order": [0, 1],
                    "sub_order": [0],
                    "selected_audio": {0, 1},
                    "selected_sub": {0},
                }
            ],
        }
        caption, markup = format_tm_ui(session)
        self.assertIn("Audio Track Selection", caption)
        self.assertIn("test.mkv", caption)
        self.assertIn("Eng", caption)
        self.assertIn("Hin", caption)

    def test_format_tm_ui_multi(self):
        session = {
            "mid": 12345,
            "is_multi": True,
            "view_mode": "list",
            "page": 1,
            "page_size": 2,
            "current_file_idx": 0,
            "files": [
                {
                    "path": "/tmp/v1.mkv",
                    "name": "v1.mkv",
                    "audio_tracks": [{"index": 1, "short_lang": "Eng"}],
                    "sub_tracks": [],
                    "audio_order": [0],
                    "sub_order": [],
                    "selected_audio": {0},
                    "selected_sub": set(),
                },
                {
                    "path": "/tmp/v2.mkv",
                    "name": "v2.mkv",
                    "audio_tracks": [{"index": 1, "short_lang": "Tam"}],
                    "sub_tracks": [],
                    "audio_order": [0],
                    "sub_order": [],
                    "selected_audio": {0},
                    "selected_sub": set(),
                },
            ],
        }
        caption, markup = format_tm_ui(session)
        self.assertIn("Track Manager - Files List", caption)
        self.assertIn("v1.mkv", caption)
        self.assertIn("v2.mkv", caption)

    def test_format_tm_ui_select_file(self):
        session = {
            "mid": 12345,
            "is_multi": True,
            "view_mode": "select_file",
            "page": 1,
            "page_size": 2,
            "current_file_idx": 0,
            "files": [
                {
                    "path": "/tmp/v1.mkv",
                    "name": "v1.mkv",
                    "audio_tracks": [{"index": 1, "short_lang": "Eng"}],
                    "sub_tracks": [],
                    "audio_order": [0],
                    "sub_order": [],
                    "selected_audio": {0},
                    "selected_sub": set(),
                },
            ],
        }
        caption, markup = format_tm_ui(session)
        self.assertIn("Select a File to Edit Tracks", caption)


if __name__ == "__main__":
    unittest.main()

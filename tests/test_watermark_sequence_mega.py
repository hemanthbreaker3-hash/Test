import unittest
from PIL import Image
import os
import tempfile
import asyncio

from bot.helper.ext_utils.media_utils import _calc_wm_position, apply_thumbnail_watermark
from bot.helper.listeners.mega_listener import _mega_error_format


class TestWatermarkSequenceMega(unittest.IsolatedAsyncioTestCase):

    def test_watermark_positions(self):
        bg_w, bg_h = 1000, 1000
        wm_w, wm_h = 100, 100
        margin = 15

        # 1. Top-Left
        self.assertEqual(_calc_wm_position("Top-Left", bg_w, bg_h, wm_w, wm_h, margin), (15, 15))
        # 2. Top-Center
        self.assertEqual(_calc_wm_position("Top-Center", bg_w, bg_h, wm_w, wm_h, margin), (450, 15))
        # 3. Top-Right
        self.assertEqual(_calc_wm_position("Top-Right", bg_w, bg_h, wm_w, wm_h, margin), (885, 15))
        # 4. Center-Left
        self.assertEqual(_calc_wm_position("Center-Left", bg_w, bg_h, wm_w, wm_h, margin), (15, 450))
        # 5. Center
        self.assertEqual(_calc_wm_position("Center", bg_w, bg_h, wm_w, wm_h, margin), (450, 450))
        # 6. Center-Right
        self.assertEqual(_calc_wm_position("Center-Right", bg_w, bg_h, wm_w, wm_h, margin), (885, 450))
        # 7. Bottom-Left
        self.assertEqual(_calc_wm_position("Bottom-Left", bg_w, bg_h, wm_w, wm_h, margin), (15, 885))
        # 8. Bottom-Center
        self.assertEqual(_calc_wm_position("Bottom-Center", bg_w, bg_h, wm_w, wm_h, margin), (450, 885))
        # 9. Bottom-Right
        self.assertEqual(_calc_wm_position("Bottom-Right", bg_w, bg_h, wm_w, wm_h, margin), (885, 885))

    async def test_apply_thumbnail_watermark(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = os.path.join(tmpdir, "test_thumb.jpg")
            img = Image.new("RGB", (500, 500), color="blue")
            img.save(img_path)

            user_dict = {
                "THUMB_WM_TEXT": "HTR Watermark",
                "THUMB_WM_TEXT_POSITION": "Bottom-Right",
                "THUMB_WM_COLOR": "cyan",
                "THUMB_WM_SIZE": "24",
            }

            wm_path = await apply_thumbnail_watermark(img_path, user_dict)
            self.assertTrue(os.path.exists(wm_path))
            self.assertTrue(wm_path.endswith("_wm.jpg"))

            # Test duplicate call returns same path without double watermarking
            dup_path = await apply_thumbnail_watermark(wm_path, user_dict)
            self.assertEqual(dup_path, wm_path)

    async def test_apply_thumbnail_image_watermark(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = os.path.join(tmpdir, "base_thumb.jpg")
            wm_img_path = os.path.join(tmpdir, "wm_logo.png")

            Image.new("RGB", (500, 500), color="green").save(base_path)
            Image.new("RGBA", (100, 100), color="red").save(wm_img_path)

            user_dict = {
                "THUMB_WM_IMAGE": wm_img_path,
                "THUMB_WM_IMAGE_POSITION": "Top-Right",
                "THUMB_WM_SIZE": "20",
            }

            res_path = await apply_thumbnail_watermark(base_path, user_dict)
            self.assertTrue(os.path.exists(res_path))
            self.assertTrue(res_path.endswith("_wm.jpg"))

    def test_sequence_upload_target_lock_keys(self):
        class DummyTaskListener:
            def __init__(self, user_id, up_dest, thread_id=None):
                self.user_id = user_id
                self.up_dest = up_dest
                self.chat_thread_id = thread_id

            def get_target_key(self):
                return (
                    self.user_id,
                    self.up_dest or self.user_id,
                    getattr(self, "chat_thread_id", None),
                )

        t1 = DummyTaskListener(12345, -100111)
        t2 = DummyTaskListener(12345, -100111)
        t3 = DummyTaskListener(12345, -100222)

        # Same user, same destination -> same target key
        self.assertEqual(t1.get_target_key(), t2.get_target_key())
        # Same user, different destination -> different target key
        self.assertNotEqual(t1.get_target_key(), t3.get_target_key())

    def test_mega_error_format(self):
        self.assertEqual(_mega_error_format("-9"), "File(s) not found or deleted")
        self.assertEqual(_mega_error_format("-16"), "Account or file(s) blocked/banned")
        self.assertEqual(_mega_error_format("-17"), "Storage quota exceeded")

    def test_async_mega_request_matching(self):
        from bot.helper.listeners.mega_listener import AsyncMega, MegaAppListener
        async_mega = AsyncMega()
        listener = MegaAppListener(async_mega, None)

        async_mega._expected_request_type = (1, 2, 3)
        self.assertTrue(listener._is_expected_request(1))
        self.assertFalse(listener._is_expected_request(99))

    def test_mega_utils_no_credentials(self):
        from bot.helper.ext_utils.mega_utils import _get_mega_account_info_sync
        res = _get_mega_account_info_sync("", "")
        self.assertIn("No credentials configured", res)


if __name__ == "__main__":
    unittest.main()

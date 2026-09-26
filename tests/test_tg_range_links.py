import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.helper.ext_utils.links_utils import is_telegram_link
from bot.helper.telegram_helper.message_utils import parse_tg_link, get_tg_link_message
from bot.helper.mirror_leech_utils.download_utils.telegram_download import TelegramDownloadHelper
from bot.helper.ext_utils.exceptions import TgLinkException


class TestTelegramRangeLinks(unittest.TestCase):
    def test_is_telegram_link(self):
        self.assertTrue(is_telegram_link("https://t.me/c/4297727512/18"))
        self.assertTrue(is_telegram_link("https://telegram.me/c/4297727512/18"))
        self.assertTrue(is_telegram_link("https://telegram.dog/channel/18"))
        self.assertTrue(is_telegram_link("https://telegram.space/c/4297727512/18"))
        self.assertTrue(is_telegram_link("tg://openmessage?user_id=123&message_id=18"))
        self.assertFalse(is_telegram_link("https://google.com"))

    def test_parse_single_tg_link(self):
        chat, msg_ids, private = parse_tg_link("https://t.me/c/4297727512/18")
        self.assertEqual(chat, -1004297727512)
        self.assertEqual(msg_ids, 18)
        self.assertFalse(private)

    def test_parse_range_format_a(self):
        chat, msg_ids, private = parse_tg_link("https://t.me/c/4297727512/18-20")
        self.assertEqual(chat, -1004297727512)
        self.assertEqual(msg_ids, [18, 19, 20])
        self.assertFalse(private)

    def test_parse_range_format_b(self):
        chat, msg_ids, private = parse_tg_link(
            "https://t.me/c/4297727512/18-https://t.me/c/4297727512/20"
        )
        self.assertEqual(chat, -1004297727512)
        self.assertEqual(msg_ids, [18, 19, 20])
        self.assertFalse(private)

    def test_parse_range_format_b_with_spaces(self):
        chat, msg_ids, private = parse_tg_link(
            "https://t.me/c/4297727512/18 - https://t.me/c/4297727512/20"
        )
        self.assertEqual(chat, -1004297727512)
        self.assertEqual(msg_ids, [18, 19, 20])
        self.assertFalse(private)

    def test_parse_range_reverse(self):
        chat, msg_ids, private = parse_tg_link("https://t.me/c/4297727512/20-18")
        self.assertEqual(chat, -1004297727512)
        self.assertEqual(msg_ids, [20, 19, 18])

    def test_parse_range_chat_mismatch(self):
        with self.assertRaises(TgLinkException):
            parse_tg_link(
                "https://t.me/c/4297727512/18-https://t.me/c/1111111111/20"
            )


class TestAsyncTelegramRangeDownload(unittest.IsolatedAsyncioTestCase):
    @patch("bot.core.tg_client.TgClient.bot")
    async def test_get_tg_link_message_range(self, mock_bot):
        m1 = MagicMock(empty=False, id=18)
        m2 = MagicMock(empty=False, id=19)
        m3 = MagicMock(empty=False, id=20)
        mock_bot.get_messages = AsyncMock(return_value=[m1, m2, m3])

        msgs, sess = await get_tg_link_message("https://t.me/c/4297727512/18-20")
        self.assertEqual(sess, "bot")
        self.assertEqual(len(msgs), 3)
        self.assertEqual([m.id for m in msgs], [18, 19, 20])

    @patch("bot.helper.mirror_leech_utils.download_utils.telegram_download.check_running_tasks", new_callable=AsyncMock)
    async def test_add_range_download_sequential(self, mock_check_tasks):
        mock_check_tasks.return_value = (False, None)

        listener = MagicMock()
        listener.mid = 1001
        listener.transmission_mode = "bot"
        listener.up_dest = None
        listener.is_leech = False
        listener.name = "Test_Range"
        listener.user_dict = {}
        listener.is_cancelled = False
        listener.multi = 1
        listener.on_download_start = AsyncMock()
        listener.on_download_complete = AsyncMock()

        helper = TelegramDownloadHelper(listener)
        helper._on_download_start = AsyncMock()
        helper._on_download_complete = AsyncMock()
        helper._download_file = AsyncMock(return_value=True)

        m1 = MagicMock(media=MagicMock(value="document"), document=MagicMock(file_name="file1.mp4", file_size=1000), text=None, caption=None, id=18)
        m2 = MagicMock(media=MagicMock(value="video"), video=MagicMock(file_name="file2.mkv", file_size=2000), text=None, caption=None, id=19)

        await helper.add_range_download([m1, m2], "/tmp/downloads/", "bot")

        self.assertEqual(helper._download_file.call_count, 2)
        helper._on_download_complete.assert_called_once()


if __name__ == "__main__":
    unittest.main()

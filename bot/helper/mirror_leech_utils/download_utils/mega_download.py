import os
from asyncio import Lock as AsyncLock, sleep as asleep
from contextlib import suppress
from secrets import token_hex

from aiofiles.os import makedirs
try:
    from mega import MegaApi, MegaCancelToken
except (ImportError, SyntaxError, Exception):
    try:
        from megasdk import MegaApi, MegaCancelToken
    except (ImportError, SyntaxError, Exception):
        MegaApi = MegaCancelToken = None

from .... import LOGGER, task_dict, task_dict_lock, user_data
from ....core.config_manager import Config
from ...telegram_helper.message_utils import send_status_message
from ...ext_utils.task_manager import (
    check_running_tasks,
    limit_checker,
    stop_duplicate_check,
)
from ...ext_utils.files_utils import clean_download
from ...ext_utils.links_utils import get_mega_subfolder_handle, is_mega_folder_link
from ...listeners.mega_listener import (
    AsyncMega,
    MegaAppListener,
    MegaFolderListener,
    _mega_error_format,
    _MEGA_SDK_LOCK,
)
from ...mirror_leech_utils.status_utils.mega_status import MegaDownloadStatus
from ...mirror_leech_utils.status_utils.queue_status import QueueStatus


_ACTIVE_MEGA_LINKS = set()
_ACTIVE_MEGA_LINKS_LOCK = AsyncLock()

_MEGA_BASE64_ALPHABET = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
)


def _mega_base64_to_int(handle_str: str) -> int | None:
    if not handle_str:
        return None
    try:
        val = 0
        for c in handle_str:
            idx = _MEGA_BASE64_ALPHABET.find(c)
            if idx < 0:
                return None
            val = (val << 6) | idx
        return val & ((1 << 64) - 1)
    except Exception:
        return None


def _find_child_by_handle(api, parent_node, target_handle):
    if not parent_node or not target_handle:
        return None
    try:
        children = api.getChildren(parent_node)
        return _find_child_in_list(children, target_handle)
    except Exception as e:
        LOGGER.warning(f"_find_child_by_handle error: {e}")
    return None


def _find_child_in_list(children, target_handle):
    if not children:
        return None
    target_int = _mega_base64_to_int(target_handle)
    try:
        _to_handle = getattr(MegaApi, "base64ToHandle", None)
        if callable(_to_handle) and target_int is None:
            target_int = _to_handle(target_handle)
    except Exception:
        pass
    for i in range(children.size()):
        child = children.get(i)
        try:
            ch = child.getHandle()
            if (
                ch == target_handle
                or (target_int is not None and ch == target_int)
                or (hasattr(child, "getName") and child.getName() == target_handle)
            ):
                return child
        except Exception:
            pass
    return None


def _make_cancel_token():
    if MegaCancelToken is None:
        return None
    try:
        return MegaCancelToken.createInstance()
    except Exception as e:
        LOGGER.error(f"Mega: failed to create cancel token: {e}")
        return None


async def _reserve_link(link: str):
    async with _ACTIVE_MEGA_LINKS_LOCK:
        if link in _ACTIVE_MEGA_LINKS:
            return False
        _ACTIVE_MEGA_LINKS.add(link)
        return True


async def _release_link(link: str):
    async with _ACTIVE_MEGA_LINKS_LOCK:
        _ACTIVE_MEGA_LINKS.discard(link)


def _mega_py_download_sync(listener, path, email, password, status_helper=None):
    import re
    from time import time
    start_time = time()
    try:
        from mega import Mega
        from mega.errors import RequestError
        mega = Mega()
    except Exception as e:
        raise ImportError(f"Mega module import failed: {e}")

    if not hasattr(RequestError, "_patched_for_str"):
        _orig_req_init = RequestError.__init__
        def _safe_req_init(self, message, code=None):
            if isinstance(message, int):
                _orig_req_init(self, message)
            else:
                self.message = str(message)
                self.code = code
        RequestError.__init__ = _safe_req_init
        RequestError._patched_for_str = True

    def _patched_parse_url(self, url):
        url = url.strip().replace(" ", "")
        if "/file/" in url:
            m = re.search(r"/file/([^#?]+)#([^?]+)", url)
            if m:
                return f"{m.group(1)}!{m.group(2)}"
        if "/folder/" in url:
            m = re.search(r"/folder/([^#?]+)#([^?]+)", url)
            if m:
                return f"{m.group(1)}!{m.group(2)}"
        if "/#F!" in url:
            m = re.search(r"/#F!([^?]+)", url)
            if m:
                return m.group(1)
        if "/#!" in url:
            m = re.search(r"/#!([^?]+)", url)
            if m:
                return m.group(1)
        if "/embed/" in url:
            m = re.search(r"/embed/([^#?]+)#([^?]+)", url)
            if m:
                return f"{m.group(1)}!{m.group(2)}"
        if "!" in url:
            m = re.search(r"!?([a-zA-Z0-9_-]+![a-zA-Z0-9_-]+)", url)
            if m:
                return m.group(1)
        raise ValueError(f"Invalid Mega URL format: {url}")

    Mega._parse_url = _patched_parse_url

    if not hasattr(Mega, "_orig_download_file"):
        from mega.crypto import (
            base64_to_a32,
            decrypt_attr,
            base64_url_decode,
            a32_to_str,
            get_chunks,
            str_to_a32,
        )
        from Crypto.Cipher import AES
        from Crypto.Util import Counter
        import requests
        import tempfile
        import shutil
        from pathlib import Path
        import os

        _orig_download_file = Mega._download_file

        def _fixed_download_file(self, file_handle, file_key, dest_path=None, dest_filename=None, is_public=False, file=None):
            if file is None:
                if isinstance(file_key, str):
                    file_key = base64_to_a32(file_key)
                if is_public:
                    file_data = self._api_request({'a': 'g', 'g': 1, 'p': file_handle})
                else:
                    file_data = self._api_request({'a': 'g', 'g': 1, 'n': file_handle})

                if len(file_key) < 8:
                    file_key = tuple(file_key) + (0,) * (8 - len(file_key))

                k = (file_key[0] ^ file_key[4], file_key[1] ^ file_key[5],
                     file_key[2] ^ file_key[6], file_key[3] ^ file_key[7])
                iv = file_key[4:6] + (0, 0)
                meta_mac = file_key[6:8]
            else:
                file_data = self._api_request({'a': 'g', 'g': 1, 'n': file['h']})
                k = file['k']
                iv = file['iv']
                meta_mac = file['meta_mac']

            if len(k) < 8:
                k = tuple(k) + (0,) * (8 - len(k))
            if len(iv) < 4:
                iv = tuple(iv) + (0,) * (4 - len(iv))
            if len(meta_mac) < 2:
                meta_mac = tuple(meta_mac) + (0,) * (2 - len(meta_mac))

            if 'g' not in file_data:
                from mega.errors import RequestError
                raise RequestError('File not accessible anymore')
            file_url = file_data['g']
            file_size = file_data['s']
            attribs = base64_url_decode(file_data['at'])
            attribs = decrypt_attr(attribs, k)

            if dest_filename is not None:
                file_name = dest_filename
            elif isinstance(attribs, dict) and 'n' in attribs:
                file_name = attribs['n']
            else:
                file_name = f"mega_file_{file_handle or 'dl'}"

            input_file = requests.get(file_url, stream=True).raw

            if dest_path is None:
                dest_path = ''
            else:
                dest_path += '/'

            with tempfile.NamedTemporaryFile(mode='w+b', prefix='megapy_', delete=False) as temp_output_file:
                k_str = a32_to_str(k)
                counter = Counter.new(128, initial_value=((iv[0] << 32) + iv[1]) << 64)
                aes = AES.new(k_str, AES.MODE_CTR, counter=counter)

                mac_str = '\0' * 16
                mac_encryptor = AES.new(k_str, AES.MODE_CBC, mac_str.encode("utf8"))
                iv_str = a32_to_str([iv[0], iv[1], iv[0], iv[1]])

                for chunk_start, chunk_size in get_chunks(file_size):
                    chunk = input_file.read(chunk_size)
                    chunk = aes.decrypt(chunk)
                    temp_output_file.write(chunk)

                    encryptor = AES.new(k_str, AES.MODE_CBC, iv_str)
                    i = 0
                    for i in range(0, len(chunk) - 16, 16):
                        block = chunk[i:i + 16]
                        encryptor.encrypt(block)

                    if file_size > 16:
                        if len(chunk) > 16:
                            i += 16
                        else:
                            i = 0
                    else:
                        i = 0

                    block = chunk[i:i + 16]
                    if len(block) % 16:
                        block += b'\0' * (16 - (len(block) % 16))
                    mac_str = mac_encryptor.encrypt(encryptor.encrypt(block))

                    file_info = os.stat(temp_output_file.name)
                    LOGGER.info('%s of %s downloaded', file_info.st_size, file_size)
                    if status_helper is not None:
                        status_helper.downloaded_bytes = file_info.st_size
                        elapsed = time() - start_time
                        if elapsed > 0:
                            status_helper.speed = int(file_info.st_size / elapsed)
                        if listener.size <= 0 and file_size > 0:
                            listener.size = file_size
                file_mac = str_to_a32(mac_str)
                if len(file_mac) < 4:
                    file_mac = tuple(file_mac) + (0,) * (4 - len(file_mac))
                if (file_mac[0] ^ file_mac[1], file_mac[2] ^ file_mac[3]) != meta_mac:
                    LOGGER.debug("Mega MAC integrity check mismatch, proceeding with download.")
                output_path = Path(dest_path + file_name)
                shutil.move(temp_output_file.name, output_path)
                return output_path

        Mega._orig_download_file = _orig_download_file
        Mega._download_file = _fixed_download_file

    m = None
    if email and password:
        try:
            m = mega.login(email, password)
        except Exception as e:
            LOGGER.warning(f"Mega user login failed, falling back to anonymous: {e}")
            m = None
    if m is None:
        m = mega.login()

    downloaded_path = m.download_url(listener.link, dest_path=path)
    return downloaded_path


class MegaPyStatusHelper:
    def __init__(self, listener, gid):
        self.listener = listener
        self._gid = gid
        self.downloaded_bytes = 0
        self.speed = 0
        self._start_time = 0
        self.engine = EngineStatus().STATUS_MEGA

    def name(self):
        return self.listener.name

    def progress_raw(self):
        if self.listener.size > 0:
            return round((self.downloaded_bytes / self.listener.size) * 100, 2)
        return 0.0

    def progress(self):
        return f"{self.progress_raw()}%"

    def status(self):
        return MirrorStatus.STATUS_DOWNLOAD

    def processed_bytes(self):
        return get_readable_file_size(self.downloaded_bytes)

    def eta(self):
        if not self.speed:
            return "-"
        try:
            seconds = (self.listener.size - self.downloaded_bytes) / self.speed
            return get_readable_time(seconds)
        except Exception:
            return "-"

    def size(self):
        return get_readable_file_size(self.listener.size) if self.listener.size > 0 else "Unknown"

    def speed_str(self):
        return f"{get_readable_file_size(self.speed)}/s"

    def gid(self):
        return self._gid

    def task(self):
        return self

    async def cancel_task(self):
        self.listener.is_cancelled = True
        await self.listener.on_download_error("download stopped by user!")


async def _download_mega_py(listener, path, email, password):
    from ...ext_utils.bot_utils import sync_to_async
    await makedirs(path, exist_ok=True)
    gid = token_hex(5)

    msg, button = await stop_duplicate_check(listener)
    if msg:
        await listener.on_download_error(msg, button)
        return

    if limit_exceeded := await limit_checker(listener):
        await listener.on_download_error(limit_exceeded, is_limit=True)
        return

    added_to_queue, event = await check_running_tasks(listener)
    if added_to_queue:
        async with task_dict_lock:
            task_dict[listener.mid] = QueueStatus(listener, gid, "dl")
        await listener.on_download_start()
        if listener.multi <= 1:
            await send_status_message(listener.message)
        await event.wait()
        if listener.is_cancelled:
            return

    status_helper = MegaPyStatusHelper(listener, gid)
    async with task_dict_lock:
        task_dict[listener.mid] = status_helper

    if added_to_queue:
        await listener.on_download_start()
    else:
        await listener.on_download_start()
        if listener.multi <= 1:
            await send_status_message(listener.message)

    if listener.is_cancelled:
        return

    try:
        res = await sync_to_async(_mega_py_download_sync, listener, path, email, password, status_helper)
        if not res or listener.is_cancelled:
            return
        await listener.on_download_complete()
    except Exception as e:
        LOGGER.error(f"Mega.py download failed for link {listener.link}: {e}", exc_info=True)
        await listener.on_download_error(f"Mega download failed: {e}")


async def add_mega_download(listener, path):
    if Config.DISABLE_MEGA:
        await listener.on_download_error(
            "Mega Link downloads are currently disabled by the Bot Owner."
        )
        return

    user_dict = user_data.get(listener.user_id, {})
    mega_email = user_dict.get("MEGA_EMAIL") or Config.MEGA_EMAIL
    mega_password = user_dict.get("MEGA_PASSWORD") or Config.MEGA_PASSWORD

    if not await _reserve_link(listener.link):
        await listener.on_download_error(
            "This Mega link is already being downloaded! Wait for it to finish."
        )
        return

    if MegaApi is None:
        try:
            try:
                from mega import Mega
            except (ImportError, SyntaxError, Exception):
                Mega = None
            if Mega is None:
                raise ImportError("MEGA SDK / mega module is not available on this system.")
            await _download_mega_py(listener, path, mega_email, mega_password)
        except Exception as e:
            await listener.on_download_error(f"Mega download failed: {e}")
        finally:
            await _release_link(listener.link)
        return

    async_api = None
    mega_base = ""
    is_folder = False
    try:
        sdk_gid = token_hex(5)
        await makedirs(path, exist_ok=True)
        mega_base = os.path.join(
            os.path.dirname(path.rstrip("/")), ".mega_sdk", sdk_gid
        )
        mega_dir = os.path.join(mega_base, "main")
        await makedirs(mega_dir, exist_ok=True)

        async_api = AsyncMega()
        async_api.api = api = MegaApi("", mega_dir, "HTR-X", 4)
        mega_listener = MegaAppListener(async_api, listener)
        async_api._mega_listener = mega_listener
        api.addListener(mega_listener)
        api._listener_ref = mega_listener

        is_folder = is_mega_folder_link(listener.link)
        subfolder_handle = get_mega_subfolder_handle(listener.link)

        if is_folder:
            async_api.folder_api = folder_api = MegaApi("", mega_dir, "HTR-X", 4)

            # Authenticate folder API with the configured premium MEGA account.
            if mega_email and mega_password:
                LOGGER.info("Mega: authenticating premium account for folder download")
                await async_api.login(mega_email, mega_password)
                if listener.is_cancelled or async_api._mega_listener.is_cancelled:
                    return
                if async_api._mega_listener.error:
                    await listener.on_download_error(
                        _mega_error_format(async_api._mega_listener.error)
                    )
                    return

                account_auth = api.getAccountAuth()
                if not account_auth:
                    await listener.on_download_error(
                        "Failed to obtain MEGA account authentication."
                    )
                    return

                folder_api.setAccountAuth(account_auth)
                LOGGER.info("Mega: premium account auth applied to folder API")
                del account_auth

            folder_listener = MegaFolderListener(async_api, listener)
            async_api._folder_listener = folder_listener
            folder_api.addListener(folder_listener)
            folder_api._listener_ref = folder_listener
            dl_listener = folder_listener

            await async_api.loginToFolder(listener.link)
            if listener.is_cancelled or dl_listener.is_cancelled:
                return
            if dl_listener.error:
                await listener.on_download_error(_mega_error_format(dl_listener.error))
                return
            await async_api.fetchNodes(api=folder_api)
            await asleep(0)
            if listener.is_cancelled or dl_listener.is_cancelled:
                LOGGER.info("Mega: cancelled after fetchNodes")
                return
            if dl_listener.error:
                LOGGER.info("Mega: error after fetchNodes: %s", dl_listener.error)
                await listener.on_download_error(_mega_error_format(dl_listener.error))
                return
            if not dl_listener.node:
                LOGGER.info("Mega: no root node after fetchNodes")
                await listener.on_download_error(
                    "Failed to get root node for MEGA folder"
                )
                return
            if subfolder_handle:
                LOGGER.info("Mega: looking up subfolder handle=%s", subfolder_handle)
                target_int = _mega_base64_to_int(subfolder_handle)
                node = _find_child_in_list(dl_listener._children, subfolder_handle)
                if not node and target_int is not None:
                    try:
                        node = folder_api.getNodeByHandle(target_int)
                    except Exception as e:
                        LOGGER.error("Mega: getNodeByHandle failed: %s", e)
                if not node:
                    await listener.on_download_error(
                        "Subfolder not found in the MEGA link"
                    )
                    return
                dl_listener.node = node
                dl_listener._cache_node_data(node)
                LOGGER.info("Mega: subfolder name=%s", dl_listener._name)

                dl_listener._size = listener.size
                if not dl_listener._size:
                    try:
                        s = node.getSize()
                        dl_listener._size = s if s < (1 << 62) else -1
                    except Exception:
                        pass
                LOGGER.info("Mega: subfolder size=%s", dl_listener._size)
            else:
                node = dl_listener.node
        else:
            dl_listener = mega_listener
            if mega_email and mega_password:
                await async_api.login(mega_email, mega_password)
                if listener.is_cancelled or mega_listener.is_cancelled:
                    return
                if mega_listener.error:
                    LOGGER.error("Mega login error: %s", mega_listener.error)
                    await listener.on_download_error(
                        _mega_error_format(mega_listener.error)
                    )
                    return
                await async_api.fetchNodes()
                if listener.is_cancelled or mega_listener.is_cancelled:
                    return
                if mega_listener.error:
                    LOGGER.error("Mega fetchNodes error: %s", mega_listener.error)
                    await listener.on_download_error(
                        _mega_error_format(mega_listener.error)
                    )
                    return
            await async_api.getPublicNode(listener.link)
            if listener.is_cancelled or mega_listener.is_cancelled:
                return
            if mega_listener.error:
                LOGGER.error("Mega getPublicNode error for link %s: %s", listener.link, mega_listener.error)
                await listener.on_download_error(_mega_error_format(mega_listener.error))
                return
            node = mega_listener.public_node
            if not node:
                LOGGER.error("Mega: Failed to resolve public node for link: %s", listener.link)
                await listener.on_download_error("Failed to resolve MEGA link")
                return

        listener.name = (
            listener.name or dl_listener._name or f"MEGA_Download_{token_hex(5)}"
        )
        listener.size = dl_listener._size if dl_listener._size < (1 << 62) else -1
        if listener.size <= 0 and node:
            try:
                s = node.getSize()
                listener.size = s if s < (1 << 62) else -1
            except Exception:
                pass
        gid = token_hex(5)
        msg, button = await stop_duplicate_check(listener)
        if msg:
            await listener.on_download_error(msg, button)
            return

        if limit_exceeded := await limit_checker(listener):
            await listener.on_download_error(limit_exceeded, is_limit=True)
            return

        added_to_queue, event = await check_running_tasks(listener)
        if added_to_queue:
            async with task_dict_lock:
                task_dict[listener.mid] = QueueStatus(listener, gid, "dl")
            await listener.on_download_start()
            if listener.multi <= 1:
                await send_status_message(listener.message)
            await event.wait()
            if listener.is_cancelled:
                return

        async with task_dict_lock:
            task_dict[listener.mid] = MegaDownloadStatus(
                listener, dl_listener, gid, "dl"
            )

        if added_to_queue:
            await listener.on_download_start()
        else:
            await listener.on_download_start()
            if listener.multi <= 1:
                await send_status_message(listener.message)

        if listener.is_cancelled or dl_listener.is_cancelled:
            return
        download_path = path
        if is_mega_folder_link(listener.link):
            download_path = os.path.join(path, listener.name)
            await makedirs(download_path, exist_ok=True)

        for attempt in range(5):
            cancel_token = _make_cancel_token()
            dl_listener._cancel_token = cancel_token
            dl_listener.error = None
            dl_listener.retryable_error = None
            dl_listener._bytes_transferred = 0
            dl_listener._total_downloaded_bytes = 0
            dl_listener._caller_manages_completion = False

            await async_api.startDownload(
                node,
                download_path,
                listener.name,
                None,
                False,
                cancel_token,
                3,
                2,
                False,
            )
            await async_api.wait_for_transfer()

            if listener.is_cancelled or dl_listener.is_cancelled:
                LOGGER.info("MegaDownload: transfer cancelled during attempt %s", attempt + 1)
                return

            if dl_listener.error and not dl_listener.retryable_error:
                LOGGER.error(
                    "MegaDownload: fatal error during download: %s",
                    dl_listener.error,
                )
                await listener.on_download_error(
                    _mega_error_format(dl_listener.error)
                )
                return

            if not dl_listener.retryable_error:
                LOGGER.info(
                    "MegaDownload: completed transfer successfully for %s",
                    listener.name,
                )
                return

            if dl_listener.retryable_error.startswith("-13"):
                local_size = 0
                if os.path.isdir(download_path):
                    for root, dirs, files in os.walk(download_path):
                        for filename in files:
                            try:
                                local_size += os.path.getsize(os.path.join(root, filename))
                            except OSError:
                                pass
                elif os.path.isfile(download_path):
                    try:
                        local_size = os.path.getsize(download_path)
                    except OSError:
                        pass

                expected_size = dl_listener._total_folder_size or dl_listener._size

                LOGGER.warning(
                    "MegaDownload: API_EINCOMPLETE local_size=%s expected_size=%s transferred=%s",
                    local_size,
                    expected_size,
                    dl_listener.downloaded_bytes,
                )

                if expected_size > 0:
                    missing = expected_size - local_size
                    tolerance = max(2 * 1024 * 1024, int(expected_size * 0.001))
                    LOGGER.warning(
                        "MegaDownload: API_EINCOMPLETE missing=%s tolerance=%s",
                        missing,
                        tolerance,
                    )
                    if missing <= tolerance:
                        LOGGER.warning(
                            "MegaDownload: treating API_EINCOMPLETE as complete; local data is within tolerance"
                        )
                        dl_listener.retryable_error = None
                        await listener.on_download_complete()
                        return

            if attempt >= 4:
                LOGGER.error(
                    "MegaDownload: transfer incomplete after 5 attempts: %s",
                    dl_listener.retryable_error,
                )
                await listener.on_download_error(
                    _mega_error_format(dl_listener.retryable_error)
                )
                return

            LOGGER.warning(
                "MegaDownload: transfer incomplete, retrying attempt %s/5: %s",
                attempt + 2,
                dl_listener.retryable_error,
            )
            await clean_download(download_path)
            await asleep(2**attempt)

    except Exception as e:
        LOGGER.error(f"Unexpected error in add_mega_download: {e}", exc_info=True)
        if not listener.is_cancelled:
            await listener.on_download_error(f"Internal error: {e}")
    finally:
        if async_api is not None:
            if not is_folder:
                async with _MEGA_SDK_LOCK:
                    with suppress(Exception):
                        await async_api.logout()
                    if (
                        async_api.api is not None
                        and async_api._mega_listener is not None
                    ):
                        with suppress(Exception):
                            async_api.api.removeListener(async_api._mega_listener)
                    if (
                        async_api.folder_api is not None
                        and async_api._folder_listener is not None
                    ):
                        with suppress(Exception):
                            async_api.folder_api.removeListener(
                                async_api._folder_listener
                            )
        await _release_link(listener.link)
        await clean_download(mega_base)

import asyncio
import pytest
from aiofiles.os import remove, path as aiopath
from bot import active_range_tasks, task_dict, task_dict_lock
from bot.helper.ext_utils.range_utils import (
    save_range_tasks_to_file,
    load_range_tasks_from_file,
    RANGE_STORE_FILE,
)
from bot.modules.cancel_task import _cancel_single_range_task


@pytest.mark.asyncio
async def test_range_task_persistence_and_cancel():
    if await aiopath.exists(RANGE_STORE_FILE):
        await remove(RANGE_STORE_FILE)

    range_id = "rl_test_123"
    rt_data = {
        "range_id": range_id,
        "mid": 999111,
        "user_id": 12345,
        "tag": "test",
        "total_links": 5,
        "current_idx": 2,
        "current_sub_task": None,
        "is_cancelled": False,
        "links": ["http://link1", "http://link2", "http://link3"],
        "listener_dict": {
            "mid": 999111,
            "user_id": 12345,
            "is_leech": True,
            "chat_id": -100123,
            "message_id": 456,
        },
    }

    active_range_tasks[range_id] = rt_data
    await save_range_tasks_to_file()

    loaded = await load_range_tasks_from_file()
    assert len(loaded) == 1
    assert loaded[0]["range_id"] == range_id
    assert loaded[0]["current_idx"] == 2

    class DummyTaskStatus:
        def __init__(self):
            self.cancelled = False

        async def cancel_task(self):
            self.cancelled = True
            async with task_dict_lock:
                task_dict.pop(999222, None)

    class DummySubTask:
        def __init__(self):
            self.mid = 999222
            self.is_cancelled = False

    dummy_sub = DummySubTask()
    dummy_status = DummyTaskStatus()
    rt_data["current_sub_task"] = dummy_sub

    async with task_dict_lock:
        task_dict[999222] = dummy_status

    await _cancel_single_range_task(rt_data)

    assert range_id not in active_range_tasks
    assert dummy_sub.is_cancelled is True
    assert dummy_status.cancelled is True
    async with task_dict_lock:
        assert 999222 not in task_dict

    loaded_after = await load_range_tasks_from_file()
    assert len(loaded_after) == 0

    if await aiopath.exists(RANGE_STORE_FILE):
        await remove(RANGE_STORE_FILE)

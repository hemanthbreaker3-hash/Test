import asyncio
import pytest
from bot.helper.ext_utils.bot_lock import SmartLock, ff_lock


@pytest.mark.asyncio
async def test_smart_lock_concurrency():
    lock = SmartLock(max_slots=3)
    assert lock.max_slots == 3

    acquired_count = 0
    acquired_event = asyncio.Event()

    async def worker():
        nonlocal acquired_count
        async with lock:
            acquired_count += 1
            if acquired_count == 3:
                acquired_event.set()
            await asyncio.sleep(0.1)

    tasks = [asyncio.create_task(worker()) for _ in range(3)]
    await asyncio.wait_for(acquired_event.wait(), timeout=1.0)
    assert acquired_count == 3
    assert lock.active == 3

    await asyncio.gather(*tasks)
    assert lock.active == 0


@pytest.mark.asyncio
async def test_ff_lock_max_slots():
    assert ff_lock.max_slots == 3

    acquired = []

    async def worker(idx):
        async with ff_lock:
            acquired.append(idx)
            await asyncio.sleep(0.05)

    tasks = [asyncio.create_task(worker(i)) for i in range(4)]
    await asyncio.sleep(0.02)
    assert len(acquired) == 3
    assert ff_lock.active == 3

    await asyncio.gather(*tasks)
    assert len(acquired) == 4
    assert ff_lock.active == 0

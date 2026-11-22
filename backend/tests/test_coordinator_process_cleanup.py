import asyncio

import pytest

from backend.mpc.coordinator import MPCCoordinator
from backend.mpc.exceptions import MPCTimeoutError


@pytest.mark.asyncio
async def test_legacy_runner_timeout_kills_reaps_and_drains_all_processes(monkeypatch):
    processes = []

    class FakeProcess:
        def __init__(self):
            self.returncode = None
            self.killed = asyncio.Event()
            self.communicate_calls = 0

        async def communicate(self, _input=None):
            self.communicate_calls += 1
            await self.killed.wait()
            self.returncode = -9
            return b"", b""

        def kill(self):
            self.killed.set()

        async def wait(self):
            await self.killed.wait()
            return self.returncode

    async def create_process(*_args, **_kwargs):
        process = FakeProcess()
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_process)
    coordinator = MPCCoordinator(timeout=0.01)

    with pytest.raises(MPCTimeoutError):
        await coordinator.execute_protocol([50000, 70000, 60000], custom_base_port=13000)

    assert len(processes) == 3
    assert all(process.returncode == -9 for process in processes)
    assert all(process.communicate_calls == 1 for process in processes)

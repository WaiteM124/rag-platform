from __future__ import annotations

import time

from app.api.stage_timer import StageTimer


def test_stage_timer_records_ms():
    timer = StageTimer()
    with timer.stage("alpha"):
        time.sleep(0.01)
    with timer.stage("beta"):
        time.sleep(0.005)
    stages = timer.as_dict()
    assert stages["alpha"] >= 8.0
    assert stages["beta"] >= 3.0
    assert timer.total_ms() >= stages["alpha"]

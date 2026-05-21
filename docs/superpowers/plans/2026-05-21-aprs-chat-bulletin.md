# APRS Chat Bulletin Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone bulletin script that announces APRS Chat on Google Play and includes short follow-up bulletin lines.

**Architecture:** Add one new shell script in `tools/` that matches the existing bulletin-script pattern already used in this repo, with a minimal `set -e` safety guard so failures are not masked by later `sleep` commands. Protect the behavior with one focused Python regression test that checks the script path, executable bit, and exact bulletin command lines.

**Tech Stack:** Bash, pytest, Python `pathlib`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `tools/bulletin-aprschat.sh` | Create | Standalone APRS Chat Google Play bulletin sender |
| `tests/test_bulletin_scripts.py` | Create | Regression test for bulletin script presence and content |

---

## Chunk 1: APRS Chat Bulletin Script

### Task 1: Add the bulletin script with a focused regression test

**Files:**
- Create: `tests/test_bulletin_scripts.py`
- Create: `tools/bulletin-aprschat.sh`

- [ ] **Step 1: Write the failing test**

Create `tests/test_bulletin_scripts.py` with:

```python
import stat
from pathlib import Path


def test_bulletin_aprschat_script_contents():
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / 'tools' / 'bulletin-aprschat.sh'

    assert script.exists()
    assert script.stat().st_mode & stat.S_IXUSR

    lines = script.read_text().splitlines()
    send_lines = [line for line in lines if line.startswith('aprsd send-message -n')]

    assert send_lines == [
        'aprsd send-message -n BLN0 "APRS Chat now on Google Play Store!"',
        'aprsd send-message -n BLN1 "Install: https://tinyurl.com/APRSChat"',
        'aprsd send-message -n BLN2 "Android app for APRS chat and messaging"',
        'aprsd send-message -n BLN3 "Search Google Play for APRS Chat"',
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bulletin_scripts.py -v`
Expected: FAIL because `tools/bulletin-aprschat.sh` does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Create `tools/bulletin-aprschat.sh` with:

```bash
#!/bin/bash
set -e

# Send APRS bulletins announcing APRS Chat on Google Play

source ~/devel/mine/hamradio/aprsd/.venv/bin/activate

export APRS_LOGIN=WB4BOR
export APRS_PASSWORD=24496

aprsd send-message -n BLN0 "APRS Chat now on Google Play Store!"
sleep 2
aprsd send-message -n BLN1 "Install: https://tinyurl.com/APRSChat"
sleep 2
aprsd send-message -n BLN2 "Android app for APRS chat and messaging"
sleep 2
aprsd send-message -n BLN3 "Search Google Play for APRS Chat"
sleep 2
```

- [ ] **Step 4: Make the script executable**

Run: `chmod +x tools/bulletin-aprschat.sh`

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_bulletin_scripts.py -v`
Expected: PASS

- [ ] **Step 6: Run a second verification pass**

Run: `bash -n tools/bulletin-aprschat.sh && pytest tests/test_bulletin_scripts.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add tests/test_bulletin_scripts.py tools/bulletin-aprschat.sh
git commit -m "Add APRS Chat bulletin script"
```

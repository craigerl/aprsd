# APRS Chat Google Play Bulletin Script

**Date:** 2026-05-21
**Status:** Draft
**Scope:** `tools/` bulletin helper scripts

## Overview

Add a new standalone bulletin script that announces APRS Chat on the Google Play Store and follows with a few short explanatory bulletin lines.

## Goals

1. Add a dedicated script for the APRS Chat Play Store announcement.
2. Match the existing `tools/bulletin-*.sh` style and operational pattern.
3. Keep bulletin text short, direct, and suitable for APRS bulletin usage.

## Current State

- Existing bulletin scripts in `tools/` are small standalone shell wrappers.
- They activate the local virtual environment, export APRS credentials, send a few `BLN` messages, and pause with `sleep 2` between lines.
- There is no dedicated APRS Chat Google Play bulletin script today.

## Design

### Script Shape

Create `tools/bulletin-aprschat.sh` using the same pattern as `tools/bulletin-aprsthursday.sh`, with one small safety improvement so the script exits immediately if activation or any bulletin send fails:

- `#!/bin/bash`
- `set -e`
- brief header comment describing purpose
- `source ~/devel/mine/hamradio/aprsd/.venv/bin/activate`
- export `APRS_LOGIN=WB4BOR` and `APRS_PASSWORD=24496`
- send four numbered bulletin messages with `aprsd send-message -n BLN* ...`
- pause with `sleep 2` between each message

### Bulletin Content

The script will send these lines:

1. `BLN0 APRS Chat now on Google Play Store!`
2. `BLN1 Install: https://tinyurl.com/APRSChat`
3. `BLN2 Android app for APRS chat and messaging`
4. `BLN3 Search Google Play for APRS Chat`

This keeps the first line focused on the announcement, the second on the install URL, and the remaining lines as short follow-up guidance.

## Files to Modify

1. `tools/bulletin-aprschat.sh` - new standalone bulletin script
2. `tests/test_bulletin_scripts.py` - regression test for script content and expected bulletin lines

## Testing Strategy

1. Write a failing test first asserting:
   - the new script exists
   - it is executable
   - it contains the expected ordered `BLN0`-`BLN3` send lines
2. Add the script with the approved content.
3. Re-run the focused test to confirm it passes.

## Non-Goals

- Refactoring existing bulletin scripts into a shared helper
- Folding the APRS Chat announcement into `tools/bulletin.sh`
- Adding scheduling or automation around bulletin execution

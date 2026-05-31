---
status: complete
phase: 03-entity-platforms
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md]
started: 2026-05-31T00:34:56Z
updated: 2026-05-31T00:37:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Test Suite Passes
expected: Running `pytest tests/ -v` from the project root completes with all 48 tests passing and zero failures or errors.
result: pass

### 2. Binary Sensor Appears in HA (Up State)
expected: After loading the Gatus integration in a live HA instance (or via `scp` deploy), a binary sensor entity named after each Gatus endpoint appears under Settings → Devices & Services → Gatus. For an endpoint that is currently healthy, the binary sensor shows state "on" (Connected).
result: pass

### 3. Binary Sensor Shows Down State
expected: For a Gatus endpoint that is currently failing, the binary sensor shows state "off" (Disconnected). The `error_reason` attribute contains the text of the first failing condition.
result: pass

### 4. Binary Sensor Attributes Present
expected: Opening the binary sensor entity detail shows four attributes: `last_check_timestamp` (ISO datetime string), `error_reason` (null or a condition string), `response_duration_ms` (integer, milliseconds), and `consecutive_failures` (integer ≥ 0).
result: pass

### 5. Response Time Sensor
expected: A sensor entity for each Gatus endpoint shows the last response duration in milliseconds as an integer. The entity's unit is `ms` and its device class is Duration.
result: pass

### 6. Uptime Sensor
expected: A sensor entity for each Gatus endpoint shows an uptime percentage (float) based on available results. If Gatus returns no results for an endpoint, the sensor state shows "unknown".
result: pass

### 7. Conditions Sensor Shows X/Y Format
expected: A sensor entity for each Gatus endpoint shows the conditions result as a string like "2/3" (passed/total). The `condition_details` attribute contains a list of individual condition results.
result: pass

### 8. Stale Endpoint Cleanup
expected: If a Gatus endpoint is removed from the Gatus server and the coordinator refreshes, the corresponding HA entities for that endpoint are removed from the entity registry automatically (no orphaned entities remain).
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]

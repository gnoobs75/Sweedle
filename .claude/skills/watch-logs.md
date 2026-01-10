# /watch-logs

Stream backend logs in real-time for debugging.

## Usage
```
/watch-logs [--filter generation|rigging|vram|error]
```

## Options
- Default: All logs
- `--filter generation`: Only generation-related logs
- `--filter rigging`: Only rigging-related logs
- `--filter vram`: Only VRAM/memory-related logs
- `--filter error`: Only errors and warnings

## Instructions

### Log File Location
```
C:\Claude\Sweedle\backend\sweedle.log
```

### Watch All Logs
Read the log file and present recent entries:
```powershell
Get-Content "C:\Claude\Sweedle\backend\sweedle.log" -Tail 50
```

For continuous watching (in a separate terminal):
```powershell
Get-Content "C:\Claude\Sweedle\backend\sweedle.log" -Tail 20 -Wait
```

### Filter: Generation
Look for these patterns:
- `generation.service`
- `inference.pipeline`
- `_generate_shape`
- `_generate_texture`
- `Shape complete`
- `Texture generation`

```powershell
Select-String -Path "C:\Claude\Sweedle\backend\sweedle.log" -Pattern "generation|pipeline|shape|texture" | Select-Object -Last 30
```

### Filter: Rigging
Look for these patterns:
- `rigging`
- `skeleton`
- `auto-rig`
- `bone`

```powershell
Select-String -Path "C:\Claude\Sweedle\backend\sweedle.log" -Pattern "rigging|skeleton|rig|bone" | Select-Object -Last 30
```

### Filter: VRAM
Look for these patterns:
- `VRAM`
- `memory`
- `allocated`
- `reserved`
- `offload`
- `empty_cache`

```powershell
Select-String -Path "C:\Claude\Sweedle\backend\sweedle.log" -Pattern "VRAM|memory|allocated|reserved|offload|cache" | Select-Object -Last 30
```

### Filter: Errors
Look for these patterns:
- `ERROR`
- `WARNING`
- `Exception`
- `failed`
- `crash`

```powershell
Select-String -Path "C:\Claude\Sweedle\backend\sweedle.log" -Pattern "ERROR|WARNING|Exception|failed|crash|Traceback" | Select-Object -Last 30
```

### Report Format
Present logs in a readable format:
```
Backend Logs [filter: <filter>]
===============================
Last updated: <timestamp>

[timestamp] [level] [module] - message
[timestamp] [level] [module] - message
...

---
Showing last 30 entries. Log file: C:\Claude\Sweedle\backend\sweedle.log
```

### Tips
- If log file is empty, backend may not be running
- Log file is overwritten each time backend starts (mode='w')
- For persistent logs, change FileHandler mode to 'a' in main.py

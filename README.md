# Shogun: Total War Gold - Harvest Report Restoration Fix

Patches `ShogunM.exe` directly to restore the original annual harvest report voices in **SHOGUN: Total War Gold**.

The patch also includes my throne-room audio fix, so the restored harvest speech uses the fixed audio path and plays to the end instead of cutting off early.

---

## The problem

In the original v1.0.0 release, the yearly harvest report played a messenger voice line for the harvest result when the report appeared between Autumn and Winter.

In the later Gold executable, the report still appears and the text still changes, but the harvest voice line no longer plays:

- the harvest voice line does not play
- the report uses the normal UI/sword sound instead

The needed voice clips are still in the Gold install as MP3 files under the English and Japanese voice folders. The executable just no longer uses them for this report.

---

## What this fix changes

Nine byte patches to `ShogunM.exe`:

| Patch | What it does |
|---|---|
| `AudioEosCheckEntry` | Redirects the audio-only end-of-stream check to the fixed timing logic from the throne-room audio patch. |
| `AudioDurationScalingGate` | Removes the bad duration scaling that can make speech end too early. |
| `AudioPostEofDelayGate` | Replaces the broken post-EOF delay path used by streamed speech. |
| `AudioStreamTimingCodeCave` | Adds the fixed stream-timing logic used by the audio patch. |
| `AudioScriptCleanupGate` | Redirects script cleanup through a guard so live speech is not destroyed too soon. |
| `AudioCleanupGuardCodeCave` | Adds the active-speech cleanup guard. |
| `HarvestReportUseMp3Suffix` | Makes the harvest report use `.Mp3` harvest voice clips. |
| `HarvestReportVoiceHook` | Redirects the harvest report setup to the restoration code cave. |
| `HarvestReportCodeCave` | Starts the harvest voice line while preserving the original harvest artwork frame IDs. |

All patches target specific file offsets. The patcher reads and validates the exact bytes at every location before writing anything.

---

## Requirements

- Windows
- Python 3.9 or newer

---

## Quick start

Run from a terminal in the folder containing the script:

```powershell
python .\shogun_harvest_audio_fix.py "F:\Games\Shogun Total War Gold"
```

The script will back up `ShogunM.exe`, apply the audio and harvest report fixes, then print the resulting SHA-256 hash.

---

## Usage

You can pass either the game folder or the EXE directly:

```powershell
# Patch using the game folder
python .\shogun_harvest_audio_fix.py "F:\Games\Shogun Total War Gold"

# Or point at the EXE directly
python .\shogun_harvest_audio_fix.py "F:\Games\Shogun Total War Gold\ShogunM.exe"
```

With no argument, the script looks for `ShogunM.exe` in the current directory:

```powershell
python .\shogun_harvest_audio_fix.py
```

Check patch status without making changes:

```powershell
python .\shogun_harvest_audio_fix.py --verify "F:\Games\Shogun Total War Gold"
```

Restore from backup:

```powershell
python .\shogun_harvest_audio_fix.py --restore "F:\Games\Shogun Total War Gold"
```

`--verify` and `--restore` cannot be used together.

---

## Backup and restore

Before patching, the script creates:

```
ShogunM.exe.harvest-report-restoration-fix.bak
```

in the same folder as the EXE. If a backup already exists, the script notes it and does not overwrite it.

To roll back:

- Run `--restore`, or
- Copy `ShogunM.exe.harvest-report-restoration-fix.bak` back over `ShogunM.exe` manually.

If the unit-cost patch or throne-room audio patch was already applied before running this patcher, the backup contains that state. Restoring later returns you to that state, not necessarily to the bare original executable.

---

## Compatibility with the unit-cost fix

Verified against: [LouieWoolger/shogun-total-war-unit-cost-training-upkeep-fix](https://github.com/LouieWoolger/shogun-total-war-unit-cost-training-upkeep-fix/tree/main)

The unit-cost/training/upkeep fix is still a separate patch. This patch is compatible with it, but does not include it.

The patch offsets do not overlap with the unit-cost patch. The two patches can be applied independently in either order.

This patch already includes the throne-room audio fix, so you do not need to run the separate audio patch first. If the audio patch is already present, those bytes are detected and left intact.

---

## Supported targets

The patcher is strict. It checks the bytes at each patch location before writing anything. If the bytes do not match what is expected, it refuses to patch rather than writing over an unknown state.

The patch can be applied to:

- A clean original GOG or Steam `ShogunM.exe`
- A `ShogunM.exe` that already has my throne-room audio fix applied
- A `ShogunM.exe` that already has my unit-cost patch applied
- A `ShogunM.exe` that already has both patches applied

It cannot be applied to an EXE that has been modified at the same offsets by another patch. If the script reports unsupported bytes, restore a clean `ShogunM.exe` first and run the patcher again.

Known SHA-256 values for a correctly patched EXE:

```
C7C3A70B5F281546F6A44F975EE795EE157D72A276007F983588F55EC88A9B89  original GOG/Steam + harvest report fix
1154B5703769809D56B80DDB5B25BD98DEE2DED19721AEEFA9254D3EB81A9F78  unit-cost-patched + harvest report fix
```

Known SHA-256 value for the clean reference executable:

```
4445DCB123D595A9B68FD18A20B98A9F9332F9651474976636CB9EC54F3D16AF  original GOG/Steam
```

---

## Verifying the fix in-game

1. Launch the patched `ShogunM.exe`.
2. Start or load a campaign.
3. End turns until the annual harvest report appears between Autumn and Winter.
4. The report should play the correct harvest messenger voice line.

If the unit-cost fix is also applied, recruitment costs, training times, and upkeep should remain unchanged by this patch.

---

## Notes

- If the script reports `status=already_patched`, no changes are made.
- `audio_fix_present=yes` means the throne-room audio fix bytes are present.
- `harvest_restoration_fix_present=yes` means the harvest report voice hook is present and the original artwork frame IDs are preserved.
- `missing_english_harvest_mp3_assets` or `missing_japanese_harvest_mp3_assets` means the EXE patch is installed but the expected harvest MP3 files were not found in that game folder.
- `unknown_unsupported` means one or more byte locations contain unexpected values.

---

## Technical details

Gold still contains the harvest result names and voice path used by the report:

```
\Throne\Messenger\Harvest\
Average
Bumper
Disastrous
Good
Poor
```

The report path originally points at a WAV suffix. This patch changes that suffix to MP3, which matches the Gold install, including the Japanese harvest clips under:

```
Foices\Throne\Messenger\Harvest
```

The patch leaves the harvest report artwork frame IDs intact:

```
Disastrous/Poor = 0
Average         = 14
Good/Bumper     = 13
```

Those frames are read from the existing `campmap\Epic.BIF` file.

### Patch locations

| # | File offset | VA | Description |
|---|---|---|---|
| 1 | `0x001B7CCB` | `0x005B7CCB` | Audio EOF check entry to code cave |
| 2 | `0x001B80D2` | `0x005B80D2` | Audio duration scaling gate to code cave |
| 3 | `0x001B7916` | `0x005B7916` | Audio post-EOF delay selection to code cave |
| 4 | `0x0031ABE0` | `0x0071ABE0` | Audio stream timing code cave |
| 5 | `0x00198FA5` | `0x00598FA5` | Audio script cleanup gate to code cave |
| 6 | `0x0031AC58` | `0x0071AC58` | Audio cleanup guard code cave |
| 7 | `0x00149D7F` | `0x00549D7F` | Harvest report MP3 suffix |
| 8 | `0x00149D88` | `0x00549D88` | Harvest report voice hook |
| 9 | `0x0031AC80` | `0x0071AC80` | Harvest report voice code cave and preserved artwork frame IDs |

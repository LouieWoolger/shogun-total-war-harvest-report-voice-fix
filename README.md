# Shogun: Total War Gold - Harvest Report Voice Fix
[![Downloads](https://img.shields.io/github/downloads/LouieWoolger/shogun-total-war-harvest-report-voice-fix/total?style=for-the-badge)](https://github.com/LouieWoolger/shogun-total-war-harvest-report-voice-fix/releases)
[![Release](https://img.shields.io/github/v/release/LouieWoolger/shogun-total-war-harvest-report-voice-fix?style=for-the-badge)](https://github.com/LouieWoolger/shogun-total-war-harvest-report-voice-fix/releases/latest)
[![Discord](https://img.shields.io/discord/1505490825889579018?style=for-the-badge&logo=discord&label=Discord&color=5865F2)](https://discord.gg/zKbDADqWRC)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support-FF5F5F?style=for-the-badge&logo=ko-fi)](https://ko-fi.com/louiewoolger)

Restores the missing harvest report voice lines in Shogun: Total War Gold by patching `ShogunM.exe` directly. The annual harvest messenger speech stopped playing in the Gold executable; the voice files are still present on disk under `Voices\Throne\Messenger\Harvest\` and `Foices\Throne\Messenger\Harvest\` but the EXE no longer calls them. This patch also bundles the throne-room audio fix, so the restored harvest speech uses the corrected stream-timing path and plays to completion rather than cutting off.

## Requirements

- Windows
- Python 3.9 or newer

## Usage

Pass the game folder or the path to `ShogunM.exe`:

```powershell
python .\shogun_harvest_audio_fix.py "F:\Games\Shogun Total War Gold"
python .\shogun_harvest_audio_fix.py "F:\Games\Shogun Total War Gold\ShogunM.exe"
```

With no argument, the script looks for `ShogunM.exe` in the current directory.

Inspect without writing changes:

```powershell
python .\shogun_harvest_audio_fix.py --verify "F:\Games\Shogun Total War Gold"
```

Restore from backup:

```powershell
python .\shogun_harvest_audio_fix.py --restore "F:\Games\Shogun Total War Gold"
```

`--verify` and `--restore` cannot be combined.

## Notes

Before patching, the script creates `ShogunM.exe.harvest-report-restoration-fix.bak` in the same folder as the EXE. An existing backup is preserved and will not be overwritten.

The patcher validates the exact bytes at every patch location before writing. If `--verify` reports `unknown_unsupported`, restore a clean `ShogunM.exe` first and run again.

The patch can be applied to a clean original, a unit-cost-patched, or a throne-room-audio-patched executable in any combination. The harvest fix offsets do not overlap with either patch. This fix includes the throne-room audio bytes; if already present, those bytes are detected and left intact.

Known SHA-256 values:

```
4445DCB123D595A9B68FD18A20B98A9F9332F9651474976636CB9EC54F3D16AF  original GOG/Steam
A6CECD32946C10B152ADBC8D922BEAC8A67F7A639E6C4A10297297310C427285  unit-cost fix only
11356636154934CC2FF2ED26B46FD82155C05EB52873FE6763F7FD22B1344D32  audio fix only
141C971763DC50AC2D5DD131E7FECAE87914C96FDB87B4EF25820E3B7A8C89DC  unit-cost + audio fixes
C7C3A70B5F281546F6A44F975EE795EE157D72A276007F983588F55EC88A9B89  audio + harvest report fixes
1154B5703769809D56B80DDB5B25BD98DEE2DED19721AEEFA9254D3EB81A9F78  unit-cost + audio + harvest report fixes
```

Status messages from `--verify`:

- `state=patched` — audio and harvest restoration bytes are present
- `combined_state=unit_audio_harvest_fixes` — all three supported fixes are present
- `unit_fix_present=yes` — unit-cost, upkeep, and training-time fix bytes are present
- `audio_fix_present=yes` — throne-room audio fix bytes are present
- `harvest_restoration_fix_present=yes` — harvest voice hook is in place
- `missing_english_harvest_mp3_assets` / `missing_japanese_harvest_mp3_assets` — EXE is patched but expected MP3 files were not found in the game folder
- `unknown_unsupported` — unexpected bytes at one or more patch locations

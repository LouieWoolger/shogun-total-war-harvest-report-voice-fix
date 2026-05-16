#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


PATCH_NAME = "Shogun: Total War Gold - Harvest Report Restoration Fix"
VERSION = "v1.0.0"
EXE_NAME = "ShogunM.exe"
EXPECTED_EXE_SIZE = 7_319_552
BACKUP_SUFFIX = ".harvest-report-restoration-fix.bak"

ORIGINAL_GOLD_SHA256 = "4445DCB123D595A9B68FD18A20B98A9F9332F9651474976636CB9EC54F3D16AF"
PATCHED_AUDIO_AND_HARVEST_SHA256 = "C7C3A70B5F281546F6A44F975EE795EE157D72A276007F983588F55EC88A9B89"

HARVEST_CLIPS = ("Average", "Bumper", "Disastrous", "Good", "Poor")


@dataclass(frozen=True)
class BytePatch:
    name: str
    offset: int
    va: int
    original: bytes
    patched: bytes
    description: str

    def __post_init__(self) -> None:
        if len(self.original) != len(self.patched):
            raise ValueError(
                f"{self.name} has mismatched lengths: "
                f"original={len(self.original)} patched={len(self.patched)}"
            )


@dataclass(frozen=True)
class InspectResult:
    exe_path: Path
    sha256: str
    state: str
    patchable: bool
    supported_state: bool
    audio_fix_present: bool
    harvest_fix_present: bool
    english_harvest_mp3_assets_present: bool
    japanese_harvest_mp3_assets_present: bool
    backup_path: Path
    notes: tuple[str, ...]


@dataclass(frozen=True)
class ApplyResult:
    before: InspectResult
    after: InspectResult
    backup_path: Path | None
    created_backup: bool
    writes_applied: tuple[BytePatch, ...]


HARVEST_WAV_SUFFIX_BYTES = bytes.fromhex("60 32 F1 00")
HARVEST_MP3_SUFFIX_BYTES = bytes.fromhex("80 33 F1 00")

SUFFIX_PATCH = BytePatch(
    name="HarvestReportUseMp3Suffix",
    offset=0x00149D7F,
    va=0x00549D7F,
    original=HARVEST_WAV_SUFFIX_BYTES,
    patched=HARVEST_MP3_SUFFIX_BYTES,
    description="Use Gold's MP3 harvest voice clips, including Japanese Foices assets.",
)

HARVEST_FRAME_ID_SETUP = bytes.fromhex(
    "33 C9 "
    "89 8C 24 80 02 00 00 "
    "89 8C 24 84 02 00 00 "
    "C7 84 24 88 02 00 00 0E 00 00 00 "
    "B8 0D 00 00 00 "
    "89 84 24 8C 02 00 00 "
    "89 84 24 90 02 00 00"
)

HOOK_PATCH = BytePatch(
    name="HarvestReportVoiceHook",
    offset=0x00149D88,
    va=0x00549D88,
    original=HARVEST_FRAME_ID_SETUP,
    patched=bytes.fromhex(
        "E9 F3 0E 1D 00 "
        "90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 "
        "90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 "
        "90 90 90 90 90 90 90 90 90"
    ),
    description="Redirect harvest report setup to the restoration code cave.",
)

HARVEST_AUDIO_CAVE_TAIL = bytes.fromhex(
    "9C 60 8B 0D 1C 88 C2 00 85 "
    "C9 74 11 6A 01 E8 E6 D2 E2 FF C7 05 1C 88 C2 00 "
    "00 00 00 00 6A 68 E8 C4 15 FE FF 83 C4 04 85 C0 "
    "74 26 89 C6 31 D2 88 56 01 89 56 04 89 56 08 C6 "
    "46 0C 01 8D 94 24 64 02 00 00 52 89 F1 E8 AE D5 "
    "E9 FF 89 35 1C 88 C2 00 61 9D 31 C9 E9 A5 F0 E2 FF"
)

RESTORED_HARVEST_CODE_CAVE = HARVEST_FRAME_ID_SETUP + (b"\x90" * 9) + HARVEST_AUDIO_CAVE_TAIL

CODE_CAVE_PATCH = BytePatch(
    name="HarvestReportCodeCave",
    offset=0x0031AC80,
    va=0x0071AC80,
    original=bytes(0x91),
    patched=RESTORED_HARVEST_CODE_CAVE,
    description="Start harvest audio while preserving Epic.BIF harvest illustration frame IDs.",
)

HARVEST_PATCHES = (SUFFIX_PATCH, HOOK_PATCH, CODE_CAVE_PATCH)

AUDIO_FIX_PATCHES = (
    BytePatch(
        "AudioEosCheckEntry",
        0x001B7CCB,
        0x005B7CCB,
        bytes.fromhex("8B 4E 60 85 C9 74"),
        bytes.fromhex("E9 10 2F 16 00 90"),
        "Route streaming audio EOF checks through the timing guard.",
    ),
    BytePatch(
        "AudioDurationScalingGate",
        0x001B80D2,
        0x005B80D2,
        bytes.fromhex("8A 45 18 84 C0 75 32"),
        bytes.fromhex("E9 49 2B 16 00 90 90"),
        "Prevent premature stream cleanup while campaign speech is still active.",
    ),
    BytePatch(
        "AudioPostEofDelayGate",
        0x001B7916,
        0x005B7916,
        bytes.fromhex("8A 45 18 84 C0 74 07 B8 01 00 00 00 EB 05"),
        bytes.fromhex("E9 1C 33 16 00 90 90 90 90 90 90 90 90 90"),
        "Use the fixed post-EOF delay for streamed speech.",
    ),
    BytePatch(
        "AudioStreamTimingCodeCave",
        0x0031ABE0,
        0x0071ABE0,
        bytes(0x78),
        bytes.fromhex(
            "8B 4E 60 85 C9 75 34 8B 4E 54 85 C9 74 23 8D 44 "
            "24 10 50 51 8B 01 FF 50 20 85 C0 7C 14 8B 54 24 "
            "10 8B 7C 24 14 8B 46 40 8B 76 44 29 C2 19 F7 7C "
            "05 E9 E4 D0 E9 FF E9 EA D0 E9 FF E9 B2 D0 E9 FF "
            "83 7D 60 00 74 0C 8A 45 18 84 C0 75 05 E9 A7 D4 "
            "E9 FF E9 D4 D4 E9 FF 83 7D 60 00 74 07 8A 45 18 "
            "84 C0 74 0A B8 01 00 00 00 E9 DB CC E9 FF B8 88 "
            "13 00 00 E9 D1 CC E9 FF"
        ),
        "Timing guard code cave used by the throne-room audio cutoff fix.",
    ),
    BytePatch(
        "AudioScriptCleanupGate",
        0x00198FA5,
        0x00598FA5,
        bytes.fromhex("A9 FF 00 00 00 75 05 E8 2F F8 FF FF"),
        bytes.fromhex("E9 AE 1C 18 00 90 90 90 90 90 90 90"),
        "Route scripted speech cleanup through the active-stream guard.",
    ),
    BytePatch(
        "AudioCleanupGuardCodeCave",
        0x0031AC58,
        0x0071AC58,
        bytes(0x20),
        bytes.fromhex(
            "A9 FF 00 00 00 75 14 8B 0D 80 79 C9 00 85 C9 74 "
            "05 80 39 00 75 05 E8 6D DB E7 FF E9 39 E3 E7 FF"
        ),
        "Cleanup guard code cave used by the throne-room audio cutoff fix.",
    ),
)

RELEASE_PATCHES = AUDIO_FIX_PATCHES + HARVEST_PATCHES


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def resolve_exe(target: str | Path) -> Path:
    path = Path(target).expanduser().resolve()
    if path.is_dir():
        path = path / EXE_NAME
    if not path.exists():
        raise FileNotFoundError(f"target not found: {path}")
    if path.name.lower() != EXE_NAME.lower():
        raise ValueError(f"target must be {EXE_NAME} or a folder containing it: {path}")
    return path


def backup_path(exe_path: Path) -> Path:
    return exe_path.with_name(exe_path.name + BACKUP_SUFFIX)


def harvest_mp3_assets_present(game_dir: Path, root_name: str) -> bool:
    harvest_root = game_dir / root_name / "Throne" / "Messenger" / "Harvest"
    return harvest_root.exists() and all((harvest_root / f"{clip}.mp3").exists() for clip in HARVEST_CLIPS)


def group_state(data: bytes, patches: tuple[BytePatch, ...]) -> tuple[str, tuple[str, ...]]:
    states: list[str] = []
    notes: list[str] = []
    for patch in patches:
        end = patch.offset + len(patch.original)
        current = data[patch.offset:end]
        if len(current) != len(patch.original):
            states.append("unknown")
            notes.append(f"{patch.name}: target is too small for offset 0x{patch.offset:08X}")
        elif current == patch.original:
            states.append("clean")
        elif current == patch.patched:
            states.append("patched")
        else:
            states.append("unknown")
            notes.append(
                f"{patch.name}: unsupported bytes at 0x{patch.offset:08X} "
                f"(found {current.hex(' ')})"
            )

    unique = set(states)
    if "unknown" in unique:
        return "unknown", tuple(notes)
    if unique == {"clean"}:
        return "clean", ()
    if unique == {"patched"}:
        return "patched", ()
    return "partial", ()


def inspect_exe(target: str | Path) -> InspectResult:
    exe_path = resolve_exe(target)
    data = exe_path.read_bytes()
    digest = sha256_bytes(data)
    notes: list[str] = []

    if len(data) != EXPECTED_EXE_SIZE:
        notes.append(f"unexpected_exe_size={len(data)} expected={EXPECTED_EXE_SIZE}")

    audio_state, audio_notes = group_state(data, AUDIO_FIX_PATCHES)
    harvest_state, harvest_notes = group_state(data, HARVEST_PATCHES)
    notes.extend(audio_notes)
    notes.extend(harvest_notes)

    english_assets = harvest_mp3_assets_present(exe_path.parent, "Voices")
    japanese_assets = harvest_mp3_assets_present(exe_path.parent, "Foices")
    if not english_assets:
        notes.append("missing_english_harvest_mp3_assets root=Voices\\Throne\\Messenger\\Harvest")
    if not japanese_assets:
        notes.append("missing_japanese_harvest_mp3_assets root=Foices\\Throne\\Messenger\\Harvest")

    if "unknown" in {audio_state, harvest_state}:
        state = "unknown"
    elif audio_state == "patched" and harvest_state == "patched":
        state = "patched"
    elif audio_state == "clean" and harvest_state == "clean":
        state = "clean"
    else:
        state = "partial"

    supported_state = state in {"clean", "partial", "patched"} and len(data) == EXPECTED_EXE_SIZE
    patchable = supported_state and state != "patched"

    return InspectResult(
        exe_path=exe_path,
        sha256=digest,
        state=state,
        patchable=patchable,
        supported_state=supported_state,
        audio_fix_present=audio_state == "patched",
        harvest_fix_present=harvest_state == "patched",
        english_harvest_mp3_assets_present=english_assets,
        japanese_harvest_mp3_assets_present=japanese_assets,
        backup_path=backup_path(exe_path),
        notes=tuple(notes),
    )


def apply_patch(target: str | Path) -> ApplyResult:
    exe_path = resolve_exe(target)
    before = inspect_exe(exe_path)
    if not before.supported_state:
        raise RuntimeError("The target executable is unsupported. Run with --verify for details.")
    if before.state == "patched":
        return ApplyResult(before=before, after=before, backup_path=before.backup_path, created_backup=False, writes_applied=())

    data = bytearray(exe_path.read_bytes())
    applied: list[BytePatch] = []
    for patch in RELEASE_PATCHES:
        end = patch.offset + len(patch.original)
        current = data[patch.offset:end]
        if current == patch.patched:
            continue
        if current != patch.original:
            raise RuntimeError(
                f"Unsupported bytes at 0x{patch.offset:08X} for {patch.name}: {current.hex(' ')}"
            )
        data[patch.offset:end] = patch.patched
        applied.append(patch)

    backup = before.backup_path
    created_backup = False
    if applied and not backup.exists():
        shutil.copy2(exe_path, backup)
        created_backup = True

    if applied:
        exe_path.write_bytes(data)

    after = inspect_exe(exe_path)
    if after.state != "patched":
        raise RuntimeError("Patch completed, but the final executable was not detected as patched.")
    if before.sha256 == ORIGINAL_GOLD_SHA256 and after.sha256 != PATCHED_AUDIO_AND_HARVEST_SHA256:
        raise RuntimeError(f"Unexpected final hash after patching clean Gold EXE: {after.sha256}")

    return ApplyResult(
        before=before,
        after=after,
        backup_path=backup,
        created_backup=created_backup,
        writes_applied=tuple(applied),
    )


def restore_patch(target: str | Path) -> InspectResult:
    exe_path = resolve_exe(target)
    before = inspect_exe(exe_path)
    if before.state == "unknown":
        raise RuntimeError("The target executable has unsupported bytes in one or more patch locations.")

    backup = before.backup_path
    if backup.exists():
        shutil.copy2(backup, exe_path)
        return inspect_exe(exe_path)

    if before.state == "clean":
        return before

    data = bytearray(exe_path.read_bytes())
    for patch in RELEASE_PATCHES:
        end = patch.offset + len(patch.patched)
        current = data[patch.offset:end]
        if current == patch.patched:
            data[patch.offset:end] = patch.original
        elif current != patch.original:
            raise RuntimeError(
                f"Unsupported bytes at 0x{patch.offset:08X} for {patch.name}: {current.hex(' ')}"
            )
    exe_path.write_bytes(data)
    return inspect_exe(exe_path)


def print_header() -> None:
    print(f"{PATCH_NAME} {VERSION}")
    print("=" * (len(PATCH_NAME) + len(VERSION) + 1))


def print_inspection(result: InspectResult) -> None:
    print(f"target={result.exe_path}")
    print(f"sha256={result.sha256}")
    print(f"state={result.state}")
    print(f"patchable={'yes' if result.patchable else 'no'}")
    print(f"supported_state={'yes' if result.supported_state else 'no'}")
    print(f"audio_fix_present={'yes' if result.audio_fix_present else 'no'}")
    print(f"harvest_restoration_fix_present={'yes' if result.harvest_fix_present else 'no'}")
    print(
        "english_harvest_mp3_assets_present="
        f"{'yes' if result.english_harvest_mp3_assets_present else 'no'}"
    )
    print(
        "japanese_harvest_mp3_assets_present="
        f"{'yes' if result.japanese_harvest_mp3_assets_present else 'no'}"
    )
    print(f"backup={result.backup_path if result.backup_path.exists() else 'not_found'}")
    for note in result.notes:
        print(f"note={note}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Apply, verify, or restore the SHOGUN: Total War Gold harvest report "
            "voice/image restoration fix. The patch includes the throne-room audio cutoff fix."
        )
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help=f"Path to {EXE_NAME} or its game folder. Defaults to the current directory.",
    )
    parser.add_argument("--verify", action="store_true", help="Inspect only; do not modify the executable.")
    parser.add_argument("--restore", action="store_true", help="Restore from backup, or restore original patch bytes.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.verify and args.restore:
        parser.error("--verify and --restore cannot be used together")

    print_header()
    try:
        if args.verify:
            result = inspect_exe(args.target)
            print_inspection(result)
            return 0 if result.supported_state else 1
        if args.restore:
            result = restore_patch(args.target)
            print("status=restored")
            print_inspection(result)
            return 0 if result.supported_state else 1

        applied = apply_patch(args.target)
        if applied.writes_applied:
            if applied.created_backup:
                print(f"backup_created={applied.backup_path}")
            else:
                print(f"backup_preserved={applied.backup_path}")
            for patch in applied.writes_applied:
                print(
                    f"patched {patch.name} file=0x{patch.offset:08X} "
                    f"va=0x{patch.va:08X} description={patch.description}"
                )
        else:
            print("status=already_patched")
            if applied.backup_path and applied.backup_path.exists():
                print(f"backup_preserved={applied.backup_path}")
        print_inspection(applied.after)
        return 0
    except Exception as exc:
        print(f"error={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

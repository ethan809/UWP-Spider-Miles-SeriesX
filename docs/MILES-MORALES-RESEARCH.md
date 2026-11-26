# Miles Morales on Xbox Series X — engineering status

**Current status: research only. No booting or playable Xbox port.**

The fork's launcher identifies Miles Morales executable names in ZIP imports,
Wi-Fi folder transfers and USB folder imports (if `Spider-Man.exe` is missing).
It gives a Miles-specific, non-playable diagnostic rather than treating Miles
files as Remastered files. The existing Remastered fingerprints stay enforced.

The public UWP Spider Launcher hard-codes `Spider-Man.exe`, approved Remastered
executable hashes, Remastered asset indexes, and the Remastered-specific
preparation/runtime scheme. Miles Morales is a different game and uses
`MilesMorales.exe` (Steam app ID `1817190`). Renaming the executable or
disabling the hash check is not a compatibility solution and must not be done.

The source repository **does not include** the native compatibility-runtime
sources or binaries, matching native adapters, preparation payloads, or
complete playable Xbox installer. These are critical independent blockers.
The current launcher is only tested primarily on Xbox Series X with
Spider-Man Remastered; its 5 GiB UWP game-memory allocation remains a constraint.

## First milestone: characterize owned PC files

From the cloned repository, on a PC or Mac with Python 3:

```bash
python3 tools/inspect_miles.py "/path/to/Marvel's Spider-Man Miles Morales" --output miles-profile-local.json
```

The script **does not run the game, modify game files, download files, or
upload information**. It lists relative filenames and sizes and hashes the
executable and `asset_archive/toc`. It also inspects the static Windows PE
import table to identify DLL functions needed for a future native runtime.
This does not catch dynamically loaded DLLs or prove runtime compatibility.
Add `--hash-assets` to generate an exact
SHA-256 file manifest; hashing the full game can take a long time.

Do not commit generated profiles automatically. A profile can contain exact
details of a particular game installation or mods. Review the file first.
Never share game files, Steam login details, saves, or signing keys.

## Requirements before calling this compatible

### Native-runtime gap analysis (stage 3 started)

The original project does not include the runtime. A separate open-source
candidate is [Tiramisu](https://github.com/xanstomper/tiramisu), an MIT-licensed
Xbox UWP x64 Windows-application runtime. Its November 2026 project notes
describe D3D12 execution and AAA-title verification as incomplete/experimental.
It is **not** a verified Miles Morales runtime. Do not assume its list of
function names proves that DirectX 12 rendering or audio works in this game.

The next investigation can compare a local Miles Morales profile's static
PE imports against **audited** exports from a selected runtime:

```bash
python3 tools/runtime_gap.py miles-profile-local.json runtime-exports-local.json
```

The runtime exports file is JSON shaped like
`{"exported_functions":{"d3d12.dll":["D3D12CreateDevice"]}}`.
These must be *actual verified exports*, not guessed capabilities. The program
prints missing symbols and explicitly does not claim a bootable game.

Actual Series X testing requires a legitimately owned PC copy and access to
the developer-mode console or its logs. Neither is present in this repository.

### Implementation gates

- Obtain a verifiable manifest for one *specific* Miles Morales PC build,
  including its executable, asset archive and required DLLs. Keep normal
  version rejection for all unrecognized files.
- Develop or lawfully obtain an Xbox UWP x64 native runtime with the imports,
  executable setup and graphics pipeline needed by this game. The Remastered
  runtime is not in this public source tree and cannot be assumed to work.
- Implement title-specific extraction/conversion of *owned* assets without
  mixing Remastered patches, shader recipes or runtime offsets into Miles files.
- Test startup, input, rendering and memory usage on an actual Xbox Series X
  in UWP Game mode; then test long gameplay, loading, fast travel and saves.
- Keep any Steam-owned assets and derived executables out of public releases.

## Checks

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Passing these tests validates only the read-only inspection tool. It is not
evidence that Miles Morales launches or plays on Xbox.

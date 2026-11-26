# Miles Morales on Xbox Series X — first real boot attempt

**Status: an actionable console experiment, not a confirmed boot.** This
project still has no Miles Morales native runtime. The fastest honest attempt
is to run the legally owned Windows copy through the separate, open-source
[Tiramisu](https://github.com/xanstomper/Tiramisu) UWP PE64 runtime.

Tiramisu has Xbox Series console evidence for *other games*. Its own current
documentation says D3D12 AAA rendering is not verified and some audio/video
middleware is incomplete. **Nobody has established that Miles Morales boots.**

## On the Series X (no PC game upload necessary)

1. Open Xbox **Dev Home**. Enable **Xbox Device Portal** (remote access) and
   **Treat UWP apps as games by default** for its larger memory allowance.
2. On a phone or Mac on the same network, open the
   [official Tiramisu releases](https://github.com/xanstomper/Tiramisu/releases).
   Download `Tiramisu.msix` and matching `dev.cer` from the same release.
   Do not mix the ordinary and EdgeSpoof packages/certificates.
3. Follow the developer's [installation guide](https://github.com/xanstomper/Tiramisu/blob/master/docs/BEGINNER-INSTALL.md)
   to install the MSIX in Xbox Device Portal at
   `https://<xbox-ip>:11443`. It is a **separate UWP app** from this fork.
4. Launch **Tiramisu** on the Xbox and open its LAN dashboard through the QR
   code or `http://<xbox-ip>:9127` on the phone/Mac. Use its **Steam** tab to
   sign in to the Steam account that actually owns *Marvel's Spider-Man: Miles
   Morales* (Steam app **1817190**). Never send credentials, Steam tokens,
   or your Xbox Device Portal password to this repository or a chat.
5. If Tiramisu exposes a legitimate download option for that game, use it.
   Allow roughly **47.4 GiB** for the current English Windows game plus spare
   space; downloads may take a while. If ownership/manifest access is refused,
   stop and report that exact stage. Do not bypass Steam checks.
6. Once the game is fully downloaded **inside Tiramisu**, select
   `MilesMorales.exe` and try **Launch**. Record the outcome honestly:
   launcher refused, executable mapped, crash, black screen, menu, or actual
   gameplay. An app loading its own dashboard is **not** Miles booting.

This fork's prototype `MilesMoralesSteam` folder is owned by a different UWP
app. **It is not automatically shared with Tiramisu**. Use Tiramisu's own
Steam download/import path rather than assuming one app can launch a file
stored in another app's private area.

## Collect evidence without posting the game

Tiramisu logs fatal faults and the bridge/API responsible. Export the console
log from the Tiramisu LAN dashboard. On a Mac or PC with Python 3, from this
fork run:

```bash
python3 tools/miles_boot_report.py path/to/tiramisu-console.log
```

The tool reads a log, isolates the `MilesMorales.exe` launch session and prints
a small JSON report of **observed** loader steps and named failures. It never
extracts or shares raw game files, account IDs or private console paths. It
cannot infer that gameplay works from a PE mapping or D3D12 function call.
For a credible boot result, save a short Series X screen recording along with
a title-specific log. Review logs before sharing them; raw logs may contain
usernames and local paths.

## Decision points

- **No game shown in Steam library:** confirm it is owned and installed or
  supported by Tiramisu's Steam downloader. No compatibility inference yet.
- **`MilesMorales.exe` cannot load:** examine the first import, licensing,
  memory or missing-file failure; use `tools/runtime_gap.py` on a genuine PE
  profile only if needed.
- **PE maps but fails before graphics:** the title has not booted. The report
  should identify the first error; any fix belongs in a properly tested runtime.
- **A D3D12 call occurs:** this is progress, not proof of a frame.
- **Actual menu/3D frame shown:** capture video and logs before marking a boot.

The runtime and its own game downloader are maintained by
[xanstomper/Tiramisu](https://github.com/xanstomper/Tiramisu), not by this
fork. Do not redistribute its signed package or any game payload as a release
of this project. No console has been accessed by this repository work.

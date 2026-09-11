# WhiteFlood Android Pilot v0.1.2

## Purpose

Diagnostic and guard release for the Android upscale path after physical-device testing showed that the save/copy stage could hide the original NCNN/RealSR failure behind a missing `output.png` message.

## Runtime changes

- Preflight the local upscale engine and required model directory before execution.
- Stop the export chain when the engine command fails.
- Require a non-empty `output.png` before the save/export step.
- Surface the native process exit code and preserve the engine log for diagnosis.
- Keep the existing local 2x and 4x photo presets and content-URI materialization path.

## Verification boundary

- CI build and repository audit must pass before publishing.
- Physical-device upscale success is not claimed by CI.
- The release remains a pre-release until select photo -> preview -> upscale -> save is verified on a physical Android device.

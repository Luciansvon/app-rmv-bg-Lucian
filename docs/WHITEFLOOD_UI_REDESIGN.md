# WhiteFlood UI Redesign Handoff

Status: Approved visual baseline for implementation
Date: 2026-08-10

## Design read

This is a redesign of a local Windows desktop utility for furniture and office
catalog images. The UI needs to make the active tool, image stage, heavy
processing state, and output action obvious without turning the workspace into
a dashboard. The direction is a dark workbench with one rose accent and a
wide preview stage.

The generated visual board is the approved visual baseline. It is not runtime
evidence, so the implementation must reproduce its composition while using
real WhiteFlood data and real processing state. Text, controls, dimensions,
and processing claims below are the implementation contract.

## Current state audit

Observed in the active source:

- CustomTkinter/Tkinter is the existing UI framework and must remain.
- The app already has a dark theme, a narrow sidebar, and a large
  Before/After preview.
- Remove Background and Upscale are separate tools with separate pipelines.
- Heavy work already runs in a worker thread and returns to Tkinter through
  `after()` callbacks.
- The sidebar currently combines four future tools with one shared file/action
  section. New workflows need tool-specific controls without hiding the
  current processing state.

Interpretation:

- The useful signature is the large image stage and local-first status model.
- The main visual debt is not the dark theme. It is unclear page ownership:
  the same action area changes meaning when the tool changes.
- The redesign therefore keeps the shell and changes the information
  hierarchy before adding decoration.

## Direction and dials

- Direction: Rose Signal Workbench.
- Theme: dark only for this Windows utility, using related charcoal surfaces.
- Accent: `#ef5b73` only. Green is reserved for a completed save state.
- `DESIGN_VARIANCE`: 4. The work is precise and calm; asymmetric decoration is
  not worth the extra scanning cost.
- `MOTION_INTENSITY`: 3. Use feedback motion only for page changes, loading,
  slider movement, and completed output. Respect reduced-motion settings where
  the platform exposes them.
- `VISUAL_DENSITY`: 6. Controls stay compact, but the preview stage gets the
  largest area and status text never competes with it.
- Radius rule: 8px for panels and buttons, 4px for small fields. No mixed
  floating cards or glass surfaces.
- Type rule: Segoe UI or the existing system sans for native Windows legibility.
  Use weight and spacing for hierarchy instead of decorative display fonts.

## Visual fidelity gate

The generated board is the acceptance reference for the first UI pass. A page
does not pass visual review if it changes the following without a new decision:

- left rail order and active-tool treatment;
- top bar placement of the page title and file actions;
- dominant stage-to-inspector proportion;
- rose accent placement and charcoal surface hierarchy;
- 8px panel/button radius and compact control rhythm;
- per-page control grouping and primary action location;
- persistent bottom status strip.

Real file names, dimensions, output paths, progress values, and error messages
must replace generated sample data. Generated sample furniture imagery is only
for visual composition; the application must keep using the user's local
image/video files.

## Shared page shell

```text
┌──────────────────────┬─────────────────────────────────────────────────────┐
│ WHITEFLOOD           │ Page title                         Open / Export      │
│ Workspace            ├───────────────────────────────────────┬─────────────┤
│ Hapus Background     │                                       │ Tool         │
│ Upscale              │          image / mask stage            │ inspector    │
│ Vectorize Image      │                                       │ controls     │
│ Remove Watermark     │                                       │             │
│                      ├───────────────────────────────────────┴─────────────┤
│ Recent / output      │ phase label                         progress / status│
└──────────────────────┴─────────────────────────────────────────────────────┘
```

The left rail stays fixed while the inspector changes by page. The top bar
contains only the current page name and file actions. The bottom status strip
is persistent so a worker never makes the user guess whether the app is idle.

## Pages

### 1. Workspace

Purpose: give the user a clear starting point without auto-processing a file.

- Main area: five tool choices, arranged as one featured Remove Background
  action plus four equal secondary actions. Each choice names its real output.
- Drop zone: one low-priority file drop area below the choices. It does not
  decide the tool silently; dropping a file still requires an active tool.
- Sidebar: recent file name and local-processing note only.
- Empty state: `Pilih alat untuk mulai` with no fake recent files.
- Loading/error states: not applicable until a tool is selected; show the
  tool's state after navigation.

### 2. Hapus Background

Purpose: preserve the existing fast path for transparent PNG output.

- Inspector: mode, edge refinement, advanced controls, then one primary
  `Pilih Gambar` action.
- Stage: Before/After split preview with labels outside the image when space
  allows. The source image appears immediately after selection.
- Output action: `Simpan Hasil` is disabled until a result exists.
- Loading: stage remains visible, inspector locks, status strip shows the
  current phase and percentage.
- Error: keep the original image visible and show a plain-language next step.

### 3. Upscale

Purpose: make scale and output dimensions obvious before the heavy process.

- Inspector top: 2x, 4x, 8x segmented scale control.
- Inspector middle: input dimensions and expected output dimensions. These
  values are derived from the loaded image, not invented copy.
- Stage: original image first, then result. No background-removal controls are
  visible on this page.
- Primary action: `Proses Upscale`, followed by `Simpan Hasil`.
- Loading: show a determinate bar only when the worker provides a real value;
  otherwise use phase text and a restrained spinner.

### 4. Vectorize Image

Purpose: turn a raster image into an SVG without pretending the SVG is editable
inside WhiteFlood.

- Inspector: preset selector with Logo, Illustration, Line Art, and Detailed.
- Stage: source image plus a result information panel. Do not add a native SVG
  renderer or node editor.
- Primary action: `Convert ke SVG`; output action: `Simpan SVG`.
- Loading: spinner plus `Mengubah gambar ke SVG...`; no fake percentage.
- Success: show SVG file name, valid/non-empty status, and byte size.
- Error: distinguish unsupported input, missing VTracer, invalid SVG, and
  cancelled conversion.
- Batch remains available because each raster file is independent and the
  preset can be applied per file. Output names stay collision-safe.

### 5. Remove Watermark Image

Purpose: let the user paint a static mask at source-pixel precision.

- Inspector: Brush, Rectangle, Eraser, brush size, zoom, Undo, Redo, Clear.
- Stage: original image with a rose mask overlay. The mask is stored in the
  source image dimensions; preview scaling must not change the mask geometry.
- Primary action is disabled while the mask is empty.
- After processing, switch the stage to Before/After while retaining a `Mask`
  view action for review.
- Success: PNG output dimensions and alpha mode are shown in the status strip.
- Error: keep the mask and original image so the user can adjust and retry.

### 6. Remove Watermark Video

Purpose: apply one static mask to every decoded frame without loading the full
  video into memory.

- Inspector: Image/Video mode is replaced by video metadata: resolution, FPS,
  duration, audio presence, and rotation when probe data exists.
- Stage: first valid frame with mask overlay. The preview is explicitly a
  representative frame, not a video player replacement.
- Primary action: `Process Video`; progress uses completed frames when the
  frame count is known, otherwise status text explains the estimate.
- Cancel: visible and safe. It terminates FFmpeg and removes the temporary
  output.
- Success: output path, audio-copy status, and FFprobe validation appear in the
  status strip. Audio fallback is a warning, not a silent success.
- Error: preserve the source frame and mask; never replace the source video.

### Batch boundary

The existing batch section remains in the shell for the light independent
image tools: Hapus Background, Upscale, and Vectorize Image. It is hidden for
Watermark Image and Watermark Video in the first release. A manually painted
mask must not be applied to unrelated images silently, and video processing
has separate audio, cancellation, and temporary-output risks.

## Component contract for CustomTkinter

- `AppShell`: owns the left rail, top bar, stage host, and persistent status.
- `ToolRail`: maps one button to one active tool and owns active/inactive
  visual state.
- `ToolInspector`: a frame per tool; only one is packed at a time.
- `ImageStage`: owns Before/After, empty, loading, error, and result states.
- `MaskCanvas`: owns source-to-preview coordinate mapping and mask history.
- `OutputPanel`: shows the real output type, path, dimensions, and collision
  warning.
- `StatusStrip`: maps worker callbacks to phase, progress, cancellation, and
  next action.

The first implementation can keep these classes in the existing source file
if that lowers integration risk. New feature engines belong in `features/` as
specified by the implementation plan.

## State matrix

| Page | Empty | Ready | Processing | Success | Error |
|---|---|---|---|---|---|
| Workspace | choose a tool | tool cards | not applicable | last action summary | not applicable |
| Remove Background | choose image | original preview | locked controls | transparent PNG details | original retained |
| Upscale | choose image | scale + dimensions | locked controls | scaled PNG details | original retained |
| Vectorize Image | choose raster | preset + source | spinner, no fake % | SVG metadata | source retained |
| Watermark Image | choose image | source + mask tools | mask locked | PNG details | mask retained |
| Watermark Video | choose video | first frame + metadata | frame progress + cancel | MP4 + audio warning | temp cleaned |

## Implementation gates

1. Implement the shared shell and tool navigation without changing the two
   existing image pipelines.
2. Convert the generated direction into the six page-specific inspectors and
   states above.
3. Add Vectorize Image and verify its static contracts.
4. Add Watermark Image and verify source-pixel mask mapping.
5. Add Watermark Video and verify streaming, cancellation, and FFprobe output.
6. Run GUI screenshot review only after explicit approval to launch the app.

## Not yet verified

- The generated board is a visual direction, not a screenshot of the current
  app and not proof of runtime behavior.
- No GUI screenshot has been taken from the current source in this turn.
- CustomTkinter geometry, Windows font fallback, and control wrapping need a
  real source run before the redesign can be called visually complete.
- The page list and layout are proposed from the approved feature plan; they
  are not a user test result.

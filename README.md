# DaVinci Resolve MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io/) server for AI-assisted video editing in DaVinci Resolve Studio. **97 tools** covering timeline assembly, Fusion effects, color grading, rendering, media management, and more.

> Forked from [tooflex/davinci-resolve-mcp](https://github.com/tooflex/davinci-resolve-mcp) (32 tools).
> Expanded by [@danieliser](https://github.com/danieliser) with 65 additional tools, proxy-safe connection handling, Fusion/Lua scripting guides, and type-annotated API layer.

---

## What Can It Do?

With this MCP server connected, an AI assistant can:

- **Build complete timelines** from JSON cut lists with frame-accurate clip placement
- **Add Fusion effects** — glow, color correction, vignettes, animated zooms via Lua
- **Create animated title cards** with TextPlus, BezierSpline keyframes, and generators
- **Color grade** — CDL values, LUT application, grade copying between clips
- **Render** — configure format/codec, queue jobs, monitor progress, export
- **Manage media** — import, organize into folders, search by name, relink, delete
- **Control playback** — play, stop, seek to frame, read playhead position
- **Manage markers and flags** — timeline markers, clip markers, color labels
- **Handle takes** — add alternate takes, switch between them, finalize
- **Export timelines** — AAF, EDL, FCP XML, FCPXML formats

## Requirements

- **DaVinci Resolve Studio** 18.0+ (free version does not expose the scripting API)
- **Python** 3.10+
- **uv** (recommended) or pip

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/danieliser/davinci-resolve-mcp.git
cd davinci-resolve-mcp
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
```

### 2. Configure Your AI Client

**Claude Code** — add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "davinci-resolve": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/davinci-resolve-mcp",
        "server.py"
      ]
    }
  }
}
```

**Claude Desktop** — add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "davinci-resolve": {
      "command": "/path/to/uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/davinci-resolve-mcp",
        "server.py"
      ]
    }
  }
}
```

### 3. Launch

1. Open **DaVinci Resolve Studio**
2. Start (or restart) your AI client
3. The MCP server connects automatically via Resolve's scripting API

---

## All 97 Tools

### Project Management (7)

| Tool | Description |
|------|-------------|
| `create_project` | Create a new project |
| `load_project` | Load an existing project by name |
| `save_project` | Save the current project |
| `export_project` | Export project to .drp file |
| `import_project` | Import project from .drp file |
| `set_project_setting` | Set a project setting (key/value) |
| `open_page` | Navigate to a page (media, edit, fusion, color, fairlight, deliver) |

### Timeline Operations (14)

| Tool | Description |
|------|-------------|
| `create_timeline` | Create a new empty timeline |
| `delete_timeline` | Delete a timeline by index |
| `set_current_timeline` | Switch active timeline by index |
| `duplicate_timeline` | Duplicate current timeline |
| `create_timeline_from_clips` | Create timeline from named clips |
| `import_timeline_from_file` | Import timeline from XML/EDL/AAF |
| `export_current_timeline` | Export timeline to AAF/EDL/FCP XML/FCPXML |
| `get_timeline_setting` | Read a timeline setting |
| `set_timeline_setting` | Write a timeline setting |
| `get_track_count` | Count tracks by type (video/audio) |
| `add_track` | Add a video or audio track |
| `set_track_name` | Rename a track |
| `enable_track` | Enable/disable a track |
| `build_timeline_from_json` | **Build complete timeline from JSON cut list** — handles clip_in/out, recordFrame placement, media pool search |

### Clip & Item Operations (10)

| Tool | Description |
|------|-------------|
| `append_to_timeline` | Append clips by name to current timeline |
| `append_clip_to_track` | Place a clip on a specific track at a specific frame |
| `get_timeline_items` | List items on a track with start/end frames |
| `get_timeline_item_info` | Detailed info for a timeline item (offsets, duration) |
| `delete_timeline_item` | Remove item by index with optional ripple |
| `trim_timeline_item` | Adjust source trim offsets (left/right) |
| `set_clip_property` | Set any property on a timeline clip |
| `get_current_video_item` | Get the item under the playhead |
| `create_compound_clip` | Combine items into a compound clip |
| `insert_fusion_composition` | Insert a Fusion comp at the playhead |

### Media Pool (10)

| Tool | Description |
|------|-------------|
| `import_media` | Import files into current media pool folder |
| `list_media_pool` | List folder tree with clip names and types |
| `add_sub_folder` | Create a subfolder |
| `move_clips_to_folder` | Move clips between folders by name |
| `get_media_clip_metadata` | Read clip metadata (all or specific key) |
| `set_media_clip_metadata` | Write clip metadata (key/value pairs) |
| `export_metadata` | Export clip metadata to CSV |
| `relink_clips` | Relink clips to a new folder path |
| `delete_media_clips` | Remove clips from media pool |
| `delete_media_folders` | Remove folders from media pool |

### Fusion / Compositing (12)

| Tool | Description |
|------|-------------|
| `execute_lua` | **Run arbitrary Lua in Fusion** — the escape hatch for anything not covered by dedicated tools |
| `create_fusion_node` | Add a tool to the current Fusion comp |
| `add_fusion_comp` | Add a new comp to a timeline item |
| `import_fusion_comp` | Import .comp/.setting file into an item |
| `export_fusion_comp` | Export a comp to file |
| `get_fusion_comp_names` | List comp names on an item |
| `create_fusion_clip` | Create a Fusion clip from timeline items |
| `insert_title` | Insert Text+ title at playhead |
| `insert_fusion_title` | Insert Fusion-based title |
| `insert_generator` | Insert generator (Solid Color, etc.) |
| `insert_fusion_generator` | Insert Fusion generator |
| `refresh` | Refresh all internal Resolve object references |
| `hot_reload` | **Hot-reload resolve_api.py** without restarting the MCP server — preserves live IPC connection |

### Color Grading (8)

| Tool | Description |
|------|-------------|
| `add_color_node` | Add a node to current clip's grade |
| `set_lut` | Apply LUT to a specific node |
| `set_cdl` | Apply CDL values (slope/offset/power/saturation) |
| `copy_grades` | Copy grade from one clip to others |
| `apply_grade_from_drx` | Apply .drx grade file |
| `refresh_lut_list` | Refresh available LUTs |
| `set_clip_color` | Set clip color label |
| `set_current_version` | Switch grade version |

### Markers & Flags (6)

| Tool | Description |
|------|-------------|
| `add_timeline_marker` | Add marker to timeline at frame |
| `get_timeline_markers` | Get all timeline markers |
| `delete_timeline_markers_by_color` | Delete markers by color |
| `add_clip_marker` | Add marker to media pool clip |
| `get_clip_markers` | Get markers on a clip |
| `add_flag` / `get_flag_list` | Add/read flags on timeline items |

### Takes (4)

| Tool | Description |
|------|-------------|
| `add_take` | Add alternate take from media pool |
| `get_takes_count` | Count takes on an item |
| `select_take` | Switch active take by index |
| `finalize_take` | Make selected take permanent |

### Stills & Gallery (4)

| Tool | Description |
|------|-------------|
| `grab_still` | Capture still from current frame |
| `grab_all_stills` | Capture stills from all clips (first/middle frame) |
| `save_still` | Save current grade as still to album |
| `apply_still` | Apply a saved still/grade to a clip |

### Audio (2)

| Tool | Description |
|------|-------------|
| `set_audio_volume` | Set volume on a timeline clip |
| `set_track_volume` | Set volume on an audio track |

### Playback (3)

| Tool | Description |
|------|-------------|
| `play_timeline` | Start playback |
| `stop_timeline` | Stop playback |
| `set_playhead_position` | Seek to a specific frame |

### Rendering (10)

| Tool | Description |
|------|-------------|
| `start_project_render` | Quick render with optional preset |
| `set_render_settings` | Configure TargetDir, CustomName, resolution, etc. |
| `set_render_format_and_codec` | Set format (mp4, mov, etc.) and codec (H264, etc.) |
| `get_render_formats` | List all supported formats |
| `get_render_codecs` | List codecs for a format |
| `add_render_job` | Add job to queue |
| `delete_render_job` / `delete_all_render_jobs` | Remove jobs |
| `get_render_job_list` | List all jobs with details |
| `get_render_job_status` | Poll job status |
| `start_rendering` / `stop_rendering` / `is_rendering` | Control render execution |

---

## Fusion & Lua Scripting Guide

The `execute_lua` tool is the most powerful capability in this MCP server. It runs arbitrary Lua inside Resolve's Fusion environment, giving access to anything the Fusion scripting API supports.

### Why Lua Instead of Python?

DaVinci Resolve's Python API has significant limitations for Fusion work:

- **BezierSpline** (keyframe animations) returns `NoneType` from Python — only works in Lua
- **Tool connections** are more reliable through Lua's `comp:AddTool()` + direct property assignment
- **Fusion page state** is accessible through Lua but not fully through Python

### Basic Pattern

```python
# From your AI assistant, call execute_lua with a Lua script string:
execute_lua(script="""
local comp = fusion:GetCurrentComp()
local mi = comp:FindTool("MediaIn1")
local mo = comp:FindTool("MediaOut1")

local sg = comp:AddTool("SoftGlow", 0, 0)
sg.Input = mi.Output
sg.Blend = 0.15
sg.Threshold = 0.7

mo.Input = sg.Output
""")
```

### Animated Properties with BezierSpline

```lua
-- Animated zoom over the clip's duration
local xf = comp:AddTool("Transform", -1, 0)
xf.Input = mi.Output
xf.Size = comp:BezierSpline({
    [comp.RenderStart] = { Value = 1.0 },
    [comp.RenderEnd]   = { Value = 1.06 }
})
```

### TextPlus with Multiline Text

```lua
-- Use Lua's native \n for newlines — NOT Python string escaping
local t = comp:AddTool("TextPlus", 0, 0)
t.StyledText = [["Click Like Thunder"\nby Sarai]]
t.Font = "Futura"
t.Style = "Bold"
t.Size = 0.072
t.Center = { 0.5, 0.54 }
```

**Critical:** When building Lua strings from Python, `\n` gets corrupted into a literal backslash-n. Use Lua long string syntax `[[ ]]` for any text containing special characters.

### Debugging Lua Scripts

`comp.Execute()` does not return Lua values. To get data out:

```lua
-- Write diagnostics to a temp file
local f = io.open("/tmp/fusion_debug.txt", "w")
f:write("Tool count: " .. tostring(#comp:GetToolList()) .. "\n")
for i, tool in ipairs(comp:GetToolList()) do
    f:write(tool:GetAttrs().TOOLS_Name .. "\n")
end
f:close()
```

Then read `/tmp/fusion_debug.txt` from your AI client.

### Comp Targeting

Always use `fusion.CurrentComp` to get the active composition:

```python
# CORRECT — matches what you see in the Fusion page UI
comp = fusion.CurrentComp

# WRONG — returns comps by creation order, often targets the wrong one
comp = item.GetFusionCompByIndex(1)
```

---

## API Architecture

### Type-Safe Proxy Handling

Resolve's scripting API returns opaque C-extension proxy objects. This fork adds type aliases documenting intent:

```python
ResolveApp = Any      # dvr_script.scriptapp("Resolve")
Timeline = Any        # project.GetCurrentTimeline()
TimelineItem = Any    # timeline.GetItemListInTrack(...)[n]
FusionComp = Any      # fusion.CurrentComp
MediaPoolItem = Any   # folder.GetClips()[n]
# ... 15 total aliases
```

### Auto-Refresh Connection Handling

Resolve's C-extension proxies go stale when the user switches projects, timelines, or pages. This fork adds three defensive helpers that detect stale proxies and re-establish the connection:

```python
def _ensure_project(self) -> bool:
    """Test proxy with GetName(), refresh() if stale."""

def _ensure_media_pool(self) -> bool:
    """Test proxy with GetRootFolder(), refresh() if stale."""

def _ensure_timeline(self) -> Optional[Timeline]:
    """Test proxy with GetName(), refresh() and retry if stale."""
```

Every API method that touches project/timeline/media pool objects calls the appropriate `_ensure_*` method first. This eliminates the most common failure mode: "method returned None" because the proxy expired.

### Hot Reload

The `hot_reload` tool reloads `resolve_api.py` from disk without restarting the MCP server process:

```
hot_reload()
→ "Hot-reloaded resolve_api.py. Connection preserved: True."
```

**How it works:** The C-extension IPC socket handle is preserved across the reload. `importlib.reload()` picks up code changes, a new `ResolveAPI` instance is created with `__new__()` (bypassing `__init__`), the old socket handle is injected, and `refresh()` repopulates all proxy references.

Without this preservation, reloading would destroy the IPC connection (the C-extension socket doesn't survive Python object recreation).

---

## Proven Workflow: Timeline from JSON

The most reliable way to build a complete edit is `build_timeline_from_json`. This was battle-tested across 3+ failed runs before arriving at the correct workflow order:

### Workflow Order (Critical)

```
1. Create project + import media into organized folders
2. build_timeline_from_json(insert_fusion_comp=true)
   — creates timeline, inserts Fusion comp for placeholders, places all clips
3. Set playhead on Fusion comp → open_page("fusion") → execute_lua(title card) → open_page("edit")
4. Purge clip audio from A1 (delete from highest index to lowest)
5. Place master WAV on A1 (now empty), label track
6. Add markers
7. Render
```

**Why this order matters:**
- `build_timeline_from_json` creates its OWN timeline (from JSON `name` field) — do NOT create a timeline manually first
- `insert_fusion_comp=true` inserts the Fusion comp FIRST before placing clips, preventing ripple corruption
- Fusion comp Lua works even with other clips present — just put the playhead on the comp before switching to Fusion page
- Audio purge (step 4) is safe — deleting A1 audio items does NOT affect V1 video clips

### Sequence JSON Format

```json
{
  "name": "Timeline Name",
  "clips": [
    {
      "shot_id": "INTRO",
      "file": null,
      "timeline_start": 0,
      "timeline_end": 7,
      "clip_in": 0,
      "clip_out": 7,
      "notes": "Placeholder — file=null triggers Fusion comp insert"
    },
    {
      "shot_id": "S003",
      "file": "relative/path/to/clip.mp4",
      "timeline_start": 7,
      "timeline_end": 13.381,
      "clip_in": 0,
      "clip_out": 6.381,
      "notes": "Optional description"
    }
  ]
}
```

**Key fields:**
- `file: null` — inserts a Fusion composition placeholder (when `insert_fusion_comp=true`)
- `clip_in` / `clip_out` — source trim points in seconds. Duration is `clip_out - clip_in`, NOT `timeline_end - timeline_start`
- `timeline_start` / `timeline_end` — timeline position in seconds (converted to frames via `86400 + round(seconds × fps)`)
- File paths are resolved relative to the JSON file location via media pool search by clip name

### Audio Track Setup

Video clips bring their own audio on A1. For a clean stereo master mix:

```
1. get_timeline_items("audio", 1)  — count items
2. Delete all A1 items in REVERSE order (highest index first to avoid index shifting)
3. append_clip_to_track("master.wav", track_index=1, start_frame=86400)
4. set_track_name("audio", 1, "Master Mix")
```

A1 is already stereo (inherited from the video clips), so just purge and reuse it. No need to create a separate A2 track.

---

## Known Gotchas

### 1. Insert Functions Always Ripple V1

`InsertFusionCompositionIntoTimeline`, `InsertTitleIntoTimeline`, and `InsertGeneratorIntoTimeline` all insert at the playhead on V1 and ripple ALL downstream clips. No track targeting parameter exists.

**Workaround:** Use `build_timeline_from_json(insert_fusion_comp=true)` which inserts the Fusion comp FIRST on an empty timeline before placing clips. If you must insert manually, do it before adding any clips.

### 2. Fusion Comp Duration Is Locked

`InsertFusionCompositionIntoTimeline` creates exactly 120 frames (5s at 24fps). The duration cannot be changed via the scripting API.

### 3. Fusion Comp Targeting on Populated Timelines

`GetFusionCompByIndex()`, `GetFusionCompByName()`, and `LoadFusionCompByName()` often return the wrong comp (usually shows as "Templates/" in name).

**Working approach:** Set the playhead on the Fusion comp in the Edit page, then `open_page("fusion")`. The comp auto-opens as `fusion:GetCurrentComp()` — this reliably returns the correct comp even with other clips on the timeline.

### 4. `append_clip_to_track` Does NOT Honor `start_frame` Precisely

Despite accepting a `start_frame` parameter, clips get butted together end-to-end rather than placed at the specified frame. **Use `build_timeline_from_json` instead** for frame-accurate placement.

### 5. Loader Tool + PNG Alpha Is Broken

The Fusion Loader tool's `PostMultiplyByAlpha` fills transparent areas with the image's edge color. `GlobalIn`/`GlobalOut` default to frame 0, causing frame range mismatches. **Workaround:** use TextPlus for text-based overlays, or pre-composite images into full-resolution video clips outside Fusion.

### 6. AppendToTimeline + trackIndex Forces Mono

When placing audio with an explicit `trackIndex`, stereo WAV files are forced to mono. **Workaround:** Use `add_track("audio")` to create a dedicated audio track, then `append_clip_to_track()` on that track. The MCP server's `add_track` passes `sub_track_type` to `timeline.AddTrack()` for stereo support.

### 7. GetClips() Returns a Dict in Newer Resolve

`folder.GetClips()` returns `{int: clip}` dict, not a list. This fork handles both formats throughout.

### 8. Timeline Frame Offset

Resolve timelines start at frame 86400 (1-hour offset at 24fps). Convert seconds to frames:

```
frame = 86400 + round(seconds × fps)
```

### 9. Clip Names Include File Extensions

`_find_media_pool_clip()` matches on `GetClipProperty("Clip Name")` which includes the file extension. Pass `"S003.v1.mp4"` not `"S003.v1"`.

### 10. `build_timeline_from_json` Requires UTF-8 Encoding

If your JSON notes fields contain em dashes or other Unicode characters, `open()` needs `encoding='utf-8'`. This fork includes the fix.

### 11. `build_timeline_from_json` Duration Calculation

Duration is `clip_out - clip_in` (source trim range), NOT `timeline_end - timeline_start`. If these don't match, the clip will be the wrong length. Ensure your JSON `clip_out` values are exact.

### 12. `save_project()` Fails During Render

`save_project()` returns failure while rendering is active. **Always save AFTER render completes.** Fallback: `execute_lua("resolve:GetProjectManager():SaveProject()")`.

### 13. Empty Fusion Comp Causes Render Failure

If the title card Lua fails silently, the Fusion comp renders as black and may cause the render job to fail entirely. Verify the comp has content before rendering (use Lua to check tool count via file-based debugging).

### 14. Media Pool Root Folder Is "Master"

Create subfolders under `"Master"`, not under a non-existent root. `add_sub_folder("Master", "Clips")` is correct.

---

## Troubleshooting

### "Not connected to DaVinci Resolve"

1. Ensure **DaVinci Resolve Studio** is running (not the free version)
2. The scripting API must be enabled in Resolve preferences
3. Restart the MCP server — the connection is established on startup

### MCP Server Won't Start

```bash
# Check Python version (needs 3.10+)
python --version

# Check dependencies
uv pip install mcp pydantic

# Check Resolve scripting module is findable
python -c "import DaVinciResolveScript"
```

### API Module Not Found

The Resolve scripting module location varies by OS:

| OS | Path |
|----|------|
| macOS | `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules` |
| Windows | `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules` |
| Linux | `/opt/resolve/Developer/Scripting/Modules` |

The `ResolveAPI` class searches these paths automatically. If your installation is non-standard, set:

```bash
export RESOLVE_SCRIPT_PATH="/custom/path/to/Scripting/Modules"
```

### Stale Proxy Errors

If tools return unexpected `None` results after switching projects or timelines in Resolve, call `refresh()` to re-establish all proxy references. The `_ensure_project()`, `_ensure_media_pool()`, and `_ensure_timeline()` helpers handle this automatically for most operations, but manual `refresh()` may still be needed after switching projects in the Resolve UI.

### Playhead Positioning Returns None

`GetTimecodeFromFrame()` doesn't exist on some timeline proxies (returns `None`, not `AttributeError`). The `set_playhead_position()` implementation falls back to manual timecode math (`HH:MM:SS:FF` from `frame ÷ fps`). Always guard Resolve proxy method calls with `getattr()` + `callable()` checks.

### Hot Reload Breaks IPC Connection

`importlib.reload()` + new `ResolveAPI()` invalidates the DaVinciResolveScript C-extension socket handle. The current `hot_reload` implementation preserves the existing `self.resolve` handle by saving it before reload and injecting it into the new instance. If hot reload fails, restart the MCP server.

### Lua Script Fails Silently

`comp.Execute()` does not return Lua values or error messages. Use file-based debugging:

```lua
local f = io.open("/tmp/fusion_debug.txt", "w")
f:write("Tool count: " .. tostring(#comp:GetToolList()) .. "\n")
f:close()
```

Then read `/tmp/fusion_debug.txt` from your AI client to verify the script executed correctly.

---

## Attribution

- **Original project:** [tooflex/davinci-resolve-mcp](https://github.com/tooflex/davinci-resolve-mcp) — 32 MCP tools covering core project/timeline/media/Fusion operations
- **This fork:** [@danieliser](https://github.com/danieliser) — expanded to 97 tools with proxy-safe connection handling, hot reload, timeline-from-JSON builder, comprehensive render pipeline, Fusion comp management, color grading tools, marker/flag/take management, media pool operations, and Lua scripting documentation

## License

[MIT License](LICENSE)

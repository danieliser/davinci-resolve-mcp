"""
DaVinci Resolve MCP Server

This module implements a Model Context Protocol (MCP) server for DaVinci Resolve,
allowing AI assistants to interact with DaVinci Resolve through the MCP protocol.
"""

import importlib
import json
import logging
import math
import sys
from typing import List, Dict, Any, Optional, Union

# Configure logging with timestamp, name, level, and message format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("resolve_mcp")  # Logger instance for this module

# Add MCP library to path if not installed as a package
try:
    from mcp.server.fastmcp import FastMCP  # Import FastMCP for MCP server functionality
    print("Successfully imported FastMCP", file=sys.stderr)
except ImportError as e:
    print(f"Error importing FastMCP: {e}", file=sys.stderr)
    raise  # Raise exception if MCP library is unavailable

# Import ResolveAPI (assumes resolve_api.py is in the same directory or installed)
try:
    import resolve_api as resolve_api_module  # Import module for hot-reload support
    from resolve_api import ResolveAPI  # Import class for initialization
    print("Successfully imported ResolveAPI", file=sys.stderr)
except ImportError as e:
    print(f"Error importing ResolveAPI: {e}", file=sys.stderr)
    raise  # Raise exception if ResolveAPI is unavailable

# Create the MCP server instance with the name "DaVinci Resolve"
mcp = FastMCP("DaVinci Resolve")

# Initialize the Resolve API to connect to DaVinci Resolve
resolve_api = ResolveAPI()

# Check connection to Resolve and log the result
if not resolve_api.is_connected():
    logger.error("Failed to connect to DaVinci Resolve. Ensure it is running.")
else:
    logger.info("Successfully connected to DaVinci Resolve.")

# --- Resource Definitions ---

@mcp.resource("system://status")
def get_system_status() -> str:
    """Get the current status of the DaVinci Resolve connection."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    project_name = resolve_api.get_project_name() or "No project open"
    timeline = resolve_api.get_current_timeline()
    timeline_name = timeline.GetName() if timeline else "No timeline open"
    return f"Connected: Yes\nProject: {project_name}\nTimeline: {timeline_name}"

@mcp.resource("project://current")
def get_current_project() -> str:
    """Get information about the current project."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    project = resolve_api.get_current_project()
    if not project:
        return "No project open."
    return f"Name: {project.GetName()}\nTimelines: {project.GetTimelineCount()}"

@mcp.resource("timeline://current")
def get_current_timeline() -> str:
    """Get information about the current timeline."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    timeline = resolve_api.get_current_timeline()
    if not timeline:
        return "No timeline open."
    return (f"Name: {timeline.GetName()}\n"
            f"Duration: {timeline.GetEndFrame() - timeline.GetStartFrame() + 1} frames\n"
            f"Video Tracks: {timeline.GetTrackCount('video')}")

@mcp.resource("mediapool://current")
def get_current_media_pool_folder() -> str:
    """Get information about the current media pool folder."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    media_pool = resolve_api.get_media_pool()
    if not media_pool:
        return "No media pool available."
    folder = media_pool.GetCurrentFolder()
    if not folder:
        return "No current folder."
    clips = folder.GetClips()
    clip_count = len(clips) if clips else 0
    return f"Folder: {folder.GetName()}\nClips: {clip_count}"

@mcp.resource("gallery://albums")
def get_gallery_albums() -> str:
    """Get a list of albums in the gallery."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    albums = resolve_api.get_gallery_albums()
    return "\n".join([album.GetName() for album in albums]) if albums else "No albums"

@mcp.resource("timeline://items")
def get_timeline_items_resource() -> str:
    """Get a list of items in the first video track of the current timeline."""
    items = resolve_api.get_timeline_items("video", 1)
    return "\n".join([f"Clip {i+1}: {item.GetName()}" for i, item in enumerate(items)]) if items else "No items"

# --- Tool Definitions ---

@mcp.tool()
def refresh() -> str:
    """Refresh all internal Resolve objects to reflect the current state."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    resolve_api.refresh()
    return "Resolve API state refreshed."

@mcp.tool()
def hot_reload() -> str:
    """Hot-reload resolve_api.py without restarting the MCP server. Use after editing resolve_api.py."""
    global resolve_api, resolve_api_module
    try:
        # Save the live IPC handle before reload — C-extension sockets don't survive reload
        old_resolve = resolve_api.resolve if resolve_api else None
        # Reload the module from disk
        resolve_api_module = importlib.reload(resolve_api_module)
        # Create new instance but inject the preserved IPC handle
        new_api = resolve_api_module.ResolveAPI.__new__(resolve_api_module.ResolveAPI)
        new_api.resolve = old_resolve
        new_api.fusion = None
        new_api.project_manager = None
        new_api.current_project = None
        new_api.media_storage = None
        new_api.media_pool = None
        # Let refresh() populate everything from the preserved handle
        new_api.refresh()
        resolve_api = new_api
        connected = resolve_api.is_connected()
        return f"Hot-reloaded resolve_api.py. Connection preserved: {connected}."
    except Exception as e:
        return f"Hot-reload failed: {e}"

@mcp.tool()
def create_project(name: str) -> str:
    """Create a new project in DaVinci Resolve."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.create_project(name)
    return f"Project '{name}' created." if success else f"Failed to create '{name}'."

@mcp.tool()
def load_project(name: str) -> str:
    """Load an existing project in DaVinci Resolve."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.load_project(name)
    return f"Project '{name}' loaded." if success else f"Failed to load '{name}'."

@mcp.tool()
def save_project() -> str:
    """Save the current project."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.save_project()
    return "Project saved." if success else "Failed to save project."

@mcp.tool()
def export_project(project_name: str, file_path: str) -> str:
    """Export a project to a file."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.export_project(project_name, file_path)
    return f"Project '{project_name}' exported to '{file_path}'." if success else "Failed to export project."

@mcp.tool()
def import_project(file_path: str) -> str:
    """Import a project from a file."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.import_project(file_path)
    return f"Project imported from '{file_path}'." if success else "Failed to import project."

@mcp.tool()
def open_page(page_name: str) -> str:
    """Open a specific page in DaVinci Resolve."""
    valid_pages = ["media", "edit", "fusion", "color", "fairlight", "deliver"]
    if page_name.lower() not in valid_pages:
        return f"Invalid page. Use: {', '.join(valid_pages)}"
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.open_page(page_name.lower())
    return f"Opened '{page_name}' page." if success else f"Failed to open '{page_name}'."

@mcp.tool()
def create_timeline(name: str) -> str:
    """Create a new timeline in the current project."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.create_timeline(name)
    return f"Timeline '{name}' created." if success else f"Failed to create '{name}'."

@mcp.tool()
def delete_timeline(timeline_index: int) -> str:
    """Delete a timeline by its 1-based index."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    timeline = resolve_api.get_timeline_by_index(timeline_index)
    if not timeline:
        return f"No timeline found at index {timeline_index}."
    name = timeline.GetName()
    success = resolve_api.delete_timeline(timeline)
    return f"Timeline '{name}' deleted." if success else f"Failed to delete '{name}'."

@mcp.tool()
def set_current_timeline(timeline_index: int) -> str:
    """Set the specified timeline as the current one by 1-based index."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    timeline = resolve_api.get_timeline_by_index(timeline_index)
    if not timeline:
        return f"No timeline found at index {timeline_index}."
    success = resolve_api.set_current_timeline(timeline)
    return f"Timeline at index {timeline_index} set as current." if success else "Failed to set timeline."

@mcp.tool()
def import_media(file_paths: List[str]) -> str:
    """Import media files into the current media pool folder."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    clips = resolve_api.add_items_to_media_pool(file_paths)
    return f"Imported {len(clips)} files." if clips else "Failed to import files."

@mcp.tool()
def list_media_pool(folder_name: Optional[str] = None) -> str:
    """List clips in a media pool folder (root if none specified). Shows folder tree and clip names."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    media_pool = resolve_api.get_media_pool()
    if not media_pool:
        return "No media pool available."
    root = media_pool.GetRootFolder()
    if not root:
        return "No root folder."

    if folder_name:
        folder = resolve_api.find_folder_by_name(folder_name)
        if not folder:
            return f"Folder '{folder_name}' not found."
        return _list_folder(folder, indent=0)
    else:
        return _list_folder(root, indent=0)

def _list_folder(folder: Any, indent: int = 0) -> str:
    """Recursively list a media pool folder's contents."""
    prefix = "  " * indent
    lines = [f"{prefix}📁 {folder.GetName()}/"]
    clips = folder.GetClips()
    clip_list = clips.values() if isinstance(clips, dict) else (clips or [])
    for c in clip_list:
        name = c.GetClipProperty("Clip Name")
        clip_type = c.GetClipProperty("Type") or ""
        lines.append(f"{prefix}  {name} ({clip_type})")
    subs = folder.GetSubFolders()
    sub_list = subs.values() if isinstance(subs, dict) else (subs or [])
    for sub in sub_list:
        lines.append(_list_folder(sub, indent + 1))
    return "\n".join(lines)

@mcp.tool()
def move_clips_to_folder(clip_names: List[str], target_folder_name: str, source_folder_name: Optional[str] = None) -> str:
    """Move media pool clips by name to a target folder."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    # Find target folder
    target = resolve_api.find_folder_by_name(target_folder_name)
    if not target:
        return f"Target folder '{target_folder_name}' not found."
    # Find source folder (optional - defaults to searching everywhere)
    source = None
    if source_folder_name:
        source = resolve_api.find_folder_by_name(source_folder_name)
        if not source:
            return f"Source folder '{source_folder_name}' not found."
    # Use recursive search from resolve_api
    name_map = resolve_api.find_clips_by_name(clip_names, source)
    matched = [name_map[n] for n in clip_names if n in name_map]
    if not matched:
        all_names = resolve_api.list_all_clip_names()
        return f"No matching clips found. Requested: {clip_names[:5]}. All clips in pool ({len(all_names)}): {all_names[:20]}"
    success = resolve_api.move_clips_to_folder(matched, target)
    return f"Moved {len(matched)} clips to '{target_folder_name}'." if success else "Failed to move clips."

@mcp.tool()
def add_sub_folder(parent_folder_name: str, folder_name: str) -> str:
    """Add a subfolder to the specified parent folder in the media pool."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    media_pool = resolve_api.get_media_pool()
    if not media_pool:
        return "No media pool available."
    root_folder = media_pool.GetRootFolder()
    # Check if parent is the root folder itself, then search subfolders
    if root_folder and root_folder.GetName() == parent_folder_name:
        parent_folder = root_folder
    else:
        subs = root_folder.GetSubFolders() if root_folder else {}
        parent_folder = next((f for f in (subs.values() if isinstance(subs, dict) else subs) if f.GetName() == parent_folder_name), None)
    if not parent_folder:
        return f"Parent folder '{parent_folder_name}' not found."
    sub_folder = resolve_api.add_sub_folder(parent_folder, folder_name)
    return f"Subfolder '{folder_name}' added to '{parent_folder_name}'." if sub_folder else "Failed to add subfolder."

@mcp.tool()
def append_to_timeline(clip_names: List[str]) -> str:
    """Append clips to the current timeline by name."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    media_pool = resolve_api.get_media_pool()
    if not media_pool:
        return "No media pool available."
    folder = media_pool.GetCurrentFolder()
    all_clips = folder.GetClips()
    # GetClips() returns dict {int: clip} in newer Resolve versions
    clip_list = all_clips.values() if isinstance(all_clips, dict) else (all_clips or [])
    clips = [c for c in clip_list if c.GetClipProperty("Clip Name") in clip_names]
    success = resolve_api.append_to_timeline(clips)
    return f"Appended {len(clips)} clips to timeline." if success else "Failed to append clips."

@mcp.tool()
def get_timeline_items(track_type: str, track_index: int) -> str:
    """Get items from a specific track in the current timeline. Returns clip names, start/end frames."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items:
        return f"No items on {track_type} track {track_index}."
    lines = []
    for i, item in enumerate(items):
        try:
            name = item.GetName()
            start = item.GetStart()
            end = item.GetEnd()
            duration = item.GetDuration()
            lines.append(f"  [{i}] {name} | start={start} end={end} duration={duration}")
        except Exception as e:
            lines.append(f"  [{i}] <error reading item: {e}>")
    return f"{track_type} track {track_index}: {len(items)} items\n" + "\n".join(lines)

@mcp.tool()
def delete_timeline_item(track_type: str, track_index: int, item_index: int, ripple: bool = False) -> str:
    """Delete a specific item from a timeline track by its index (from get_timeline_items)."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range (track has {len(items) if items else 0} items)."
    target = items[item_index]
    name = target.GetName()
    success = resolve_api.delete_timeline_items([target], ripple)
    return f"Deleted '{name}' from {track_type} track {track_index}." if success else f"Failed to delete '{name}'."

@mcp.tool()
def get_timeline_item_info(track_type: str, track_index: int, item_index: int) -> str:
    """Get detailed info (offsets, start/end, duration) for a timeline item."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    item = items[item_index]
    info = resolve_api.get_timeline_item_offsets(item)
    name = item.GetName()
    return f"{name}: {info}"

@mcp.tool()
def trim_timeline_item(track_type: str, track_index: int, item_index: int, right_offset: Optional[int] = None, left_offset: Optional[int] = None) -> str:
    """Adjust source trim offsets on a timeline item. Lower right_offset extends the clip end. Higher left_offset trims the start."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    item = items[item_index]
    name = item.GetName()
    results = []
    if right_offset is not None:
        result = resolve_api.set_timeline_item_right_offset(item, right_offset)
        results.append(f"right_offset→{right_offset}: result={result}")
    if left_offset is not None:
        result = resolve_api.set_timeline_item_left_offset(item, left_offset)
        results.append(f"left_offset→{left_offset}: result={result}")
    # Get updated info
    info = resolve_api.get_timeline_item_offsets(item)
    return f"{name}: {', '.join(results)}. Now: {info}"

def _find_media_pool_clip(clip_name: str) -> Optional[Any]:
    """Search all media pool folders for a clip by name."""
    media_pool = resolve_api.get_media_pool()
    if not media_pool:
        return None
    root = media_pool.GetRootFolder()
    def search(folder: Any) -> Optional[Any]:
        clips = folder.GetClips()
        clip_list = clips.values() if isinstance(clips, dict) else (clips or [])
        for c in clip_list:
            if c.GetClipProperty("Clip Name") == clip_name:
                return c
        subs = folder.GetSubFolders()
        sub_list = subs.values() if isinstance(subs, dict) else (subs or [])
        for sub in sub_list:
            found = search(sub)
            if found:
                return found
        return None
    return search(root)

@mcp.tool()
def append_clip_to_track(clip_name: str, track_index: int, start_frame: Optional[int] = None) -> str:
    """Append a media pool clip to a specific track index in the current timeline."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    clip = _find_media_pool_clip(clip_name)
    if not clip:
        return f"Clip '{clip_name}' not found in media pool."
    # Detect media type from clip properties
    clip_type = clip.GetClipProperty("Type") or ""
    if "Video" in clip_type:
        media_type = 1  # video only
    elif "Audio" in clip_type:
        media_type = 2  # audio only
    else:
        media_type = 1  # default to video
    info = {"mediaPoolItem": clip, "trackIndex": track_index, "mediaType": media_type}
    if start_frame is not None:
        info["recordFrame"] = start_frame
    success = resolve_api.append_to_timeline_with_info([info])
    return f"Appended '{clip_name}' to track {track_index}." if success else f"Failed to append '{clip_name}' to track {track_index}."

@mcp.tool()
def build_timeline_from_json(json_path: str, fps: float = 24.0, timeline_start_frame: int = 86400, insert_fusion_comp: bool = False) -> str:
    """Build a timeline from a JSON sequence file. Creates timeline, inserts clips with trim points. If insert_fusion_comp=True, inserts a Fusion composition for placeholder clips (file=null) before placing other clips."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    import os
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            spec = json.load(f)
    except Exception as e:
        return f"Failed to read JSON: {e}"

    name = spec.get("name", "Untitled")
    clips_spec = spec.get("clips", [])
    base_dir = os.path.dirname(os.path.dirname(json_path))  # project root from sequences/

    # Delete existing timeline with same name if it exists
    count = resolve_api.get_timeline_count()
    for i in range(1, count + 1):
        tl = resolve_api.get_timeline_by_index(i)
        if tl and tl.GetName() == name:
            resolve_api.delete_timeline(tl)
            break

    # Create fresh timeline
    if not resolve_api.create_timeline(name):
        return f"Failed to create timeline '{name}'."

    # Set it as current
    count = resolve_api.get_timeline_count()
    for i in range(1, count + 1):
        tl = resolve_api.get_timeline_by_index(i)
        if tl and tl.GetName() == name:
            resolve_api.set_current_timeline(tl)
            break

    results = []
    skipped = []

    # Insert Fusion compositions for placeholder clips FIRST (before any media clips)
    # This avoids ripple issues since the timeline is empty at this point
    if insert_fusion_comp:
        for clip_spec in clips_spec:
            if clip_spec.get("file") is None:
                shot_id = clip_spec.get("shot_id", "?")
                tl_start = clip_spec.get("timeline_start", 0)
                frame = timeline_start_frame + round(tl_start * fps)
                resolve_api.set_playhead_position(frame)
                if resolve_api.insert_fusion_composition():
                    results.append(f"  {shot_id}: Fusion comp @ {tl_start}s (placeholder)")
                else:
                    skipped.append(f"{shot_id} (Fusion comp insert failed)")

    for clip_spec in clips_spec:
        shot_id = clip_spec.get("shot_id", "?")
        file_rel = clip_spec.get("file")
        tl_start = clip_spec.get("timeline_start", 0)
        clip_in = clip_spec.get("clip_in", 0)
        clip_out = clip_spec.get("clip_out")

        if not file_rel:
            if not insert_fusion_comp:
                skipped.append(f"{shot_id} (no file -- placeholder)")
            continue

        # Find clip in media pool by filename
        filename = os.path.basename(file_rel)
        mp_clip = _find_media_pool_clip(filename)
        if not mp_clip:
            # Try without extension
            name_no_ext = os.path.splitext(filename)[0]
            mp_clip = _find_media_pool_clip(name_no_ext)
        if not mp_clip:
            skipped.append(f"{shot_id} ({filename} not in media pool)")
            continue

        # Calculate frames
        record_frame = timeline_start_frame + round(tl_start * fps)
        source_start = round(clip_in * fps)
        info = {
            "mediaPoolItem": mp_clip,
            "trackIndex": 1,
            "recordFrame": record_frame,
            "startFrame": source_start,
        }
        if clip_out is not None:
            source_end = round(clip_out * fps)
            info["endFrame"] = source_end

        success = resolve_api.append_to_timeline_with_info([info])
        if success:
            duration_s = round((clip_out or 0) - clip_in, 2)
            results.append(f"  {shot_id}: {filename} @ {tl_start}s ({duration_s}s)")
        else:
            skipped.append(f"{shot_id} (insert failed)")

    output = f"Timeline '{name}' built with {len(results)} clips:\n" + "\n".join(results)
    if skipped:
        output += f"\n\nSkipped {len(skipped)}:\n  " + "\n  ".join(skipped)
    return output

@mcp.tool()
def create_timeline_from_clips(timeline_name: str, clip_names: List[str]) -> str:
    """Create a new timeline from the specified clips by name."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    media_pool = resolve_api.get_media_pool()
    if not media_pool:
        return "No media pool available."
    folder = media_pool.GetCurrentFolder()
    all_clips = folder.GetClips()
    clip_list = all_clips.values() if isinstance(all_clips, dict) else (all_clips or [])
    clips = [c for c in clip_list if c.GetClipProperty("Clip Name") in clip_names]
    timeline = resolve_api.create_timeline_from_clips(timeline_name, clips)
    return f"Timeline '{timeline_name}' created with {len(clips)} clips." if timeline else "Failed to create timeline."

@mcp.tool()
def import_timeline_from_file(file_path: str) -> str:
    """Import a timeline from a file (e.g., XML, EDL)."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    timeline = resolve_api.import_timeline_from_file(file_path)
    return f"Timeline imported from '{file_path}'." if timeline else "Failed to import timeline."

@mcp.tool()
def execute_lua(script: str) -> str:
    """Execute a Lua script in Resolve's Fusion environment."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    result = resolve_api.execute_lua(script)
    # Execute() returns None for scripts that don't return a value (e.g. print-only)
    # Only treat as failure if we get a specific False return
    if result is False:
        return "Failed to execute Lua script."
    if result is None:
        return "Lua script executed (no return value)."
    return f"Lua script executed: {result}"

@mcp.tool()
def create_fusion_node(node_type: str, inputs: Optional[Dict[str, Any]] = None) -> str:
    """Create a new node in the current Fusion composition."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    node = resolve_api.create_fusion_node(node_type, inputs)
    return f"Node '{node_type}' created." if node else f"Failed to create '{node_type}' node."

@mcp.tool()
def set_clip_property(clip_name: str, property_name: str, value: Any) -> str:
    """Set a property on a timeline clip by name."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items("video", 1)
    clip = next((item for item in items if item.GetName() == clip_name), None)
    if not clip:
        return f"Clip '{clip_name}' not found."
    success = resolve_api.set_clip_property(clip, property_name, value)
    return f"Property '{property_name}' set to {value} on '{clip_name}'." if success else "Failed to set property."

@mcp.tool()
def add_color_node(node_type: str = "Corrector") -> str:
    """Add a new node to the current clip's color grade."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    node = resolve_api.add_color_node(node_type)
    return f"Color node '{node_type}' added." if node else "Failed to add color node."

@mcp.tool()
def set_project_setting(key: str, value: Any) -> str:
    """Set a specific project setting."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.set_project_setting(key, value)
    return f"Project setting '{key}' set to {value}." if success else f"Failed to set '{key}'."

@mcp.tool()
def start_project_render(preset_name: Optional[str] = None, render_path: Optional[str] = None) -> str:
    """Start rendering the current project with optional preset and path."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.start_render(preset_name, render_path)
    return "Render started." if success else "Failed to start render."

@mcp.tool()
def add_timeline_marker(frame: int, color: str = "Blue", name: str = "", note: str = "") -> str:
    """Add a marker to the current timeline at a specific frame."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.add_timeline_marker(frame, color, name, note)
    return f"Marker added at frame {frame}." if success else "Failed to add marker."

@mcp.tool()
def save_still(album_name: str = "Stills") -> str:
    """Save the current clip's grade as a still in the specified gallery album."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    still = resolve_api.save_still(album_name)
    return f"Still saved to '{album_name}'." if still else "Failed to save still."

@mcp.tool()
def apply_still(still_name: str, clip_name: Optional[str] = None) -> str:
    """Apply a still (grade) to a clip by name, defaulting to current clip if none specified."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    gallery = resolve_api.get_gallery()
    if not gallery:
        return "No gallery available."
    albums = resolve_api.get_gallery_albums()
    still = None
    for album in albums:
        stills = album.GetStills()
        still = next((s for s in stills if s.GetLabel() == still_name), None)
        if still:
            break
    if not still:
        return f"Still '{still_name}' not found."
    clip = None
    if clip_name:
        items = resolve_api.get_timeline_items("video", 1)
        clip = next((item for item in items if item.GetName() == clip_name), None)
        if not clip:
            return f"Clip '{clip_name}' not found."
    success = resolve_api.apply_still(still, clip)
    return f"Still '{still_name}' applied." if success else "Failed to apply still."

@mcp.tool()
def add_track(track_type: str = "video", sub_track_type: Optional[str] = None) -> str:
    """Add a new track to the current timeline. For audio tracks, sub_track_type controls channel format: 'mono', 'stereo', '5.1', '5.1film', '7.1', '7.1film', 'adaptive1'-'adaptive36'."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.add_track(track_type, sub_track_type)
    label = f"{track_type.capitalize()}"
    if sub_track_type:
        label += f" ({sub_track_type})"
    return f"{label} track added." if success else f"Failed to add {track_type} track."

@mcp.tool()
def set_track_name(track_type: str, track_index: int, name: str) -> str:
    """Set the name of a track in the current timeline."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.set_track_name(track_type, track_index, name)
    return f"Track {track_index} named '{name}'." if success else "Failed to set track name."

@mcp.tool()
def enable_track(track_type: str, track_index: int, enable: bool = True) -> str:
    """Enable or disable a track in the current timeline."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.enable_track(track_type, track_index, enable)
    state = "enabled" if enable else "disabled"
    return f"Track {track_index} {state}." if success else f"Failed to {state} track."

@mcp.tool()
def set_audio_volume(clip_name: str, volume: float) -> str:
    """Set the audio volume of a timeline clip by name."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items("audio", 1)
    clip = next((item for item in items if item.GetName() == clip_name), None)
    if not clip:
        return f"Clip '{clip_name}' not found."
    success = resolve_api.set_audio_volume(clip, volume)
    return f"Volume set to {volume} on '{clip_name}'." if success else "Failed to set volume."

@mcp.tool()
def set_track_volume(track_index: int, volume: float) -> str:
    """Set the volume of an audio track in the current timeline."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.set_track_volume(track_index, volume)
    return f"Track {track_index} volume set to {volume}." if success else "Failed to set track volume."

@mcp.tool()
def set_current_version(clip_name: str, version_index: int, version_type: str = "color") -> str:
    """Set the current version for a clip by name (e.g., switch between color grades)."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items("video", 1)
    clip = next((item for item in items if item.GetName() == clip_name), None)
    if not clip:
        return f"Clip '{clip_name}' not found."
    success = resolve_api.set_current_version(clip, version_index, version_type)
    return f"Version {version_index} set for '{clip_name}'." if success else "Failed to set version."

@mcp.tool()
def play_timeline() -> str:
    """Start playback in the current timeline."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.play()
    return "Playback started." if success else "Failed to start playback."

@mcp.tool()
def stop_timeline() -> str:
    """Stop playback in the current timeline."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.stop()
    return "Playback stopped." if success else "Failed to stop playback."

@mcp.tool()
def set_playhead_position(frame: int) -> str:
    """Set the playhead position to a specific frame in the current timeline."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.set_playhead_position(frame)
    if success:
        return f"Playhead set to frame {frame}."
    debug = getattr(resolve_api, '_playhead_debug', 'no debug info')
    return f"Failed to set playhead position. Debug: {debug}"

# ─── Tier 1: Titles, Generators, Render Pipeline, Timeline Export ───

@mcp.tool()
def insert_title(title_name: str, track_index: int = 1) -> str:
    """Insert a title (text+) into the current timeline at the playhead. Use 'Text+' for default."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.insert_title(title_name)
    return f"Title '{title_name}' inserted." if success else f"Failed to insert title '{title_name}'."

@mcp.tool()
def insert_fusion_title(title_name: str) -> str:
    """Insert a Fusion-based title into the current timeline."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.insert_fusion_title(title_name)
    return f"Fusion title '{title_name}' inserted." if success else f"Failed to insert Fusion title '{title_name}'."

@mcp.tool()
def insert_generator(generator_name: str) -> str:
    """Insert a generator (e.g., 'Solid Color', '10 Point Gradient') into the timeline."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.insert_generator(generator_name)
    return f"Generator '{generator_name}' inserted." if success else f"Failed to insert generator '{generator_name}'."

@mcp.tool()
def insert_fusion_generator(generator_name: str) -> str:
    """Insert a Fusion generator into the timeline."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.insert_fusion_generator(generator_name)
    return f"Fusion generator '{generator_name}' inserted." if success else f"Failed to insert Fusion generator '{generator_name}'."

@mcp.tool()
def duplicate_timeline(new_name: Optional[str] = None) -> str:
    """Duplicate the current timeline, optionally with a new name."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    result = resolve_api.duplicate_timeline(new_name)
    if result:
        try:
            return f"Timeline duplicated as '{result.GetName()}'."
        except:
            return "Timeline duplicated."
    return "Failed to duplicate timeline."

@mcp.tool()
def create_compound_clip(track_type: str, track_index: int, item_indices: List[int], name: str = "Compound Clip") -> str:
    """Create a compound clip from timeline items specified by index."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items:
        return f"No items on {track_type} track {track_index}."
    selected = [items[i] for i in item_indices if 0 <= i < len(items)]
    if not selected:
        return "No valid items selected."
    success = resolve_api.create_compound_clip(selected, {"name": name})
    return f"Compound clip '{name}' created from {len(selected)} items." if success else "Failed to create compound clip."

@mcp.tool()
def export_current_timeline(file_path: str, export_type: str, export_subtype: Optional[str] = None) -> str:
    """Export the current timeline to file. export_type: 'AAF', 'DRT', 'EDL', 'FCP_7_XML', 'FCPXML_1_8', etc."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.export_timeline(file_path, export_type, export_subtype)
    return f"Timeline exported to '{file_path}'." if success else "Failed to export timeline."

@mcp.tool()
def get_timeline_setting(setting_name: str) -> str:
    """Get a specific timeline setting (e.g., 'timelineFrameRate', 'timelineResolutionWidth')."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    value = resolve_api.get_timeline_setting(setting_name)
    return f"{setting_name} = {value}" if value is not None else f"Setting '{setting_name}' not found."

@mcp.tool()
def set_timeline_setting(setting_name: str, value: str) -> str:
    """Set a specific timeline setting."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.set_timeline_setting(setting_name, value)
    return f"Timeline setting '{setting_name}' set to '{value}'." if success else f"Failed to set '{setting_name}'."

# Render pipeline tools

@mcp.tool()
def add_render_job() -> str:
    """Add a render job based on current render settings. Returns the job ID."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    job_id = resolve_api.add_render_job()
    return f"Render job added: {job_id}" if job_id else "Failed to add render job."

@mcp.tool()
def delete_render_job(job_id: str) -> str:
    """Delete a render job by its ID."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.delete_render_job(job_id)
    return f"Render job '{job_id}' deleted." if success else f"Failed to delete job '{job_id}'."

@mcp.tool()
def delete_all_render_jobs() -> str:
    """Delete all render jobs from the queue."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.delete_all_render_jobs()
    return "All render jobs deleted." if success else "Failed to delete render jobs."

@mcp.tool()
def get_render_job_list() -> str:
    """List all render jobs with their details."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    jobs = resolve_api.get_render_job_list()
    if not jobs:
        return "No render jobs."
    lines = []
    for i, job in enumerate(jobs):
        lines.append(f"  [{i}] {job}")
    return f"{len(jobs)} render jobs:\n" + "\n".join(lines)

@mcp.tool()
def get_render_preset_list() -> str:
    """List available render presets."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    presets = resolve_api.get_render_preset_list()
    return "\n".join(presets) if presets else "No render presets found."

@mcp.tool()
def load_render_preset(preset_name: str) -> str:
    """Load a render preset by name."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.load_render_preset(preset_name)
    return f"Preset '{preset_name}' loaded." if success else f"Failed to load preset '{preset_name}'."

@mcp.tool()
def set_render_settings(settings: Dict[str, Any]) -> str:
    """Set render settings. Common keys: TargetDir, CustomName, FormatWidth, FormatHeight, FrameRate."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.set_render_settings(settings)
    return f"Render settings updated: {list(settings.keys())}" if success else "Failed to set render settings."

@mcp.tool()
def get_render_formats() -> str:
    """Get all supported render formats."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    formats = resolve_api.get_render_formats()
    if not formats:
        return "No render formats available."
    lines = [f"  {k}: {v}" for k, v in formats.items()]
    return "Render formats:\n" + "\n".join(lines)

@mcp.tool()
def get_render_codecs(render_format: str) -> str:
    """Get available codecs for a specific render format."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    codecs = resolve_api.get_render_codecs(render_format)
    if not codecs:
        return f"No codecs for format '{render_format}'."
    lines = [f"  {k}: {v}" for k, v in codecs.items()]
    return f"Codecs for '{render_format}':\n" + "\n".join(lines)

@mcp.tool()
def set_render_format_and_codec(render_format: str, codec: str) -> str:
    """Set the render format and codec (e.g., format='mp4', codec='H264')."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.set_render_format_and_codec(render_format, codec)
    return f"Render set to {render_format}/{codec}." if success else "Failed to set format/codec."

@mcp.tool()
def get_render_job_status(job_id: str) -> str:
    """Get the status of a specific render job."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    status = resolve_api.get_render_job_status(job_id)
    return f"Job '{job_id}': {status}" if status else f"No status for job '{job_id}'."

@mcp.tool()
def stop_rendering() -> str:
    """Stop any active rendering."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.stop_rendering()
    return "Rendering stopped." if success else "Failed to stop rendering."

@mcp.tool()
def is_rendering() -> str:
    """Check if rendering is currently in progress."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    rendering = resolve_api.is_rendering()
    return f"Rendering: {'Yes' if rendering else 'No'}"

@mcp.tool()
def start_rendering() -> str:
    """Start rendering all queued render jobs."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    if not resolve_api._ensure_project():
        return "No project."
    try:
        result = resolve_api.current_project.StartRendering()
        return "Rendering started." if result else "Failed to start rendering."
    except Exception as e:
        return f"Error: {e}"

# ─── Tier 2: Color Grading Workflow ───

@mcp.tool()
def set_lut(track_type: str, track_index: int, item_index: int, node_index: int, lut_path: str) -> str:
    """Apply a LUT file to a specific node of a timeline clip."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    success = resolve_api.set_lut(items[item_index], node_index, lut_path)
    return f"LUT applied to node {node_index}." if success else "Failed to apply LUT."

@mcp.tool()
def set_cdl(track_type: str, track_index: int, item_index: int, slope: Optional[List[float]] = None, offset: Optional[List[float]] = None, power: Optional[List[float]] = None, saturation: Optional[float] = None) -> str:
    """Apply CDL values to a timeline clip. slope/offset/power are [R,G,B] lists."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    cdl = {}
    if slope: cdl["Slope"] = slope
    if offset: cdl["Offset"] = offset
    if power: cdl["Power"] = power
    if saturation is not None: cdl["Saturation"] = saturation
    success = resolve_api.set_cdl(items[item_index], cdl)
    return f"CDL applied: {list(cdl.keys())}" if success else "Failed to apply CDL."

@mcp.tool()
def copy_grades(track_type: str, track_index: int, source_index: int, target_indices: List[int]) -> str:
    """Copy color grade from one clip to others on the same track."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items:
        return "No items found."
    if source_index < 0 or source_index >= len(items):
        return f"Source index {source_index} out of range."
    targets = [items[i] for i in target_indices if 0 <= i < len(items)]
    if not targets:
        return "No valid target items."
    success = resolve_api.copy_grades(items[source_index], targets)
    return f"Grade copied to {len(targets)} clips." if success else "Failed to copy grades."

@mcp.tool()
def apply_grade_from_drx(drx_path: str, grade_mode: int, track_type: str, track_index: int, item_indices: List[int]) -> str:
    """Apply a DRX grade file to clips. grade_mode: 0=No keyframes, 1=Source TC, 2=Start frames."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items:
        return "No items found."
    selected = [items[i] for i in item_indices if 0 <= i < len(items)]
    success = resolve_api.apply_grade_from_drx(drx_path, grade_mode, selected)
    return f"DRX grade applied to {len(selected)} clips." if success else "Failed to apply DRX grade."

@mcp.tool()
def refresh_lut_list() -> str:
    """Refresh the project's LUT list to pick up newly added LUTs."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.refresh_lut_list()
    return "LUT list refreshed." if success else "Failed to refresh LUT list."

# ─── Tier 3: Organization & Metadata ───

@mcp.tool()
def get_media_clip_metadata(clip_name: str, key: Optional[str] = None) -> str:
    """Get metadata for a media pool clip. If key is provided, returns just that value."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    clip = _find_media_pool_clip(clip_name)
    if not clip:
        return f"Clip '{clip_name}' not found."
    result = resolve_api.get_clip_metadata(clip, key)
    if key:
        return f"{clip_name}.{key} = {result}"
    lines = [f"  {k}: {v}" for k, v in result.items()] if isinstance(result, dict) else [str(result)]
    return f"Metadata for '{clip_name}':\n" + "\n".join(lines)

@mcp.tool()
def set_media_clip_metadata(clip_name: str, metadata: Dict[str, str]) -> str:
    """Set metadata on a media pool clip (dict of key-value pairs)."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    clip = _find_media_pool_clip(clip_name)
    if not clip:
        return f"Clip '{clip_name}' not found."
    success = resolve_api.set_clip_metadata(clip, metadata)
    return f"Metadata set on '{clip_name}': {list(metadata.keys())}" if success else "Failed to set metadata."

@mcp.tool()
def add_clip_marker(clip_name: str, frame: int, color: str = "Blue", name: str = "", note: str = "", duration: int = 1) -> str:
    """Add a marker to a media pool clip at a specific frame."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    clip = _find_media_pool_clip(clip_name)
    if not clip:
        return f"Clip '{clip_name}' not found."
    success = resolve_api.add_clip_marker(clip, frame, color, name, note, duration)
    return f"Marker added to '{clip_name}' at frame {frame}." if success else "Failed to add marker."

@mcp.tool()
def get_clip_markers(clip_name: str) -> str:
    """Get all markers on a media pool clip."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    clip = _find_media_pool_clip(clip_name)
    if not clip:
        return f"Clip '{clip_name}' not found."
    markers = resolve_api.get_clip_markers(clip)
    if not markers:
        return f"No markers on '{clip_name}'."
    lines = [f"  Frame {k}: {v}" for k, v in markers.items()]
    return f"Markers on '{clip_name}':\n" + "\n".join(lines)

@mcp.tool()
def get_timeline_markers() -> str:
    """Get all markers on the current timeline."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    markers = resolve_api.get_timeline_markers()
    if not markers:
        return "No timeline markers."
    lines = [f"  Frame {k}: {v}" for k, v in markers.items()]
    return f"{len(markers)} timeline markers:\n" + "\n".join(lines)

@mcp.tool()
def delete_timeline_markers_by_color(color: str) -> str:
    """Delete all timeline markers of a given color. Use 'All' to delete all markers."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.delete_timeline_markers_by_color(color)
    return f"Deleted {color} markers." if success else f"Failed to delete {color} markers."

@mcp.tool()
def set_clip_color(track_type: str, track_index: int, item_index: int, color: str) -> str:
    """Set the color label on a timeline clip. Colors: Blue, Cyan, Green, Yellow, Red, Pink, Purple, Fuchsia, Rose, Lavender, Sky, Mint, Lemon, Sand, Cocoa, Cream."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    success = resolve_api.set_clip_color(items[item_index], color)
    return f"Clip color set to '{color}'." if success else "Failed to set clip color."

@mcp.tool()
def add_flag(track_type: str, track_index: int, item_index: int, color: str) -> str:
    """Add a flag to a timeline clip."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    success = resolve_api.add_flag(items[item_index], color)
    return f"Flag '{color}' added." if success else "Failed to add flag."

@mcp.tool()
def get_flag_list(track_type: str, track_index: int, item_index: int) -> str:
    """Get all flags on a timeline clip."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    flags = resolve_api.get_flag_list(items[item_index])
    return f"Flags: {flags}" if flags else "No flags."

@mcp.tool()
def relink_clips(clip_names: List[str], folder_path: str) -> str:
    """Relink media pool clips to a new folder path."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    name_map = resolve_api.find_clips_by_name(clip_names)
    matched = [name_map[n] for n in clip_names if n in name_map]
    if not matched:
        return "No matching clips found."
    success = resolve_api.relink_clips(matched, folder_path)
    return f"Relinked {len(matched)} clips to '{folder_path}'." if success else "Failed to relink."

@mcp.tool()
def delete_media_clips(clip_names: List[str]) -> str:
    """Delete clips from the media pool by name."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    name_map = resolve_api.find_clips_by_name(clip_names)
    matched = [name_map[n] for n in clip_names if n in name_map]
    if not matched:
        return "No matching clips found."
    success = resolve_api.delete_clips(matched)
    return f"Deleted {len(matched)} clips." if success else "Failed to delete clips."

@mcp.tool()
def delete_media_folders(folder_names: List[str]) -> str:
    """Delete folders from the media pool by name."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    folders = [resolve_api.find_folder_by_name(n) for n in folder_names]
    matched = [f for f in folders if f is not None]
    if not matched:
        return "No matching folders found."
    success = resolve_api.delete_folders(matched)
    return f"Deleted {len(matched)} folders." if success else "Failed to delete folders."

@mcp.tool()
def export_metadata(file_name: str, clip_names: Optional[List[str]] = None) -> str:
    """Export clip metadata to CSV. If clip_names provided, exports only those clips."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    clips = None
    if clip_names:
        name_map = resolve_api.find_clips_by_name(clip_names)
        clips = [name_map[n] for n in clip_names if n in name_map]
    success = resolve_api.export_metadata(file_name, clips)
    return f"Metadata exported to '{file_name}'." if success else "Failed to export metadata."

# Takes system

@mcp.tool()
def add_take(track_type: str, track_index: int, item_index: int, clip_name: str, start_frame: Optional[int] = None, end_frame: Optional[int] = None) -> str:
    """Add an alternate take to a timeline item from a media pool clip."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    mp_clip = _find_media_pool_clip(clip_name)
    if not mp_clip:
        return f"Clip '{clip_name}' not found in media pool."
    success = resolve_api.add_take(items[item_index], mp_clip, start_frame, end_frame)
    return f"Take '{clip_name}' added." if success else "Failed to add take."

@mcp.tool()
def get_takes_count(track_type: str, track_index: int, item_index: int) -> str:
    """Get number of takes for a timeline item."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    count = resolve_api.get_takes_count(items[item_index])
    return f"Takes: {count}"

@mcp.tool()
def select_take(track_type: str, track_index: int, item_index: int, take_index: int) -> str:
    """Select a take by index on a timeline item."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    success = resolve_api.select_take(items[item_index], take_index)
    return f"Take {take_index} selected." if success else "Failed to select take."

@mcp.tool()
def finalize_take(track_type: str, track_index: int, item_index: int) -> str:
    """Finalize the selected take on a timeline item (makes it permanent)."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    success = resolve_api.finalize_take(items[item_index])
    return "Take finalized." if success else "Failed to finalize take."

# ─── Tier 4: Fusion & Advanced ───

@mcp.tool()
def create_fusion_clip(track_type: str, track_index: int, item_indices: List[int]) -> str:
    """Create a Fusion clip from timeline items."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items:
        return "No items found."
    selected = [items[i] for i in item_indices if 0 <= i < len(items)]
    if not selected:
        return "No valid items selected."
    success = resolve_api.create_fusion_clip(selected)
    return f"Fusion clip created from {len(selected)} items." if success else "Failed to create Fusion clip."

@mcp.tool()
def add_fusion_comp(track_type: str, track_index: int, item_index: int) -> str:
    """Add a new Fusion composition to a timeline item."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    success = resolve_api.add_fusion_comp(items[item_index])
    return "Fusion comp added." if success else "Failed to add Fusion comp."

@mcp.tool()
def import_fusion_comp(track_type: str, track_index: int, item_index: int, file_path: str) -> str:
    """Import a Fusion composition from a .comp or .setting file."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    success = resolve_api.import_fusion_comp(items[item_index], file_path)
    return f"Fusion comp imported from '{file_path}'." if success else "Failed to import Fusion comp."

@mcp.tool()
def export_fusion_comp(track_type: str, track_index: int, item_index: int, file_path: str, comp_index: int = 1) -> str:
    """Export a Fusion composition from a timeline item to file."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    success = resolve_api.export_fusion_comp(items[item_index], file_path, comp_index)
    return f"Fusion comp exported to '{file_path}'." if success else "Failed to export Fusion comp."

@mcp.tool()
def get_fusion_comp_names(track_type: str, track_index: int, item_index: int) -> str:
    """Get list of Fusion composition names on a timeline item."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    items = resolve_api.get_timeline_items(track_type, track_index)
    if not items or item_index < 0 or item_index >= len(items):
        return f"Item index {item_index} out of range."
    names = resolve_api.get_fusion_comp_names(items[item_index])
    return f"Fusion comps: {names}" if names else "No Fusion compositions."

@mcp.tool()
def grab_still() -> str:
    """Grab a still from the current frame to the gallery."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    result = resolve_api.grab_still()
    return "Still grabbed." if result else "Failed to grab still."

@mcp.tool()
def grab_all_stills(still_frame_source: int = 2) -> str:
    """Grab stills from all clips in the timeline. source: 1=first frame, 2=middle frame."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.grab_all_stills(still_frame_source)
    return "Stills grabbed from all clips." if success else "Failed to grab stills."

@mcp.tool()
def insert_fusion_composition() -> str:
    """Insert a Fusion composition at the playhead in the current timeline."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    success = resolve_api.insert_fusion_composition()
    return "Fusion composition inserted." if success else "Failed to insert Fusion composition."

@mcp.tool()
def get_track_count(track_type: str = "video") -> str:
    """Get number of tracks of a given type in the current timeline."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    count = resolve_api.get_track_count(track_type)
    return f"{track_type} tracks: {count}"

@mcp.tool()
def get_current_video_item() -> str:
    """Get info about the video item currently under the playhead."""
    if not resolve_api.is_connected():
        return "Not connected to DaVinci Resolve."
    item = resolve_api.get_current_video_item()
    if not item:
        return "No video item under playhead."
    try:
        name = item.GetName()
        start = item.GetStart()
        end = item.GetEnd()
        return f"Current item: {name} (start={start}, end={end})"
    except Exception as e:
        return f"Item found but error reading: {e}"

# --- Main Entry Point ---

def main():
    """Run the MCP server."""
    logger.info("Starting DaVinci Resolve MCP server...")
    mcp.run()  # Start the MCP server to listen for connections

if __name__ == "__main__":
    main()  # Execute main function if script is run directly
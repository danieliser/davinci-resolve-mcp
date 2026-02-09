"""
DaVinci Resolve API connector module.

This module provides functions to connect to DaVinci Resolve's Python API
and interact with its various components, such as projects, timelines, media pools, and more.
"""

import sys
import os
import platform
import logging
from typing import Optional, Dict, List, Any, Union, Tuple

# ─── DaVinci Resolve proxy type aliases ───────────────────────────────────────
# Resolve's scripting API returns opaque C-extension proxy objects with no
# Python type stubs. These aliases document intent — the runtime type is always
# a Resolve proxy (or None).  Use these in signatures so callers know *which
# kind* of proxy a method expects/returns.
ResolveApp = Any          # dvr_script.scriptapp("Resolve")
ProjectManager = Any      # resolve.GetProjectManager()
Project = Any             # pm.GetCurrentProject()
MediaStorage = Any        # resolve.GetMediaStorage()
MediaPool = Any           # project.GetMediaPool()
MediaPoolFolder = Any     # mediaPool.GetRootFolder() / GetCurrentFolder()
MediaPoolItem = Any       # folder.GetClips()[n]
Timeline = Any            # project.GetCurrentTimeline()
TimelineItem = Any        # timeline.GetItemListInTrack(...)[n]
Fusion = Any              # resolve.Fusion()
FusionComp = Any          # fusion.CurrentComp / item.GetFusionCompByIndex(n)
FusionTool = Any          # comp.AddTool(...) / comp.FindTool(...)
Gallery = Any             # project.GetGallery()
GalleryAlbum = Any        # gallery.GetGalleryAlbumList()[n]
GalleryStill = Any        # timeline.GrabStill()

# Configure logging with a standard format including timestamp, logger name, level, and message
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ResolveAPI")  # Logger instance for this module

class ResolveAPI:
    """Class to handle connection and interaction with DaVinci Resolve API."""
    
    def __init__(self) -> None:
        """
        Initialize the ResolveAPI class and establish a connection to DaVinci Resolve.
        Sets up internal references to Resolve objects (e.g., project manager, media pool).
        """
        self.resolve: Optional[ResolveApp] = None
        self.fusion: Optional[Fusion] = None
        self.project_manager: Optional[ProjectManager] = None
        self.current_project: Optional[Project] = None
        self.media_storage: Optional[MediaStorage] = None
        self.media_pool: Optional[MediaPool] = None
        self._playhead_debug: str = ""
        self._connect_to_resolve()

    def _find_scripting_module(self) -> Optional[str]:
        """
        Dynamically locate the DaVinciResolveScript module path based on the operating system.
        Checks for a custom path via environment variable, then falls back to default locations.
        
        Returns:
            Optional[str]: Path to the scripting module if found, None otherwise.
        """
        custom_path = os.environ.get("RESOLVE_SCRIPT_PATH")  # Check for user-defined path
        if custom_path and os.path.exists(custom_path):
            return custom_path
        # Default paths for Resolve scripting module by OS
        base_paths = {
            "Windows": os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"), "Blackmagic Design", "DaVinci Resolve", "Support", "Developer", "Scripting", "Modules"),
            "Darwin": ["/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules",
                       os.path.join(os.path.expanduser("~"), "Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules")],
            "Linux": "/opt/resolve/Developer/Scripting/Modules"
        }
        system = platform.system()  # Get current OS
        paths = base_paths.get(system, []) if system != "Darwin" else base_paths["Darwin"]
        for path in ([paths] if isinstance(paths, str) else paths):  # Handle single path or list
            if os.path.exists(path) and path not in sys.path:
                sys.path.append(path)  # Add to Python path if not already present
                return path
        return None  # Return None if no valid path is found

    def _connect_to_resolve(self) -> None:
        """
        Establish a connection to DaVinci Resolve by importing its scripting module.
        Initializes core objects (e.g., project manager, media pool) if successful.
        """
        script_path = self._find_scripting_module()  # Find the scripting module path
        if not script_path:
            logger.error("No valid Resolve scripting module path found")
            return
        try:
            import DaVinciResolveScript as dvr_script  # Import the Resolve scripting API
            self.resolve = dvr_script.scriptapp("Resolve")  # Connect to Resolve app
            logger.info(f"Connected to Resolve using {script_path}")
        except ImportError:
            logger.error(f"Failed to import DaVinciResolveScript from {script_path}")
            self.resolve = None
        if self.resolve:  # If connection is successful, initialize other objects
            self.project_manager = self.resolve.GetProjectManager()
            self.current_project = self.project_manager.GetCurrentProject()
            self.media_storage = self.resolve.GetMediaStorage()
            self.fusion = self.resolve.Fusion()
            self.media_pool = self.current_project.GetMediaPool() if self.current_project else None

    def refresh(self) -> None:
        """
        Refresh all internal Resolve objects to ensure they reflect the current state.
        Useful if Resolve's state changes externally (e.g., project switch).
        """
        if not self.resolve:
            self._connect_to_resolve()
        if self.resolve:
            self.project_manager = self.resolve.GetProjectManager()
            self.current_project = self.project_manager.GetCurrentProject()
            self.media_storage = self.resolve.GetMediaStorage()
            try:
                self.fusion = self.resolve.Fusion()
            except Exception:
                self.fusion = None
            self.media_pool = self.current_project.GetMediaPool() if self.current_project else None
            logger.info("Refreshed Resolve API state")

    def _ensure_project(self) -> bool:
        """Auto-refresh if current_project proxy is stale, return True if valid."""
        try:
            if self.current_project:
                self.current_project.GetName()  # Test the proxy
                return True
        except Exception:
            pass
        self.refresh()
        return self.current_project is not None

    def _ensure_media_pool(self) -> bool:
        """Auto-refresh if media_pool proxy is stale, return True if valid."""
        try:
            if self.media_pool:
                self.media_pool.GetRootFolder()  # Test the proxy
                return True
        except Exception:
            pass
        self.refresh()
        return self.media_pool is not None

    def _ensure_timeline(self) -> Optional[Timeline]:
        """Return current timeline, auto-refreshing if proxy is stale."""
        if not self._ensure_project():
            return None
        try:
            tl = self.current_project.GetCurrentTimeline()
            if tl:
                tl.GetName()  # Test the proxy
                return tl
        except Exception:
            self.refresh()
        if self.current_project:
            return self.current_project.GetCurrentTimeline()
        return None

    def is_connected(self) -> bool:
        """
        Check if the API is connected to DaVinci Resolve.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self.resolve is not None

    def get_project_manager(self) -> Optional[ProjectManager]:
        """Get the project manager object."""
        return self.project_manager

    def get_current_project(self) -> Optional[Project]:
        """Get the current project object, auto-refreshing if proxy is stale."""
        self._ensure_project()
        return self.current_project

    def get_media_storage(self) -> Optional[MediaStorage]:
        """Get the media storage object."""
        return self.media_storage

    def get_media_pool(self) -> Optional[MediaPool]:
        """Get the media pool object for the current project, auto-refreshing if stale."""
        self._ensure_media_pool()
        return self.media_pool

    def get_fusion(self) -> Optional[Fusion]:
        """Get the Fusion object for compositing tasks."""
        return self.fusion

    def open_page(self, page_name: str) -> bool:
        """
        Open a specific page in DaVinci Resolve (e.g., "edit", "color").
        """
        if not self.resolve:
            self.refresh()
        if not self.resolve:
            return False
        valid_pages = ["media", "edit", "fusion", "color", "fairlight", "deliver"]
        if page_name.lower() not in valid_pages:
            return False
        self.resolve.OpenPage(page_name.lower())
        return True

    def create_project(self, project_name: str) -> bool:
        """
        Create a new project with the given name.

        Args:
            project_name (str): Name of the project to create.

        Returns:
            bool: True if successful, False if project manager is unavailable or creation fails.
        """
        if not self.project_manager:
            return False
        new_project = self.project_manager.CreateProject(project_name)
        if new_project:
            self.refresh()  # Re-acquire all proxy objects after project creation
            return True
        return False

    def load_project(self, project_name: str) -> bool:
        """
        Load an existing project by name.
        
        Args:
            project_name (str): Name of the project to load.
        
        Returns:
            bool: True if successful, False if project manager is unavailable or project doesn't exist.
        """
        if not self.project_manager:
            return False
        loaded_project = self.project_manager.LoadProject(project_name)
        if loaded_project:  # If loading succeeds, update internal state
            self.current_project = loaded_project
            self.media_pool = self.current_project.GetMediaPool()
            return True
        return False

    def save_project(self) -> bool:
        """Save the current project."""
        if not self._ensure_project():
            return False
        try:
            result = self.current_project.SaveProject()
            # Some Resolve versions return None on success instead of True
            if result is not False:
                return True
        except Exception:
            pass
        # Retry after full refresh
        self.refresh()
        if not self.current_project:
            return False
        try:
            result = self.current_project.SaveProject()
            return result is not False
        except Exception as e:
            logger.error(f"Failed to save project after retry: {e}")
            return False

    def get_project_name(self) -> Optional[str]:
        """Get the name of the current project."""
        if not self._ensure_project():
            return None
        return self.current_project.GetName()

    def create_timeline(self, timeline_name: str) -> bool:
        """Create a new empty timeline in the current project."""
        if not self._ensure_media_pool():
            return False
        new_timeline = self.media_pool.CreateEmptyTimeline(timeline_name)
        return new_timeline is not None

    def get_current_timeline(self) -> Optional[Timeline]:
        """Get the current timeline, auto-refreshing if proxy is stale."""
        return self._ensure_timeline()

    def delete_timeline(self, timeline: Timeline) -> bool:
        """Delete a timeline from the current project."""
        if not self._ensure_media_pool():
            return False
        try:
            return self.media_pool.DeleteTimelines([timeline])
        except Exception as e:
            logger.error(f"Failed to delete timeline: {e}")
            return False

    def get_timeline_count(self) -> int:
        """Get the number of timelines in the current project."""
        if not self._ensure_project():
            return 0
        return self.current_project.GetTimelineCount()

    def get_timeline_by_index(self, index: int):
        """Get a timeline by its 1-based index."""
        if not self._ensure_project():
            return None
        return self.current_project.GetTimelineByIndex(index)

    def set_current_timeline(self, timeline) -> bool:
        """Set the specified timeline as the current one."""
        if not self._ensure_project():
            return False
        return self.current_project.SetCurrentTimeline(timeline)

    def get_mounted_volumes(self) -> List[str]:
        """
        Get a list of mounted volumes in the media storage.
        
        Returns:
            List[str]: List of volume paths, empty if media storage is unavailable.
        """
        if not self.media_storage:
            return []
        return self.media_storage.GetMountedVolumes()

    def get_sub_folders(self, folder_path: str) -> List[str]:
        """
        Get a list of subfolders in the specified folder path.
        
        Args:
            folder_path (str): Path to the folder.
        
        Returns:
            List[str]: List of subfolder paths, empty if media storage is unavailable.
        """
        if not self.media_storage:
            return []
        return self.media_storage.GetSubFolders(folder_path)

    def get_files(self, folder_path: str) -> List[str]:
        """
        Get a list of files in the specified folder path.
        
        Args:
            folder_path (str): Path to the folder.
        
        Returns:
            List[str]: List of file paths, empty if media storage is unavailable.
        """
        if not self.media_storage:
            return []
        return self.media_storage.GetFiles(folder_path)

    def add_items_to_media_pool(self, file_paths: List[str]) -> List[Any]:
        """
        Add media files to the current media pool using MediaPool.ImportMedia().

        Args:
            file_paths (List[str]): List of file paths to add.

        Returns:
            List[Any]: List of added media pool items, empty if media pool is unavailable.
        """
        if not self.media_pool:
            self.refresh()
        if not self.media_pool:
            return []
        try:
            result = self.media_pool.ImportMedia(file_paths)
            return result if result else []
        except Exception as e:
            logger.error(f"Failed to import media: {e}")
            return []

    def get_root_folder(self):
        """Get the root folder of the media pool."""
        if not self._ensure_media_pool():
            return None
        return self.media_pool.GetRootFolder()

    def get_current_folder(self):
        """Get the current folder in the media pool."""
        if not self._ensure_media_pool():
            return None
        return self.media_pool.GetCurrentFolder()

    def add_sub_folder(self, parent_folder, folder_name: str):
        """Add a subfolder to the specified parent folder in the media pool."""
        if not self._ensure_media_pool():
            return None
        return self.media_pool.AddSubFolder(parent_folder, folder_name)

    def move_clips_to_folder(self, clips: List[Any], target_folder) -> bool:
        """Move media pool clips to a target folder."""
        if not self._ensure_media_pool():
            return False
        try:
            return self.media_pool.MoveClips(clips, target_folder)
        except Exception as e:
            logger.error(f"Failed to move clips: {e}")
            return False

    def set_current_folder(self, folder: MediaPoolFolder) -> bool:
        """Set the current folder in the media pool."""
        if not self._ensure_media_pool():
            return False
        try:
            return self.media_pool.SetCurrentFolder(folder)
        except Exception as e:
            logger.error(f"Failed to set current folder: {e}")
            return False

    def find_folder_by_name(self, name: str, parent=None):
        """Find a folder by name, searching recursively from parent (or root)."""
        if not self._ensure_media_pool():
            return None
        if parent is None:
            parent = self.media_pool.GetRootFolder()
        if not parent:
            return None
        if parent.GetName() == name:
            return parent
        subs = parent.GetSubFolders()
        sub_list = subs.values() if isinstance(subs, dict) else (subs or [])
        for sub in sub_list:
            if sub.GetName() == name:
                return sub
            found = self.find_folder_by_name(name, sub)
            if found:
                return found
        return None

    def get_folder_clips(self, folder: MediaPoolFolder) -> List[MediaPoolItem]:
        """
        Get a list of clips in the specified folder.

        Args:
            folder: Folder object.

        Returns:
            List[Any]: List of media pool items, empty if folder is invalid.
        """
        if not folder:
            return []
        return folder.GetClips()

    def find_clips_by_name(self, clip_names: List[str], source_folder=None) -> dict:
        """Search all media pool folders for clips matching the given names.
        Returns dict of {clip_name: clip_object} for matches found."""
        if not self._ensure_media_pool():
            return {}
        if source_folder is None:
            source_folder = self.media_pool.GetRootFolder()
        if not source_folder:
            return {}
        result = {}
        # Search this folder
        try:
            raw = source_folder.GetClips()
            if raw:
                items = raw.values() if isinstance(raw, dict) else raw
                for c in items:
                    try:
                        name = c.GetClipProperty("Clip Name")
                        if name and name in clip_names:
                            result[name] = c
                    except:
                        pass
        except:
            pass
        # Recurse into subfolders
        try:
            subs = source_folder.GetSubFolders()
            sub_list = subs.values() if isinstance(subs, dict) else (subs or [])
            for sub in sub_list:
                result.update(self.find_clips_by_name(clip_names, sub))
        except:
            pass
        return result

    def list_all_clip_names(self, folder=None) -> List[str]:
        """List all clip names recursively from the given folder (or root)."""
        if not self._ensure_media_pool():
            return []
        if folder is None:
            folder = self.media_pool.GetRootFolder()
        if not folder:
            return []
        names = []
        try:
            raw = folder.GetClips()
            if raw:
                items = raw.values() if isinstance(raw, dict) else raw
                for c in items:
                    try:
                        name = c.GetClipProperty("Clip Name")
                        if name:
                            names.append(name)
                    except:
                        pass
        except:
            pass
        try:
            subs = folder.GetSubFolders()
            sub_list = subs.values() if isinstance(subs, dict) else (subs or [])
            for sub in sub_list:
                names.extend(self.list_all_clip_names(sub))
        except:
            pass
        return names

    def get_folder_name(self, folder: MediaPoolFolder) -> Optional[str]:
        """
        Get the name of the specified folder.
        
        Args:
            folder: Folder object.
        
        Returns:
            Optional[str]: Folder name or None if folder is invalid.
        """
        if not folder:
            return None
        return folder.GetName()

    def get_folder_sub_folders(self, folder: MediaPoolFolder) -> List[MediaPoolFolder]:
        """
        Get a list of subfolders in the specified folder.
        
        Args:
            folder: Folder object.
        
        Returns:
            List[Any]: List of subfolder objects, empty if folder is invalid.
        """
        if not folder:
            return []
        return folder.GetSubFolders()

    def append_to_timeline(self, clips: List[Any]) -> bool:
        """Append clips to the current timeline."""
        if not self._ensure_media_pool():
            return False
        return self.media_pool.AppendToTimeline(clips)

    def append_to_timeline_with_info(self, clip_infos: List[Dict[str, Any]]) -> bool:
        """
        Append clips to the current timeline with placement info (track, start frame).

        Args:
            clip_infos: List of dicts with keys:
                - mediaPoolItem: MediaPoolItem object
                - trackIndex (int): 1-based track index to place on
                - startFrame (int, optional): Timeline frame to start at
                - endFrame (int, optional): Timeline frame to end at

        Returns:
            bool: True if successful.
        """
        if not self._ensure_media_pool():
            return False
        try:
            result = self.media_pool.AppendToTimeline(clip_infos)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to append to timeline with info: {e}")
            return False

    def delete_timeline_items(self, items: List[Any], do_ripple: bool = False) -> bool:
        """
        Delete timeline items from the current timeline.

        Args:
            items: List of timeline item objects to delete.
            do_ripple: If True, ripple delete (close gaps). Defaults to False.

        Returns:
            bool: True if successful.
        """
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return timeline.DeleteClips(items, do_ripple)
        except Exception as e:
            logger.error(f"Failed to delete timeline items: {e}")
            return False

    def create_timeline_from_clips(self, timeline_name: str, clips: List[Any]):
        """Create a new timeline from the specified clips."""
        if not self._ensure_media_pool():
            return None
        return self.media_pool.CreateTimelineFromClips(timeline_name, clips)

    def import_timeline_from_file(self, file_path: str):
        """Import a timeline from a file (e.g., XML, EDL)."""
        if not self._ensure_media_pool():
            return None
        return self.media_pool.ImportTimelineFromFile(file_path)

    def execute_lua(self, script: str) -> Optional[Any]:
        """Execute a Lua script in the active Fusion composition.

        Targets the comp visible in the Fusion page UI (via get_current_comp()).
        Falls back to global ``fusion.Execute()`` if no comp is available.

        Note:
            ``comp.Execute()`` does NOT return Lua ``return`` values.  To get
            data out of a Lua script, write results to a temp file via
            ``io.open("/tmp/…", "w")`` and read it back afterwards.

        Returns:
            The raw result from ``Execute()`` — typically ``None`` even on
            success.  Only an explicit ``False`` indicates failure.
        """
        comp: Optional[FusionComp] = self.get_current_comp()
        if comp:
            try:
                return comp.Execute(script)
            except Exception:
                pass
        # Fallback to global Fusion object
        if not self.fusion:
            self.refresh()
        if not self.fusion:
            return None
        return self.fusion.Execute(script)

    def create_fusion_node(
        self, node_type: str, inputs: Optional[Dict[str, Any]] = None
    ) -> Optional[FusionTool]:
        """Create a new node in the active Fusion composition.

        Args:
            node_type: Fusion tool ID (e.g. ``"TextPlus"``, ``"Merge"``, ``"Background"``).
            inputs: Optional dict of input names → values passed via ``SetInput()``.

        Returns:
            The created FusionTool proxy, or ``None`` on failure.
        """
        comp: Optional[FusionComp] = self.get_current_comp()
        if not comp:
            return None
        try:
            node: Optional[FusionTool] = comp.AddTool(node_type, 0, 0)
            if not node:
                return None
            if inputs:
                for key, value in inputs.items():
                    node.SetInput(key, value)
            return node
        except Exception as e:
            logger.error(f"Error creating Fusion node: {e}")
            return None

    def get_current_comp(self) -> Optional[FusionComp]:
        """Get the active Fusion composition — prefers what the user sees.

        Priority order:
          1. ``fusion.CurrentComp`` — matches the Fusion page UI when open.
          2. ``item.GetFusionCompByIndex(1)`` — fallback when Fusion page
             is closed.  WARNING: returns by *creation order*, not active comp.
        """
        if not self.fusion:
            self.refresh()
        if self.fusion:
            try:
                comp: Optional[FusionComp] = self.fusion.CurrentComp
                if comp:
                    return comp
            except Exception:
                pass
        # Fallback to timeline item's first comp (when Fusion page isn't open)
        timeline: Optional[Timeline] = self.get_current_timeline()
        if timeline:
            try:
                item: Optional[TimelineItem] = timeline.GetCurrentVideoItem()
                if item:
                    comp = item.GetFusionCompByIndex(1)
                    if comp:
                        return comp
            except Exception:
                pass
        return None

    # New methods with enhanced functionality

    def get_timeline_items(self, track_type: str = "video", track_index: int = 1) -> List[TimelineItem]:
        """
        Get items (clips) from a specific track in the current timeline.
        
        Args:
            track_type (str): Type of track ("video", "audio", "subtitle"), defaults to "video".
            track_index (int): 1-based index of the track, defaults to 1.
        
        Returns:
            List[Any]: List of timeline items, empty if no timeline or track is invalid.
        """
        timeline = self.get_current_timeline()
        if not timeline:
            logger.warning("No current timeline available")
            return []
        try:
            items = timeline.GetItemListInTrack(track_type, track_index)
            return items if items else []
        except Exception as e:
            logger.error(f"Failed to get timeline items: {e}")
            return []

    def set_clip_property(self, clip: TimelineItem, property_name: str, value: Any) -> bool:
        """
        Set a property on a timeline clip (e.g., "Pan", "ZoomX").
        
        Args:
            clip: Timeline item object.
            property_name (str): Name of the property to set.
            value: Value to assign to the property.
        
        Returns:
            bool: True if successful, False if clip is invalid or property set fails.
        """
        if not clip:
            return False
        try:
            return clip.SetProperty(property_name, value)
        except Exception as e:
            logger.error(f"Failed to set clip property {property_name}: {e}")
            return False

    def get_timeline_item_offsets(self, item: TimelineItem) -> Dict[str, int]:
        """Get left/right offsets (source trim) for a timeline item."""
        if not item:
            return {}
        try:
            return {
                "left_offset": item.GetLeftOffset(),
                "right_offset": item.GetRightOffset(),
                "start": item.GetStart(),
                "end": item.GetEnd(),
                "duration": item.GetDuration(),
            }
        except Exception as e:
            logger.error(f"Failed to get item offsets: {e}")
            return {}

    def set_timeline_item_right_offset(self, item: TimelineItem, offset: int) -> Union[bool, str]:
        """Set the right offset (source out trim) for a timeline item.
        Decreasing the right offset extends the clip's end on the timeline."""
        if not item:
            return "no item"
        try:
            result = item.SetRightOffset(offset)
            return result
        except Exception as e:
            logger.error(f"Failed to set right offset: {e}")
            return f"exception: {e}"

    def set_timeline_item_left_offset(self, item: TimelineItem, offset: int) -> Union[bool, str]:
        """Set the left offset (source in trim) for a timeline item.
        Increasing the left offset trims the start of the clip."""
        if not item:
            return "no item"
        try:
            result = item.SetLeftOffset(offset)
            return result
        except Exception as e:
            logger.error(f"Failed to set left offset: {e}")
            return f"exception: {e}"

    def get_color_page_nodes(self) -> List[FusionTool]:
        """
        Get all nodes in the current clip's color grade on the Color page.
        
        Returns:
            List[Any]: List of node objects, empty if no timeline or clip is available.
        """
        timeline = self.get_current_timeline()
        if not timeline:
            return []
        clip = timeline.GetCurrentVideoItem()
        if not clip:
            logger.warning("No current clip on Color page")
            return []
        try:
            return clip.GetNodeGraph().GetNodes()
        except Exception as e:
            logger.error(f"Failed to get color nodes: {e}")
            return []

    def add_color_node(self, node_type: str = "Corrector") -> Optional[FusionTool]:
        """
        Add a new node to the current clip's color grade.
        
        Args:
            node_type (str): Type of node to add (e.g., "Corrector", "Layer"), defaults to "Corrector".
        
        Returns:
            Optional[Any]: Created node object or None if no timeline or clip is available.
        """
        timeline = self.get_current_timeline()
        if not timeline:
            return None
        clip = timeline.GetCurrentVideoItem()
        if not clip:
            return None
        try:
            node_graph = clip.GetNodeGraph()
            return node_graph.AddNode(node_type)
        except Exception as e:
            logger.error(f"Failed to add color node: {e}")
            return None

    def get_project_settings(self) -> Dict[str, Any]:
        """Get the current project's settings."""
        if not self._ensure_project():
            return {}
        try:
            return self.current_project.GetSetting()
        except Exception as e:
            logger.error(f"Failed to get project settings: {e}")
            return {}

    def set_project_setting(self, key: str, value: Any) -> bool:
        """Set a specific project setting."""
        if not self._ensure_project():
            return False
        try:
            return self.current_project.SetSetting(key, value)
        except Exception as e:
            logger.error(f"Failed to set project setting {key}: {e}")
            return False

    def start_render(self, preset_name: Optional[str] = None, render_path: Optional[str] = None) -> bool:
        """Start rendering the current project with optional preset and path."""
        if not self._ensure_project():
            return False
        try:
            if preset_name:
                self.current_project.LoadRenderPreset(preset_name)
            if render_path:
                self.current_project.SetRenderSettings({"TargetDir": render_path})
            return self.current_project.StartRendering()
        except Exception as e:
            logger.error(f"Failed to start render: {e}")
            return False

    def get_render_status(self) -> Dict[str, Any]:
        """Get the current render status of the project."""
        if not self._ensure_project():
            return {}
        try:
            return {
                "IsRenderInProgress": self.current_project.IsRenderingInProgress(),
                "CompletionPercentage": self.current_project.GetRenderingProgress()
            }
        except Exception as e:
            logger.error(f"Failed to get render status: {e}")
            return {}

    def add_timeline_marker(self, frame: int, color: str = "Blue", name: str = "", note: str = "") -> bool:
        """
        Add a marker to the current timeline at a specific frame.
        
        Args:
            frame (int): Frame number for the marker.
            color (str): Marker color (e.g., "Blue", "Red"), defaults to "Blue".
            name (str): Marker name, defaults to empty string.
            note (str): Marker note, defaults to empty string.
        
        Returns:
            bool: True if successful, False if no timeline or addition fails.
        """
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return timeline.AddMarker(frame, color, name, note, 1)  # Duration of 1 frame
        except Exception as e:
            logger.error(f"Failed to add marker: {e}")
            return False

    def get_gallery(self) -> Optional[Gallery]:
        """Get the Gallery object for the current project."""
        if not self._ensure_project():
            return None
        try:
            return self.current_project.GetGallery()
        except Exception as e:
            logger.error(f"Failed to get gallery: {e}")
            return None

    def get_gallery_albums(self) -> List[GalleryAlbum]:
        """
        Get all albums in the gallery.
        
        Returns:
            List[Any]: List of GalleryAlbum objects, empty if gallery is unavailable.
        """
        gallery = self.get_gallery()
        if not gallery:
            return []
        try:
            return gallery.GetGalleryAlbumList()
        except Exception as e:
            logger.error(f"Failed to get gallery albums: {e}")
            return []

    def save_still(self, album_name: str = "Stills") -> Optional[GalleryStill]:
        """
        Save the current clip's grade as a still in the specified gallery album.
        
        Args:
            album_name (str): Name of the album to save the still in, defaults to "Stills".
        
        Returns:
            Optional[Any]: Saved GalleryStill object or None if saving fails.
        """
        gallery = self.get_gallery()
        timeline = self.get_current_timeline()
        if not gallery or not timeline:
            return None
        clip = timeline.GetCurrentVideoItem()
        if not clip:
            logger.warning("No current clip to save still from")
            return None
        try:
            album = gallery.GetAlbum(album_name)
            if not album:
                album = gallery.CreateEmptyAlbum(album_name)  # Create album if it doesn't exist
            return clip.SaveAsStill(album)
        except Exception as e:
            logger.error(f"Failed to save still: {e}")
            return None

    def apply_still(self, still: GalleryStill, clip: Optional[TimelineItem] = None) -> bool:
        """
        Apply a still (grade) to a clip, defaulting to the current clip if none specified.
        
        Args:
            still: GalleryStill object to apply.
            clip: Timeline item to apply the still to (optional).
        
        Returns:
            bool: True if successful, False if still or clip is invalid.
        """
        if not still:
            return False
        target_clip = clip or self.get_current_timeline().GetCurrentVideoItem() if self.get_current_timeline() else None
        if not target_clip:
            logger.warning("No clip to apply still to")
            return False
        try:
            return target_clip.ApplyGradeFromStill(still)
        except Exception as e:
            logger.error(f"Failed to apply still: {e}")
            return False

    def add_track(self, track_type: str = "video") -> bool:
        """
        Add a new track to the current timeline.
        
        Args:
            track_type (str): Type of track to add ("video", "audio", "subtitle"), defaults to "video".
        
        Returns:
            bool: True if successful, False if no timeline or addition fails.
        """
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return timeline.AddTrack(track_type)
        except Exception as e:
            logger.error(f"Failed to add {track_type} track: {e}")
            return False

    def set_track_name(self, track_type: str, track_index: int, name: str) -> bool:
        """
        Set the name of a track in the current timeline.
        
        Args:
            track_type (str): Type of track ("video", "audio", "subtitle").
            track_index (int): 1-based index of the track.
            name (str): New name for the track.
        
        Returns:
            bool: True if successful, False if no timeline or naming fails.
        """
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return timeline.SetTrackName(track_type, track_index, name)
        except Exception as e:
            logger.error(f"Failed to set track name: {e}")
            return False

    def enable_track(self, track_type: str, track_index: int, enable: bool = True) -> bool:
        """
        Enable or disable a track in the current timeline.
        
        Args:
            track_type (str): Type of track ("video", "audio", "subtitle").
            track_index (int): 1-based index of the track.
            enable (bool): True to enable, False to disable, defaults to True.
        
        Returns:
            bool: True if successful, False if no timeline or enabling fails.
        """
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return timeline.SetTrackEnable(track_type, track_index, enable)
        except Exception as e:
            logger.error(f"Failed to set track enable state: {e}")
            return False

    def get_audio_volume(self, clip: TimelineItem) -> Optional[float]:
        """
        Get the audio volume of a timeline clip.
        
        Args:
            clip: Timeline item with audio.
        
        Returns:
            Optional[float]: Volume level (e.g., 0.0 to 1.0) or None if clip is invalid.
        """
        if not clip:
            return None
        try:
            return clip.GetAudioVolume()
        except Exception as e:
            logger.error(f"Failed to get audio volume: {e}")
            return None

    def set_audio_volume(self, clip: TimelineItem, volume: float) -> bool:
        """
        Set the audio volume of a timeline clip.
        
        Args:
            clip: Timeline item with audio.
            volume (float): Volume level to set (e.g., 0.0 to 1.0).
        
        Returns:
            bool: True if successful, False if clip is invalid or setting fails.
        """
        if not clip:
            return False
        try:
            return clip.SetAudioVolume(volume)
        except Exception as e:
            logger.error(f"Failed to set audio volume: {e}")
            return False

    def set_track_volume(self, track_index: int, volume: float) -> bool:
        """
        Set the volume of an audio track in the current timeline.
        
        Args:
            track_index (int): 1-based index of the audio track.
            volume (float): Volume level to set (e.g., 0.0 to 1.0).
        
        Returns:
            bool: True if successful, False if no timeline or setting fails.
        """
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return timeline.SetTrackVolume("audio", track_index, volume)
        except Exception as e:
            logger.error(f"Failed to set track volume: {e}")
            return False

    def get_version_count(self, clip: TimelineItem, version_type: str = "color") -> int:
        """
        Get the number of versions (e.g., color grades) for a clip.
        
        Args:
            clip: Timeline item.
            version_type (str): Type of version ("color" or "fusion"), defaults to "color".
        
        Returns:
            int: Number of versions, 0 if clip is invalid.
        """
        if not clip:
            return 0
        try:
            return clip.GetVersionCount(version_type)
        except Exception as e:
            logger.error(f"Failed to get version count: {e}")
            return 0

    def set_current_version(self, clip: TimelineItem, version_index: int, version_type: str = "color") -> bool:
        """
        Set the current version for a clip (e.g., switch between color grades).
        
        Args:
            clip: Timeline item.
            version_index (int): 0-based index of the version to set.
            version_type (str): Type of version ("color" or "fusion"), defaults to "color".
        
        Returns:
            bool: True if successful, False if clip is invalid or setting fails.
        """
        if not clip:
            return False
        try:
            return clip.SetCurrentVersion(version_index, version_type)
        except Exception as e:
            logger.error(f"Failed to set current version: {e}")
            return False

    def play(self) -> bool:
        """Start playback in DaVinci Resolve."""
        if not self.resolve:
            self.refresh()
        if not self.resolve:
            return False
        try:
            self.resolve.Play()
            return True
        except Exception as e:
            logger.error(f"Failed to start playback: {e}")
            return False

    def stop(self) -> bool:
        """Stop playback in DaVinci Resolve."""
        if not self.resolve:
            self.refresh()
        if not self.resolve:
            return False
        try:
            self.resolve.Stop()
            return True
        except Exception as e:
            logger.error(f"Failed to stop playback: {e}")
            return False

    def get_current_timecode(self) -> Optional[str]:
        """Get the current playback timecode."""
        if not self.resolve:
            self.refresh()
        if not self.resolve:
            return None
        try:
            return self.resolve.GetCurrentTimecode()
        except Exception as e:
            logger.error(f"Failed to get current timecode: {e}")
            return None

    def set_playhead_position(self, frame: int) -> bool:
        """
        Set the playhead position to a specific frame in the current timeline.

        Args:
            frame (int): Frame number to set the playhead to.

        Returns:
            bool: True if successful, False if no timeline or setting fails.
        """
        timeline = self.get_current_timeline()
        if not timeline:
            self._playhead_debug = "no current timeline"
            return False
        try:
            has_set_tc = callable(getattr(timeline, 'SetCurrentTimecode', None))
            if not has_set_tc:
                self._playhead_debug = "SetCurrentTimecode not available on timeline proxy"
                return False
            # Try native GetTimecodeFromFrame if available
            tc: Optional[str] = None
            get_tc_fn = getattr(timeline, 'GetTimecodeFromFrame', None)
            if callable(get_tc_fn):
                tc = get_tc_fn(frame)
                if tc:
                    result = timeline.SetCurrentTimecode(tc)
                    if result:
                        return True
            # Compute timecode manually from frame number
            get_setting_fn = getattr(timeline, 'GetSetting', None)
            fps = float(get_setting_fn("timelineFrameRate") or 24) if callable(get_setting_fn) else 24.0
            fps_int = round(fps)
            total_frames = int(frame)
            h = total_frames // (3600 * fps_int)
            remainder = total_frames % (3600 * fps_int)
            m = remainder // (60 * fps_int)
            remainder = remainder % (60 * fps_int)
            s = remainder // fps_int
            f = remainder % fps_int
            tc_str = f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"
            result2 = timeline.SetCurrentTimecode(tc_str)
            if not result2:
                self._playhead_debug = f"native_tc={tc!r} fallback_tc={tc_str!r} fps={fps} start_tc={timeline.GetStartTimecode()!r} current_tc={timeline.GetCurrentTimecode()!r}"
            return result2
        except Exception as e:
            self._playhead_debug = f"exception: {e}"
            return False

    def export_project(self, project_name: str, file_path: str) -> bool:
        """Export a project to a file (e.g., .drp file)."""
        if not self.project_manager:
            self.refresh()
        if not self.project_manager:
            return False
        try:
            return self.project_manager.ExportProject(project_name, file_path)
        except Exception as e:
            logger.error(f"Failed to export project: {e}")
            return False

    def import_project(self, file_path: str) -> bool:
        """Import a project from a file (e.g., .drp file)."""
        if not self.project_manager:
            self.refresh()
        if not self.project_manager:
            return False
        try:
            return self.project_manager.ImportProject(file_path)
        except Exception as e:
            logger.error(f"Failed to import project: {e}")
            return False

    # ─── Tier 1: Titles, Generators, Render, Export, Duplicate, Compound ───

    def insert_title(self, title_name: str) -> bool:
        """Insert a title (text) into the current timeline at the playhead."""
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return bool(timeline.InsertTitleIntoTimeline(title_name))
        except Exception as e:
            logger.error(f"Failed to insert title '{title_name}': {e}")
            return False

    def insert_fusion_title(self, title_name: str) -> bool:
        """Insert a Fusion-based title into the current timeline."""
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return bool(timeline.InsertFusionTitleIntoTimeline(title_name))
        except Exception as e:
            logger.error(f"Failed to insert Fusion title '{title_name}': {e}")
            return False

    def insert_generator(self, generator_name: str) -> bool:
        """Insert a generator (solid color, gradient, etc.) into the timeline."""
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return bool(timeline.InsertGeneratorIntoTimeline(generator_name))
        except Exception as e:
            logger.error(f"Failed to insert generator '{generator_name}': {e}")
            return False

    def insert_fusion_generator(self, generator_name: str) -> bool:
        """Insert a Fusion generator into the timeline."""
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return bool(timeline.InsertFusionGeneratorIntoTimeline(generator_name))
        except Exception as e:
            logger.error(f"Failed to insert Fusion generator '{generator_name}': {e}")
            return False

    def duplicate_timeline(self, new_name: Optional[str] = None) -> Optional[Timeline]:
        """Duplicate the current timeline. Returns the new timeline object."""
        timeline = self.get_current_timeline()
        if not timeline:
            return None
        try:
            dup_name = new_name or f"{timeline.GetName()} (copy)"
            return timeline.DuplicateTimeline(dup_name)
        except Exception as e:
            logger.error(f"Failed to duplicate timeline: {e}")
            return None

    def create_compound_clip(self, items: List[TimelineItem], clip_info: Optional[Dict[str, Any]] = None) -> bool:
        """Create a compound clip from timeline items."""
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return bool(timeline.CreateCompoundClip(items, clip_info or {}))
        except Exception as e:
            logger.error(f"Failed to create compound clip: {e}")
            return False

    def export_timeline(self, file_path: str, export_type: str, export_subtype: Optional[str] = None) -> bool:
        """Export the current timeline to a file (EDL, XML, AAF, etc.)."""
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            if export_subtype:
                return bool(timeline.Export(file_path, export_type, export_subtype))
            return bool(timeline.Export(file_path, export_type))
        except Exception as e:
            logger.error(f"Failed to export timeline: {e}")
            return False

    def get_timeline_setting(self, setting_name: str) -> Optional[str]:
        """Get a specific timeline setting."""
        timeline = self.get_current_timeline()
        if not timeline:
            return None
        try:
            return timeline.GetSetting(setting_name)
        except Exception as e:
            logger.error(f"Failed to get timeline setting '{setting_name}': {e}")
            return None

    def set_timeline_setting(self, setting_name: str, value: Any) -> bool:
        """Set a specific timeline setting."""
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return bool(timeline.SetSetting(setting_name, value))
        except Exception as e:
            logger.error(f"Failed to set timeline setting: {e}")
            return False

    # Render pipeline
    def add_render_job(self) -> str:
        """Add a render job based on current render settings. Returns job ID."""
        if not self._ensure_project():
            return ""
        try:
            return self.current_project.AddRenderJob() or ""
        except Exception as e:
            logger.error(f"Failed to add render job: {e}")
            return ""

    def delete_render_job(self, job_id: str) -> bool:
        """Delete a render job by ID."""
        if not self._ensure_project():
            return False
        try:
            return bool(self.current_project.DeleteRenderJob(job_id))
        except Exception as e:
            logger.error(f"Failed to delete render job: {e}")
            return False

    def delete_all_render_jobs(self) -> bool:
        """Delete all render jobs."""
        if not self._ensure_project():
            return False
        try:
            return bool(self.current_project.DeleteAllRenderJobs())
        except Exception as e:
            logger.error(f"Failed to delete all render jobs: {e}")
            return False

    def get_render_job_list(self) -> List[Dict[str, Any]]:
        """Get list of all render jobs with details."""
        if not self._ensure_project():
            return []
        try:
            return self.current_project.GetRenderJobList() or []
        except Exception as e:
            logger.error(f"Failed to get render job list: {e}")
            return []

    def get_render_preset_list(self) -> List[str]:
        """Get list of available render presets."""
        if not self._ensure_project():
            return []
        try:
            return self.current_project.GetRenderPresetList() or []
        except Exception as e:
            logger.error(f"Failed to get render presets: {e}")
            return []

    def load_render_preset(self, preset_name: str) -> bool:
        """Load a render preset by name."""
        if not self._ensure_project():
            return False
        try:
            return bool(self.current_project.LoadRenderPreset(preset_name))
        except Exception as e:
            logger.error(f"Failed to load render preset '{preset_name}': {e}")
            return False

    def set_render_settings(self, settings: Dict[str, Any]) -> bool:
        """Set render settings from a dict (e.g., TargetDir, CustomName, etc.)."""
        if not self._ensure_project():
            return False
        try:
            return bool(self.current_project.SetRenderSettings(settings))
        except Exception as e:
            logger.error(f"Failed to set render settings: {e}")
            return False

    def get_render_formats(self) -> Dict[str, str]:
        """Get supported render formats."""
        if not self._ensure_project():
            return {}
        try:
            return self.current_project.GetRenderFormats() or {}
        except Exception as e:
            logger.error(f"Failed to get render formats: {e}")
            return {}

    def get_render_codecs(self, render_format: str) -> Dict[str, str]:
        """Get codecs available for a render format."""
        if not self._ensure_project():
            return {}
        try:
            return self.current_project.GetRenderCodecs(render_format) or {}
        except Exception as e:
            logger.error(f"Failed to get render codecs: {e}")
            return {}

    def set_render_format_and_codec(self, fmt: str, codec: str) -> bool:
        """Set the render format and codec."""
        if not self._ensure_project():
            return False
        try:
            return bool(self.current_project.SetCurrentRenderFormatAndCodec(fmt, codec))
        except Exception as e:
            logger.error(f"Failed to set render format/codec: {e}")
            return False

    def get_render_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a specific render job."""
        if not self._ensure_project():
            return {}
        try:
            return self.current_project.GetRenderJobStatus(job_id) or {}
        except Exception as e:
            logger.error(f"Failed to get render job status: {e}")
            return {}

    def stop_rendering(self) -> bool:
        """Stop any active rendering."""
        if not self._ensure_project():
            return False
        try:
            self.current_project.StopRendering()
            return True
        except Exception as e:
            logger.error(f"Failed to stop rendering: {e}")
            return False

    def is_rendering(self) -> bool:
        """Check if rendering is in progress."""
        if not self._ensure_project():
            return False
        try:
            return bool(self.current_project.IsRenderingInProgress())
        except Exception as e:
            return False

    # ─── Tier 2: Color & Grading ───

    def set_lut(self, item: TimelineItem, node_index: int, lut_path: str) -> bool:
        """Apply a LUT to a specific node of a timeline item."""
        if not item:
            return False
        try:
            return bool(item.SetLUT(node_index, lut_path))
        except Exception as e:
            logger.error(f"Failed to set LUT: {e}")
            return False

    def set_cdl(self, item: TimelineItem, cdl_map: Dict[str, Any]) -> bool:
        """Apply CDL (Color Decision List) values to a timeline item."""
        if not item:
            return False
        try:
            return bool(item.SetCDL(cdl_map))
        except Exception as e:
            logger.error(f"Failed to set CDL: {e}")
            return False

    def copy_grades(self, source_item: TimelineItem, target_items: List[TimelineItem]) -> bool:
        """Copy color grades from source to target timeline items."""
        if not source_item or not target_items:
            return False
        try:
            return bool(source_item.CopyGrades(target_items))
        except Exception as e:
            logger.error(f"Failed to copy grades: {e}")
            return False

    def apply_grade_from_drx(self, drx_path: str, grade_mode: int, items: List[TimelineItem]) -> bool:
        """Apply color grade from a DRX file to timeline items.
        grade_mode: 0=No keyframes, 1=Source timecode aligned, 2=Start frames aligned."""
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return bool(timeline.ApplyGradeFromDRX(drx_path, grade_mode, items))
        except Exception as e:
            logger.error(f"Failed to apply grade from DRX: {e}")
            return False

    def export_stills(self, stills: List[GalleryStill], folder_path: str, file_prefix: str = "still", fmt: str = "dpx") -> bool:
        """Export gallery stills to disk."""
        gallery = self.get_gallery()
        if not gallery:
            return False
        try:
            album = gallery.GetCurrentStillAlbum()
            if not album:
                return False
            return bool(album.ExportStills(stills, folder_path, file_prefix, fmt))
        except Exception as e:
            logger.error(f"Failed to export stills: {e}")
            return False

    def refresh_lut_list(self) -> bool:
        """Refresh the LUT list in the project."""
        if not self._ensure_project():
            return False
        try:
            return bool(self.current_project.RefreshLUTList())
        except Exception as e:
            logger.error(f"Failed to refresh LUT list: {e}")
            return False

    # ─── Tier 3: Organization & Metadata ───

    def get_clip_metadata(self, clip: MediaPoolItem, key: Optional[str] = None) -> Union[Dict[str, str], Optional[str]]:
        """Get metadata for a media pool item. If key is None, returns all metadata."""
        if not clip:
            return {} if key is None else None
        try:
            if key:
                return clip.GetMetadata(key)
            return clip.GetMetadata() or {}
        except Exception as e:
            logger.error(f"Failed to get clip metadata: {e}")
            return {} if key is None else None

    def set_clip_metadata(self, clip: MediaPoolItem, metadata: Dict[str, str]) -> bool:
        """Set metadata on a media pool item (dict of key-value pairs)."""
        if not clip:
            return False
        try:
            return bool(clip.SetMetadata(metadata))
        except Exception as e:
            logger.error(f"Failed to set clip metadata: {e}")
            return False

    def add_clip_marker(self, clip: MediaPoolItem, frame: int, color: str, name: str = "", note: str = "", duration: int = 1, custom_data: str = "") -> bool:
        """Add a marker to a media pool clip."""
        if not clip:
            return False
        try:
            return bool(clip.AddMarker(frame, color, name, note, duration, custom_data))
        except Exception as e:
            logger.error(f"Failed to add clip marker: {e}")
            return False

    def get_clip_markers(self, clip: MediaPoolItem) -> Dict[int, Dict[str, Any]]:
        """Get all markers on a media pool clip."""
        if not clip:
            return {}
        try:
            return clip.GetMarkers() or {}
        except Exception as e:
            logger.error(f"Failed to get clip markers: {e}")
            return {}

    def get_timeline_markers(self) -> Dict[int, Dict[str, Any]]:
        """Get all markers on the current timeline."""
        timeline = self.get_current_timeline()
        if not timeline:
            return {}
        try:
            return timeline.GetMarkers() or {}
        except Exception as e:
            logger.error(f"Failed to get timeline markers: {e}")
            return {}

    def delete_timeline_markers_by_color(self, color: str) -> bool:
        """Delete all timeline markers of a given color. Use 'All' to delete all."""
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return bool(timeline.DeleteMarkersByColor(color))
        except Exception as e:
            logger.error(f"Failed to delete markers: {e}")
            return False

    def set_clip_color(self, item: TimelineItem, color: str) -> bool:
        """Set the color label on a timeline item."""
        if not item:
            return False
        try:
            return bool(item.SetClipColor(color))
        except Exception as e:
            logger.error(f"Failed to set clip color: {e}")
            return False

    def add_flag(self, item: TimelineItem, color: str) -> bool:
        """Add a flag to a timeline item."""
        if not item:
            return False
        try:
            return bool(item.AddFlag(color))
        except Exception as e:
            logger.error(f"Failed to add flag: {e}")
            return False

    def get_flag_list(self, item: TimelineItem) -> List[str]:
        """Get list of flags on a timeline item."""
        if not item:
            return []
        try:
            return item.GetFlagList() or []
        except Exception as e:
            logger.error(f"Failed to get flag list: {e}")
            return []

    def relink_clips(self, clips: List[MediaPoolItem], folder_path: str) -> bool:
        """Relink media pool clips to a new folder path."""
        if not self._ensure_media_pool():
            return False
        try:
            return bool(self.media_pool.RelinkClips(clips, folder_path))
        except Exception as e:
            logger.error(f"Failed to relink clips: {e}")
            return False

    def delete_clips(self, clips: List[MediaPoolItem]) -> bool:
        """Delete clips from the media pool."""
        if not self._ensure_media_pool():
            return False
        try:
            return bool(self.media_pool.DeleteClips(clips))
        except Exception as e:
            logger.error(f"Failed to delete clips: {e}")
            return False

    def delete_folders(self, folders: List[MediaPoolFolder]) -> bool:
        """Delete folders from the media pool."""
        if not self._ensure_media_pool():
            return False
        try:
            return bool(self.media_pool.DeleteFolders(folders))
        except Exception as e:
            logger.error(f"Failed to delete folders: {e}")
            return False

    def export_metadata(self, file_name: str, clips: Optional[List[MediaPoolItem]] = None) -> bool:
        """Export clip metadata to CSV."""
        if not self._ensure_media_pool():
            return False
        try:
            if clips:
                return bool(self.media_pool.ExportMetadata(file_name, clips))
            return bool(self.media_pool.ExportMetadata(file_name))
        except Exception as e:
            logger.error(f"Failed to export metadata: {e}")
            return False

    # Takes system
    def add_take(self, item: TimelineItem, media_pool_item: MediaPoolItem, start_frame: Optional[int] = None, end_frame: Optional[int] = None) -> bool:
        """Add an alternate take to a timeline item."""
        if not item or not media_pool_item:
            return False
        try:
            if start_frame is not None and end_frame is not None:
                return bool(item.AddTake(media_pool_item, start_frame, end_frame))
            return bool(item.AddTake(media_pool_item))
        except Exception as e:
            logger.error(f"Failed to add take: {e}")
            return False

    def get_takes_count(self, item: TimelineItem) -> int:
        """Get number of takes for a timeline item."""
        if not item:
            return 0
        try:
            return item.GetTakesCount() or 0
        except Exception as e:
            return 0

    def select_take(self, item: TimelineItem, take_index: int) -> bool:
        """Select a take by index on a timeline item."""
        if not item:
            return False
        try:
            return bool(item.SelectTakeByIndex(take_index))
        except Exception as e:
            logger.error(f"Failed to select take: {e}")
            return False

    def finalize_take(self, item: TimelineItem) -> bool:
        """Finalize the selected take on a timeline item."""
        if not item:
            return False
        try:
            return bool(item.FinalizeTake())
        except Exception as e:
            logger.error(f"Failed to finalize take: {e}")
            return False

    # ─── Tier 4: Fusion & Advanced ───

    def create_fusion_clip(self, items: List[TimelineItem]) -> bool:
        """Create a Fusion clip from timeline items."""
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return bool(timeline.CreateFusionClip(items))
        except Exception as e:
            logger.error(f"Failed to create Fusion clip: {e}")
            return False

    def add_fusion_comp(self, item: TimelineItem) -> bool:
        """Add a new Fusion composition to a timeline item."""
        if not item:
            return False
        try:
            return bool(item.AddFusionComp())
        except Exception as e:
            logger.error(f"Failed to add Fusion comp: {e}")
            return False

    def import_fusion_comp(self, item: TimelineItem, path: str) -> bool:
        """Import a Fusion composition from file to a timeline item."""
        if not item:
            return False
        try:
            return bool(item.ImportFusionComp(path))
        except Exception as e:
            logger.error(f"Failed to import Fusion comp: {e}")
            return False

    def export_fusion_comp(self, item: TimelineItem, path: str, comp_index: int = 1) -> bool:
        """Export a Fusion composition from a timeline item to file."""
        if not item:
            return False
        try:
            return bool(item.ExportFusionComp(path, comp_index))
        except Exception as e:
            logger.error(f"Failed to export Fusion comp: {e}")
            return False

    def get_fusion_comp_names(self, item: TimelineItem) -> List[str]:
        """Get list of Fusion composition names on a timeline item."""
        if not item:
            return []
        try:
            return item.GetFusionCompNameList() or []
        except Exception as e:
            return []

    def grab_still(self) -> Optional[GalleryStill]:
        """Grab a still from the current frame to the gallery."""
        timeline = self.get_current_timeline()
        if not timeline:
            return None
        try:
            return timeline.GrabStill()
        except Exception as e:
            logger.error(f"Failed to grab still: {e}")
            return None

    def grab_all_stills(self, still_frame_source: int = 2) -> bool:
        """Grab stills from all clips. source: 1=first frame, 2=middle frame."""
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return bool(timeline.GrabAllStills(still_frame_source))
        except Exception as e:
            logger.error(f"Failed to grab all stills: {e}")
            return False

    def insert_fusion_composition(self) -> bool:
        """Insert a Fusion composition at the playhead."""
        timeline = self.get_current_timeline()
        if not timeline:
            return False
        try:
            return bool(timeline.InsertFusionCompositionIntoTimeline())
        except Exception as e:
            logger.error(f"Failed to insert Fusion composition: {e}")
            return False

    def get_track_count(self, track_type: str = "video") -> int:
        """Get number of tracks of a given type."""
        timeline = self.get_current_timeline()
        if not timeline:
            return 0
        try:
            return timeline.GetTrackCount(track_type) or 0
        except Exception as e:
            return 0

    def get_current_video_item(self) -> Optional[TimelineItem]:
        """Get the current video item under the playhead."""
        timeline = self.get_current_timeline()
        if not timeline:
            return None
        try:
            return timeline.GetCurrentVideoItem()
        except Exception as e:
            return None
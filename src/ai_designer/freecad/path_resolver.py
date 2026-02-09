"""
FreeCAD Path Resolution Module

Provides centralized, portable path resolution for FreeCAD installations.
Supports multiple installation types:
- AppImage (.AppImage files)
- System packages (apt, dnf, pacman)
- Custom installations
- Conda environments

Path resolution order:
1. FREECAD_PATH environment variable
2. config.yaml configuration
3. Auto-detection from common install locations
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FreeCADPathError(Exception):
    """Raised when FreeCAD paths cannot be resolved"""

    pass


class FreeCADPathResolver:
    """
    Centralized FreeCAD path resolution.

    Handles detection and configuration of FreeCAD installation paths
    across different installation methods and operating systems.
    """

    # Common FreeCAD installation locations by OS
    COMMON_PATHS = {
        "linux": [
            "/usr/lib/freecad",
            "/usr/lib64/freecad",
            "/usr/local/lib/freecad",
            "/opt/freecad",
            "/snap/freecad/current/usr/lib",
            "~/Downloads",  # AppImage location
            "~/Applications",  # AppImage location
        ],
        "darwin": [  # macOS
            "/Applications/FreeCAD.app/Contents/Resources/lib",
            "~/Applications/FreeCAD.app/Contents/Resources/lib",
        ],
        "windows": [
            r"C:\Program Files\FreeCAD\bin",
            r"C:\Program Files (x86)\FreeCAD\bin",
        ],
    }

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize path resolver.

        Args:
            config: Optional configuration dictionary from config.yaml
        """
        self.config = config or {}
        self._resolved_paths: Optional[Tuple[str, str]] = None

    def resolve_paths(self) -> Tuple[str, str]:
        """
        Resolve FreeCAD library and module paths.

        Returns:
            Tuple of (lib_path, mod_path)

        Raises:
            FreeCADPathError: If paths cannot be resolved
        """
        if self._resolved_paths:
            return self._resolved_paths

        # Try resolution in order of priority
        paths = (
            self._from_environment()
            or self._from_config()
            or self._from_appimage()
            or self._from_system_install()
        )

        if not paths:
            raise FreeCADPathError(
                "Could not locate FreeCAD installation. "
                "Please set FREECAD_PATH environment variable or "
                "configure freecad.appimage_path in config.yaml"
            )

        self._resolved_paths = paths
        logger.info(f"Resolved FreeCAD paths - lib: {paths[0]}, mod: {paths[1]}")
        return paths

    def _from_environment(self) -> Optional[Tuple[str, str]]:
        """Try to resolve from FREECAD_PATH environment variable"""
        freecad_path = os.getenv("FREECAD_PATH")
        if not freecad_path:
            return None

        path = Path(freecad_path).expanduser()

        # Handle AppImage
        if path.suffix == ".AppImage" and path.exists():
            return self._extract_appimage_paths(str(path))

        # Handle directory path
        if path.is_dir():
            lib_path = path / "lib"
            mod_path = path / "Mod"
            if lib_path.exists() and mod_path.exists():
                return (str(lib_path), str(mod_path))

        logger.warning(f"FREECAD_PATH set but invalid: {freecad_path}")
        return None

    def _from_config(self) -> Optional[Tuple[str, str]]:
        """Try to resolve from config.yaml"""
        freecad_config = self.config.get("freecad", {})

        # Check if explicit lib/mod paths are set
        lib_path = freecad_config.get("lib_path")
        mod_path = freecad_config.get("mod_path")
        if lib_path and mod_path:
            lib_path = Path(lib_path).expanduser()
            mod_path = Path(mod_path).expanduser()
            if lib_path.exists() and mod_path.exists():
                return (str(lib_path), str(mod_path))

        # Check for AppImage path in config
        appimage_path = freecad_config.get("appimage_path")
        if appimage_path:
            appimage_path = Path(appimage_path).expanduser()
            if appimage_path.exists() and appimage_path.suffix == ".AppImage":
                return self._extract_appimage_paths(str(appimage_path))

        return None

    def _from_appimage(self) -> Optional[Tuple[str, str]]:
        """Auto-detect AppImage in common locations"""
        search_dirs = [
            Path.home() / "Downloads",
            Path.home() / "Applications",
            Path.cwd(),
        ]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            # Look for FreeCAD*.AppImage files
            for appimage in search_dir.glob("FreeCAD*.AppImage"):
                if appimage.exists():
                    logger.info(f"Found FreeCAD AppImage: {appimage}")
                    return self._extract_appimage_paths(str(appimage))

        return None

    def _from_system_install(self) -> Optional[Tuple[str, str]]:
        """Auto-detect system FreeCAD installation"""
        # Determine OS
        if sys.platform.startswith("linux"):
            platform = "linux"
        elif sys.platform == "darwin":
            platform = "darwin"
        elif sys.platform == "win32":
            platform = "windows"
        else:
            return None

        # Check common paths for this platform
        for base_path in self.COMMON_PATHS.get(platform, []):
            base_path = Path(base_path).expanduser()
            if not base_path.exists():
                continue

            # Try standard structure
            lib_path = base_path / "lib"
            mod_path = base_path / "Mod"
            if lib_path.exists() and mod_path.exists():
                logger.info(f"Found system FreeCAD installation: {base_path}")
                return (str(lib_path), str(mod_path))

            # Try alternate structure (some distros)
            if (base_path / "freecad").exists():
                lib_path = base_path / "freecad" / "lib"
                mod_path = base_path / "freecad" / "Mod"
                if lib_path.exists() and mod_path.exists():
                    return (str(lib_path), str(mod_path))

        return None

    def _extract_appimage_paths(self, appimage_path: str) -> Optional[Tuple[str, str]]:
        """
        Extract lib and Mod paths from AppImage.

        For AppImages, we need to mount them to access the internal structure.
        In practice, when using AppImage with --appimage-extract-and-run or
        subprocess execution, we rely on FreeCAD's internal path resolution.

        Args:
            appimage_path: Path to the .AppImage file

        Returns:
            Tuple of (lib_path, mod_path) or None if extraction fails
        """
        # For AppImages, we return a marker that indicates AppImage usage
        # The actual paths are resolved internally by FreeCAD when executed
        appimage = Path(appimage_path)
        if not appimage.exists():
            return None

        # Store the AppImage path for subprocess execution
        # Actual lib/Mod paths are inside the squashfs image
        # We'll use the AppImage directly for execution
        return (f"appimage:{appimage}", f"appimage:{appimage}")

    def setup_sys_path(self) -> None:
        """
        Configure sys.path with FreeCAD paths.

        Should be called before importing FreeCAD modules.
        """
        try:
            lib_path, mod_path = self.resolve_paths()

            # Handle AppImage marker
            if lib_path.startswith("appimage:"):
                # For AppImage, we don't modify sys.path
                # FreeCAD executable handles this internally
                logger.info("Using AppImage - path setup handled by FreeCAD")
                return

            # Add paths to sys.path if not already present
            for path in [lib_path, mod_path]:
                if path not in sys.path:
                    sys.path.insert(0, path)
                    logger.debug(f"Added to sys.path: {path}")

        except FreeCADPathError as e:
            logger.error(f"Failed to setup FreeCAD paths: {e}")
            raise

    def get_executable_path(self) -> str:
        """
        Get path to FreeCAD executable for subprocess execution.

        Returns:
            Path to freecadcmd or AppImage

        Raises:
            FreeCADPathError: If executable cannot be found
        """
        # Check environment variable first
        freecad_path = os.getenv("FREECAD_PATH")
        if freecad_path:
            path = Path(freecad_path).expanduser()
            if path.exists():
                if path.suffix == ".AppImage":
                    return str(path)
                elif path.is_dir():
                    # Look for freecadcmd in bin/
                    freecadcmd = path / "bin" / "freecadcmd"
                    if freecadcmd.exists():
                        return str(freecadcmd)

        # Check config
        freecad_config = self.config.get("freecad", {})
        appimage_path = freecad_config.get("appimage_path")
        if appimage_path:
            path = Path(appimage_path).expanduser()
            if path.exists() and path.suffix == ".AppImage":
                return str(path)

        # Try to find AppImage
        appimage_paths = self._from_appimage()
        if appimage_paths:
            appimage_marker = appimage_paths[0]
            if appimage_marker.startswith("appimage:"):
                return appimage_marker.replace("appimage:", "")

        # Fall back to system freecadcmd
        import shutil

        freecadcmd = shutil.which("freecadcmd")
        if freecadcmd:
            return freecadcmd

        raise FreeCADPathError(
            "Could not locate FreeCAD executable. "
            "Please set FREECAD_PATH or install FreeCAD system-wide."
        )


# Global resolver instance
_resolver: Optional[FreeCADPathResolver] = None


def get_resolver(config: Optional[Dict] = None) -> FreeCADPathResolver:
    """
    Get or create the global FreeCAD path resolver.

    Args:
        config: Optional configuration dictionary

    Returns:
        FreeCADPathResolver instance
    """
    global _resolver
    if _resolver is None or config is not None:
        _resolver = FreeCADPathResolver(config)
    return _resolver


def setup_freecad_paths(config: Optional[Dict] = None) -> None:
    """
    Convenience function to setup FreeCAD paths.

    Args:
        config: Optional configuration dictionary

    Raises:
        FreeCADPathError: If paths cannot be resolved
    """
    resolver = get_resolver(config)
    resolver.setup_sys_path()


def get_freecad_executable(config: Optional[Dict] = None) -> str:
    """
    Convenience function to get FreeCAD executable path.

    Args:
        config: Optional configuration dictionary

    Returns:
        Path to FreeCAD executable

    Raises:
        FreeCADPathError: If executable cannot be found
    """
    resolver = get_resolver(config)
    return resolver.get_executable_path()

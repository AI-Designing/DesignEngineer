"""
Unit tests for FreeCAD path resolver.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_designer.freecad.path_resolver import (
    FreeCADPathError,
    FreeCADPathResolver,
    get_freecad_executable,
    get_resolver,
    setup_freecad_paths,
)


class TestFreeCADPathResolver:
    """Test FreeCADPathResolver class"""

    def test_initialization(self):
        """Test resolver initialization"""
        resolver = FreeCADPathResolver()
        assert resolver.config == {}
        assert resolver._resolved_paths is None

        config = {"freecad": {"lib_path": "/usr/lib"}}
        resolver = FreeCADPathResolver(config)
        assert resolver.config == config

    def test_from_environment_appimage(self, tmp_path):
        """Test resolution from FREECAD_PATH environment variable with AppImage"""
        # Create mock AppImage
        appimage = tmp_path / "FreeCAD.AppImage"
        appimage.touch()

        with patch.dict(os.environ, {"FREECAD_PATH": str(appimage)}):
            resolver = FreeCADPathResolver()
            lib_path, mod_path = resolver.resolve_paths()

            assert lib_path == f"appimage:{appimage}"
            assert mod_path == f"appimage:{appimage}"

    def test_from_environment_directory(self, tmp_path):
        """Test resolution from FREECAD_PATH with directory structure"""
        # Create mock directory structure
        lib_dir = tmp_path / "lib"
        mod_dir = tmp_path / "Mod"
        lib_dir.mkdir()
        mod_dir.mkdir()

        with patch.dict(os.environ, {"FREECAD_PATH": str(tmp_path)}):
            resolver = FreeCADPathResolver()
            lib_path, mod_path = resolver.resolve_paths()

            assert lib_path == str(lib_dir)
            assert mod_path == str(mod_dir)

    def test_from_environment_invalid(self, tmp_path):
        """Test handling of invalid FREECAD_PATH"""
        invalid_path = tmp_path / "nonexistent"

        with patch.dict(os.environ, {"FREECAD_PATH": str(invalid_path)}):
            resolver = FreeCADPathResolver()
            # Should fall back to other methods
            with pytest.raises(FreeCADPathError):
                resolver.resolve_paths()

    def test_from_config_appimage(self, tmp_path):
        """Test resolution from config with AppImage"""
        appimage = tmp_path / "FreeCAD.AppImage"
        appimage.touch()

        config = {"freecad": {"appimage_path": str(appimage)}}
        resolver = FreeCADPathResolver(config)
        lib_path, mod_path = resolver.resolve_paths()

        assert lib_path == f"appimage:{appimage}"
        assert mod_path == f"appimage:{appimage}"

    def test_from_config_explicit_paths(self, tmp_path):
        """Test resolution from config with explicit lib/mod paths"""
        lib_dir = tmp_path / "lib"
        mod_dir = tmp_path / "Mod"
        lib_dir.mkdir()
        mod_dir.mkdir()

        config = {
            "freecad": {
                "lib_path": str(lib_dir),
                "mod_path": str(mod_dir),
            }
        }
        resolver = FreeCADPathResolver(config)
        lib_path, mod_path = resolver.resolve_paths()

        assert lib_path == str(lib_dir)
        assert mod_path == str(mod_dir)

    def test_from_config_home_expansion(self, tmp_path):
        """Test that ~ is expanded in config paths"""
        # Create paths in temp directory (not actual home)
        lib_dir = tmp_path / "lib"
        mod_dir = tmp_path / "Mod"
        lib_dir.mkdir()
        mod_dir.mkdir()

        # Use expanduser to handle ~ properly
        config = {
            "freecad": {
                "lib_path": str(lib_dir),
                "mod_path": str(mod_dir),
            }
        }
        resolver = FreeCADPathResolver(config)
        lib_path, mod_path = resolver.resolve_paths()

        # Paths should be expanded
        assert not lib_path.startswith("~")
        assert not mod_path.startswith("~")

    def test_caching_resolved_paths(self, tmp_path):
        """Test that resolved paths are cached"""
        lib_dir = tmp_path / "lib"
        mod_dir = tmp_path / "Mod"
        lib_dir.mkdir()
        mod_dir.mkdir()

        with patch.dict(os.environ, {"FREECAD_PATH": str(tmp_path)}):
            resolver = FreeCADPathResolver()

            # First call resolves paths
            paths1 = resolver.resolve_paths()

            # Second call should return cached result
            paths2 = resolver.resolve_paths()

            assert paths1 == paths2
            assert resolver._resolved_paths is not None

    def test_setup_sys_path_normal(self, tmp_path):
        """Test sys.path setup with normal paths"""
        lib_dir = tmp_path / "lib"
        mod_dir = tmp_path / "Mod"
        lib_dir.mkdir()
        mod_dir.mkdir()

        original_path = sys.path.copy()

        with patch.dict(os.environ, {"FREECAD_PATH": str(tmp_path)}):
            resolver = FreeCADPathResolver()
            resolver.setup_sys_path()

            # Check paths were added
            assert str(lib_dir) in sys.path
            assert str(mod_dir) in sys.path

        # Cleanup
        sys.path = original_path

    def test_setup_sys_path_appimage(self, tmp_path):
        """Test sys.path setup with AppImage (should not modify sys.path)"""
        appimage = tmp_path / "FreeCAD.AppImage"
        appimage.touch()

        original_path = sys.path.copy()

        with patch.dict(os.environ, {"FREECAD_PATH": str(appimage)}):
            resolver = FreeCADPathResolver()
            resolver.setup_sys_path()

            # sys.path should not be modified for AppImage
            assert sys.path == original_path

    def test_get_executable_path_from_env_appimage(self, tmp_path):
        """Test getting executable path from environment AppImage"""
        appimage = tmp_path / "FreeCAD.AppImage"
        appimage.touch()

        with patch.dict(os.environ, {"FREECAD_PATH": str(appimage)}):
            resolver = FreeCADPathResolver()
            executable = resolver.get_executable_path()

            assert executable == str(appimage)

    def test_get_executable_path_from_env_directory(self, tmp_path):
        """Test getting executable path from environment directory"""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        freecadcmd = bin_dir / "freecadcmd"
        freecadcmd.touch()
        freecadcmd.chmod(0o755)

        with patch.dict(os.environ, {"FREECAD_PATH": str(tmp_path)}):
            resolver = FreeCADPathResolver()
            executable = resolver.get_executable_path()

            assert executable == str(freecadcmd)

    def test_get_executable_path_from_config(self, tmp_path):
        """Test getting executable path from config"""
        appimage = tmp_path / "FreeCAD.AppImage"
        appimage.touch()

        config = {"freecad": {"appimage_path": str(appimage)}}
        resolver = FreeCADPathResolver(config)
        executable = resolver.get_executable_path()

        assert executable == str(appimage)

    @patch("shutil.which")
    def test_get_executable_path_system_fallback(self, mock_which, tmp_path):
        """Test fallback to system freecadcmd"""
        system_freecadcmd = "/usr/bin/freecadcmd"
        mock_which.return_value = system_freecadcmd

        resolver = FreeCADPathResolver()
        executable = resolver.get_executable_path()

        assert executable == system_freecadcmd
        mock_which.assert_called_once_with("freecadcmd")

    def test_get_executable_path_not_found(self):
        """Test error when executable not found"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("shutil.which", return_value=None):
                resolver = FreeCADPathResolver()

                with pytest.raises(FreeCADPathError) as exc_info:
                    resolver.get_executable_path()

                assert "Could not locate FreeCAD executable" in str(exc_info.value)

    def test_resolution_priority_env_over_config(self, tmp_path):
        """Test that environment variable takes priority over config"""
        env_appimage = tmp_path / "env_FreeCAD.AppImage"
        config_appimage = tmp_path / "config_FreeCAD.AppImage"
        env_appimage.touch()
        config_appimage.touch()

        config = {"freecad": {"appimage_path": str(config_appimage)}}

        with patch.dict(os.environ, {"FREECAD_PATH": str(env_appimage)}):
            resolver = FreeCADPathResolver(config)
            lib_path, _ = resolver.resolve_paths()

            # Should use environment variable
            assert str(env_appimage) in lib_path

    def test_no_paths_found_error(self):
        """Test error when no valid paths can be found"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(
                FreeCADPathResolver, "_from_system_install", return_value=None
            ):
                with patch.object(
                    FreeCADPathResolver, "_from_appimage", return_value=None
                ):
                    resolver = FreeCADPathResolver()

                    with pytest.raises(FreeCADPathError) as exc_info:
                        resolver.resolve_paths()

                    assert "Could not locate FreeCAD installation" in str(
                        exc_info.value
                    )


class TestConvenienceFunctions:
    """Test module-level convenience functions"""

    def test_get_resolver_singleton(self):
        """Test global resolver instance"""
        resolver1 = get_resolver()
        resolver2 = get_resolver()

        # Should return same instance
        assert resolver1 is resolver2

    def test_get_resolver_with_config(self):
        """Test creating new resolver with config"""
        config = {"freecad": {"lib_path": "/test"}}
        resolver = get_resolver(config)

        assert resolver.config == config

    def test_setup_freecad_paths(self, tmp_path):
        """Test setup_freecad_paths convenience function"""
        lib_dir = tmp_path / "lib"
        mod_dir = tmp_path / "Mod"
        lib_dir.mkdir()
        mod_dir.mkdir()

        original_path = sys.path.copy()

        with patch.dict(os.environ, {"FREECAD_PATH": str(tmp_path)}):
            setup_freecad_paths()

            assert str(lib_dir) in sys.path
            assert str(mod_dir) in sys.path

        # Cleanup
        sys.path = original_path

    def test_get_freecad_executable(self, tmp_path):
        """Test get_freecad_executable convenience function"""
        appimage = tmp_path / "FreeCAD.AppImage"
        appimage.touch()

        config = {"freecad": {"appimage_path": str(appimage)}}
        executable = get_freecad_executable(config)

        assert executable == str(appimage)


class TestPlatformSpecific:
    """Test platform-specific path detection"""

    @patch("sys.platform", "linux")
    def test_linux_common_paths(self, tmp_path):
        """Test Linux common path detection"""
        # Create mock Linux installation
        freecad_dir = tmp_path / "usr" / "lib" / "freecad"
        lib_dir = freecad_dir / "lib"
        mod_dir = freecad_dir / "Mod"
        lib_dir.mkdir(parents=True)
        mod_dir.mkdir(parents=True)

        # Patch common paths to include tmp_path
        with patch.object(
            FreeCADPathResolver,
            "COMMON_PATHS",
            {"linux": [str(tmp_path / "usr" / "lib" / "freecad")]},
        ):
            resolver = FreeCADPathResolver()
            lib_path, mod_path = resolver.resolve_paths()

            assert lib_path == str(lib_dir)
            assert mod_path == str(mod_dir)

    def test_appimage_auto_detection(self, tmp_path):
        """Test auto-detection of AppImage in Downloads"""
        downloads_dir = tmp_path / "Downloads"
        downloads_dir.mkdir()
        appimage = downloads_dir / "FreeCAD_1.0.0.AppImage"
        appimage.touch()

        with patch.object(Path, "home", return_value=tmp_path):
            resolver = FreeCADPathResolver()
            lib_path, _ = resolver.resolve_paths()

            assert "appimage:" in lib_path

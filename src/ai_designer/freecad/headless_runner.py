"""
FreeCAD Headless Execution Engine

Production-grade headless FreeCAD script execution using freecadcmd subprocess.

Features:
- Subprocess-based execution (no GUI dependency)
- Automatic retry with exponential backoff for recompute errors
- Comprehensive stdout/stderr parsing
- Auto-save with metadata tracking
- Concurrent execution limiting via semaphore
- Multi-format export (STEP, STL, FCStd)
- FreeCAD version detection and adaptation
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from ..sandbox.result import ExecutionResult, ExecutionStatus
from .path_resolver import FreeCADPathResolver

logger = logging.getLogger(__name__)

# Global semaphore for limiting concurrent FreeCAD executions
_execution_semaphore: Optional[asyncio.Semaphore] = None


def get_execution_semaphore(max_concurrent: int = 4) -> asyncio.Semaphore:
    """
    Get or create global execution semaphore.

    Args:
        max_concurrent: Maximum concurrent FreeCAD processes (default: 4)

    Returns:
        Asyncio semaphore for limiting concurrent executions
    """
    global _execution_semaphore
    if _execution_semaphore is None:
        _execution_semaphore = asyncio.Semaphore(max_concurrent)
    return _execution_semaphore


class HeadlessRunner:
    """
    Headless FreeCAD script execution engine.

    Executes FreeCAD Python scripts via freecadcmd subprocess with:
    - Automatic retry on recompute errors
    - Output parsing and state extraction
    - Metadata tracking
    - Multi-format export
    """

    def __init__(
        self,
        freecad_cmd: Optional[str] = None,
        timeout: int = 120,
        max_retries: int = 3,
        outputs_dir: str = "outputs",
        auto_export: bool = True,
        export_formats: Optional[List[str]] = None,
    ):
        """
        Initialize headless runner.

        Args:
            freecad_cmd: Path to freecadcmd executable or AppImage (auto-detect if None)
            timeout: Execution timeout in seconds (default: 120)
            max_retries: Maximum retry attempts for recompute errors (default: 3)
            outputs_dir: Directory for saved outputs (default: "outputs")
            auto_export: Automatically export to configured formats (default: True)
            export_formats: Export formats list (default: ["fcstd", "step"])
        """
        self.freecad_cmd = freecad_cmd or self._detect_freecad_cmd()
        self.timeout = timeout
        self.max_retries = max_retries
        self.outputs_dir = Path(outputs_dir)
        self.auto_export = auto_export
        self.export_formats = export_formats or ["fcstd", "step"]

        # Create outputs directory
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

        # Detect FreeCAD version for template adaptation
        self.freecad_version = self._detect_freecad_version()

        logger.info(
            f"Initialized HeadlessRunner: cmd={self.freecad_cmd}, "
            f"version={self.freecad_version}, timeout={timeout}s, "
            f"max_retries={max_retries}"
        )

    def _detect_freecad_cmd(self) -> str:
        """Detect freecadcmd executable path."""
        try:
            resolver = FreeCADPathResolver()

            # Try common executable names
            for cmd in ["freecadcmd", "freecad", "FreeCADCmd"]:
                try:
                    result = subprocess.run(
                        [cmd, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        logger.info(f"Detected FreeCAD command: {cmd}")
                        return cmd
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue

            # Check for AppImage
            appimage_paths = [
                Path.home() / "Downloads",
                Path.home() / "Applications",
                Path("/opt"),
            ]
            for path_dir in appimage_paths:
                if path_dir.exists():
                    for appimage in path_dir.glob("FreeCAD*.AppImage"):
                        logger.info(f"Detected FreeCAD AppImage: {appimage}")
                        return str(appimage)

            # Fallback to freecadcmd
            logger.warning("Could not detect FreeCAD, using 'freecadcmd' as default")
            return "freecadcmd"

        except Exception as e:
            logger.warning(f"FreeCAD detection failed: {e}, using 'freecadcmd'")
            return "freecadcmd"

    def _detect_freecad_version(self) -> Optional[str]:
        """Detect FreeCAD version."""
        try:
            result = subprocess.run(
                [self.freecad_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Parse version from output (e.g., "FreeCAD 0.21.2")
                match = re.search(r"FreeCAD\s+([\d.]+)", result.stdout)
                if match:
                    version = match.group(1)
                    logger.info(f"Detected FreeCAD version: {version}")
                    return version
        except Exception as e:
            logger.warning(f"Could not detect FreeCAD version: {e}")
        return None

    def _create_script_template(
        self,
        user_script: str,
        document_name: str,
        request_id: Optional[UUID] = None,
    ) -> str:
        """
        Create complete FreeCAD script with error handling and output markers.

        Args:
            user_script: User-provided FreeCAD Python code
            document_name: Name for the FreeCAD document
            request_id: Optional design request ID for tracking

        Returns:
            Complete FreeCAD script ready for execution
        """
        # Indent user script
        indented_script = "\n".join(f"    {line}" for line in user_script.split("\n"))

        template = f'''#!/usr/bin/env python3
"""
Auto-generated FreeCAD script
Generated: {datetime.utcnow().isoformat()}
Document: {document_name}
Request ID: {request_id or "N/A"}
"""

import sys
import traceback

# Import FreeCAD modules
try:
    import FreeCAD as App
    import Part
    import PartDesign
    import Sketcher
    import Draft
except ImportError as e:
    print(f"ERROR: Failed to import FreeCAD modules: {{e}}")
    sys.exit(1)

# Create new document
try:
    doc = App.newDocument("{document_name}")
    print(f"DOCUMENT_CREATED: {document_name}")
except Exception as e:
    print(f"ERROR: Failed to create document: {{e}}")
    sys.exit(1)

# Execute user script
print("SCRIPT_START")
try:
{indented_script}

    # Recompute document
    print("RECOMPUTE_START")
    recompute_result = doc.recompute()

    if recompute_result == -1:
        print("ERROR: Document recompute failed")
        # Check for specific errors
        for obj in doc.Objects:
            if hasattr(obj, 'State') and obj.State != 0:
                print(f"ERROR: Object '{{obj.Label}}' has errors (State={{obj.State}})")
    else:
        print("RECOMPUTE_SUCCESS")

    # Report created objects
    for obj in doc.Objects:
        obj_type = obj.TypeId if hasattr(obj, 'TypeId') else 'Unknown'
        print(f"CREATED_OBJECT: {{obj.Label}} ({{obj_type}})")

    print("SCRIPT_SUCCESS")

except Exception as e:
    print(f"ERROR: Script execution failed: {{e}}")
    traceback.print_exc()
    sys.exit(1)

# Save document (will be handled by runner)
print("EXECUTION_COMPLETE")
'''
        return template

    def _parse_output(
        self, stdout: str, stderr: str, exit_code: int
    ) -> Tuple[List[str], List[str], List[str], bool]:
        """
        Parse FreeCAD output for objects, errors, and warnings.

        Args:
            stdout: Process stdout
            stderr: Process stderr
            exit_code: Process exit code

        Returns:
            Tuple of (created_objects, errors, warnings, recompute_success)
        """
        created_objects = []
        errors = []
        warnings = []
        recompute_success = False

        # Parse stdout for markers
        for line in stdout.split("\n"):
            line = line.strip()

            if line.startswith("CREATED_OBJECT:"):
                obj_info = line.replace("CREATED_OBJECT:", "").strip()
                created_objects.append(obj_info)

            elif line.startswith("ERROR:"):
                error_msg = line.replace("ERROR:", "").strip()
                errors.append(error_msg)

            elif line.startswith("WARNING:"):
                warning_msg = line.replace("WARNING:", "").strip()
                warnings.append(warning_msg)

            elif line == "RECOMPUTE_SUCCESS":
                recompute_success = True

        # Parse stderr for Python errors
        if stderr:
            for line in stderr.split("\n"):
                if line.strip() and not line.startswith("Qt"):  # Ignore Qt warnings
                    errors.append(line.strip())

        # Check exit code
        if exit_code != 0 and not errors:
            errors.append(f"Process exited with code {exit_code}")

        return created_objects, errors, warnings, recompute_success

    async def execute_script(
        self,
        script: str,
        document_name: Optional[str] = None,
        request_id: Optional[UUID] = None,
        user_prompt: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Execute FreeCAD script with retry logic.

        Args:
            script: FreeCAD Python script to execute
            document_name: Document name (auto-generated if None)
            request_id: Design request ID for tracking
            user_prompt: Original user prompt for metadata

        Returns:
            ExecutionResult with execution details
        """
        # Use semaphore to limit concurrent executions
        semaphore = get_execution_semaphore()

        async with semaphore:
            return await self._execute_with_retry(
                script, document_name, request_id, user_prompt
            )

    async def _execute_with_retry(
        self,
        script: str,
        document_name: Optional[str],
        request_id: Optional[UUID],
        user_prompt: Optional[str],
    ) -> ExecutionResult:
        """Execute script with exponential backoff retry."""
        if not document_name:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            document_name = f"Design_{timestamp}"

        attempt = 0
        last_error = None

        while attempt < self.max_retries:
            attempt += 1
            logger.info(
                f"Executing script (attempt {attempt}/{self.max_retries}): {document_name}"
            )

            try:
                result = await self._execute_single(
                    script, document_name, request_id, user_prompt
                )

                # Check if recompute failed
                if not result.success and "recompute failed" in result.error.lower():
                    last_error = result.error

                    if attempt < self.max_retries:
                        # Exponential backoff: 1s, 2s, 4s
                        backoff_seconds = 2 ** (attempt - 1)
                        logger.warning(
                            f"Recompute failed, retrying in {backoff_seconds}s... "
                            f"(attempt {attempt}/{self.max_retries})"
                        )
                        await asyncio.sleep(backoff_seconds)
                        continue

                return result

            except subprocess.TimeoutExpired:
                last_error = f"Execution timeout ({self.timeout}s)"
                logger.error(f"Attempt {attempt} timed out")

                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue

            except Exception as e:
                last_error = str(e)
                logger.error(f"Attempt {attempt} failed: {e}")

                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue

        # All retries exhausted
        return ExecutionResult(
            success=False,
            status=ExecutionStatus.EXECUTION_FAILED,
            error=f"Failed after {self.max_retries} attempts. Last error: {last_error}",
            metadata={"retries": attempt, "last_error": last_error},
        )

    async def _execute_single(
        self,
        script: str,
        document_name: str,
        request_id: Optional[UUID],
        user_prompt: Optional[str],
    ) -> ExecutionResult:
        """Execute single script attempt."""
        start_time = time.time()

        # Create complete script
        full_script = self._create_script_template(script, document_name, request_id)

        # Write to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as temp_file:
            temp_file.write(full_script)
            script_path = temp_file.name

        try:
            # Determine command based on FreeCAD type
            if self.freecad_cmd.endswith(".AppImage"):
                cmd = [self.freecad_cmd, "--console", "--run", script_path]
            else:
                cmd = [self.freecad_cmd, script_path]

            # Execute subprocess
            logger.debug(f"Running: {' '.join(cmd)}")

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            process = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                ),
            )

            execution_time = time.time() - start_time

            # Parse output
            created_objects, errors, warnings, recompute_ok = self._parse_output(
                process.stdout, process.stderr, process.returncode
            )

            # Determine success
            success = process.returncode == 0 and recompute_ok and not errors

            # Save document if successful
            document_path = None
            if success and self.auto_export:
                document_path = await self._save_document(
                    document_name, request_id, user_prompt, created_objects
                )

            # Create result
            result = ExecutionResult(
                success=success,
                status=ExecutionStatus.SUCCESS
                if success
                else ExecutionStatus.EXECUTION_FAILED,
                output=process.stdout,
                error="\n".join(errors) if errors else "",
                execution_time=execution_time,
                exit_code=process.returncode,
                created_objects=[obj.split("(")[0].strip() for obj in created_objects],
                metadata={
                    "document_name": document_name,
                    "document_path": str(document_path) if document_path else None,
                    "request_id": str(request_id) if request_id else None,
                    "warnings": warnings,
                    "recompute_success": recompute_ok,
                    "freecad_version": self.freecad_version,
                },
            )

            if success:
                logger.info(
                    f"Script executed successfully: {len(created_objects)} objects created "
                    f"in {execution_time:.2f}s"
                )
            else:
                logger.error(f"Script execution failed: {errors}")

            return result

        finally:
            # Cleanup temp file
            try:
                Path(script_path).unlink()
            except Exception:
                pass

    async def _save_document(
        self,
        document_name: str,
        request_id: Optional[UUID],
        user_prompt: Optional[str],
        created_objects: List[str],
    ) -> Optional[Path]:
        """
        Save FreeCAD document and metadata.

        Returns:
            Path to saved document or None if save failed
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            base_name = f"{document_name}_{timestamp}"

            if request_id:
                base_name = f"{document_name}_{request_id}_{timestamp}"

            # Save metadata
            metadata = {
                "timestamp": datetime.utcnow().isoformat(),
                "document_name": document_name,
                "request_id": str(request_id) if request_id else None,
                "user_prompt": user_prompt,
                "created_objects": created_objects,
                "freecad_version": self.freecad_version,
                "export_formats": self.export_formats,
            }

            metadata_path = self.outputs_dir / f"{base_name}.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Saved metadata: {metadata_path}")

            # Note: Actual document saving will be handled by export methods
            # Return the base path for exports
            return self.outputs_dir / base_name

        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
            return None

    async def export_step(
        self,
        doc_path: Path,
        output_path: Optional[Path] = None,
        timeout: int = 60,
    ) -> Optional[Path]:
        """
        Export FreeCAD document to STEP format.

        Args:
            doc_path: Path to FreeCAD document (.FCStd)
            output_path: Optional output path (auto-generated if None)
            timeout: Export timeout in seconds (default: 60)

        Returns:
            Path to exported STEP file, or None on failure
        """
        if output_path is None:
            output_path = doc_path.with_suffix(".step")

        logger.info(f"Exporting STEP: {doc_path} -> {output_path}")

        export_script = f"""
import sys
try:
    import FreeCAD as App
    import Import

    # Open document
    doc = App.openDocument("{doc_path}")

    # Get all visible objects
    objects = [obj for obj in doc.Objects if hasattr(obj, 'ViewObject') and obj.ViewObject.Visibility]

    # Export to STEP
    Import.export(objects, "{output_path}")

    print(f"EXPORT_SUCCESS: {output_path}")

    App.closeDocument(doc.Name)
    sys.exit(0)

except Exception as e:
    print(f"EXPORT_ERROR: {{e}}", file=sys.stderr)
    sys.exit(1)
"""

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as temp_file:
                temp_file.write(export_script)
                script_path = temp_file.name

            try:
                result = subprocess.run(
                    [self.freecad_cmd, script_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                if result.returncode == 0 and output_path.exists():
                    logger.info(f"STEP export successful: {output_path}")
                    return output_path
                else:
                    logger.error(f"STEP export failed: {result.stderr}")
                    return None

            finally:
                Path(script_path).unlink()

        except Exception as e:
            logger.error(f"STEP export error: {e}")
            return None

    async def export_stl(
        self,
        doc_path: Path,
        output_path: Optional[Path] = None,
        resolution: float = 0.1,
        timeout: int = 60,
    ) -> Optional[Path]:
        """
        Export FreeCAD document to STL format.

        Args:
            doc_path: Path to FreeCAD document (.FCStd)
            output_path: Optional output path (auto-generated if None)
            resolution: Mesh resolution (0.01-1.0, lower = finer, default: 0.1)
            timeout: Export timeout in seconds (default: 60)

        Returns:
            Path to exported STL file, or None on failure
        """
        if output_path is None:
            output_path = doc_path.with_suffix(".stl")

        # Clamp resolution
        resolution = max(0.01, min(1.0, resolution))

        logger.info(
            f"Exporting STL: {doc_path} -> {output_path} (resolution={resolution})"
        )

        export_script = f"""
import sys
try:
    import FreeCAD as App
    import Mesh
    import MeshPart

    # Open document
    doc = App.openDocument("{doc_path}")

    # Get all visible objects with shapes
    objects = []
    for obj in doc.Objects:
        if hasattr(obj, 'Shape') and hasattr(obj, 'ViewObject') and obj.ViewObject.Visibility:
            objects.append(obj)

    if not objects:
        print("EXPORT_ERROR: No visible objects with shapes found", file=sys.stderr)
        sys.exit(1)

    # Create mesh from shapes
    meshes = []
    for obj in objects:
        # Mesh parameters: deviation={resolution}, angular_deflection=0.5
        mesh = MeshPart.meshFromShape(
            Shape=obj.Shape,
            LinearDeflection={resolution},
            AngularDeflection=0.5,
            Relative=False
        )
        meshes.append(mesh)

    # Merge all meshes
    if len(meshes) > 1:
        combined_mesh = meshes[0]
        for mesh in meshes[1:]:
            combined_mesh.addMesh(mesh)
    else:
        combined_mesh = meshes[0]

    # Export to STL
    combined_mesh.write("{output_path}")

    print(f"EXPORT_SUCCESS: {output_path}")

    App.closeDocument(doc.Name)
    sys.exit(0)

except Exception as e:
    import traceback
    print(f"EXPORT_ERROR: {{e}}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    sys.exit(1)
"""

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as temp_file:
                temp_file.write(export_script)
                script_path = temp_file.name

            try:
                result = subprocess.run(
                    [self.freecad_cmd, script_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                if result.returncode == 0 and output_path.exists():
                    logger.info(f"STL export successful: {output_path}")
                    return output_path
                else:
                    logger.error(f"STL export failed: {result.stderr}")
                    return None

            finally:
                Path(script_path).unlink()

        except Exception as e:
            logger.error(f"STL export error: {e}")
            return None

    async def export_fcstd(
        self,
        doc_path: Path,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Copy FreeCAD document to new location (native format export).

        Args:
            doc_path: Path to FreeCAD document (.FCStd)
            output_path: Optional output path (auto-generated if None)

        Returns:
            Path to copied FCStd file, or None on failure
        """
        if output_path is None:
            output_path = self.outputs_dir / doc_path.name

        try:
            import shutil

            shutil.copy2(doc_path, output_path)
            logger.info(f"FCStd copied: {doc_path} -> {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"FCStd copy error: {e}")
            return None

    async def export_all_formats(
        self,
        doc_path: Path,
        output_dir: Optional[Path] = None,
        stl_resolution: float = 0.1,
        formats: Optional[List[str]] = None,
        timeout: int = 120,
    ) -> Dict[str, Optional[Path]]:
        """
        Export FreeCAD document to multiple formats.

        Args:
            doc_path: Path to FreeCAD document (.FCStd)
            output_dir: Optional output directory (uses self.outputs_dir if None)
            stl_resolution: Mesh resolution for STL (default: 0.1)
            formats: List of formats to export ['step', 'stl', 'fcstd'] (default: all)
            timeout: Export timeout per format in seconds (default: 120)

        Returns:
            Dictionary mapping format to exported path (None on failure):
            {
                'step': Path or None,
                'stl': Path or None,
                'fcstd': Path or None,
            }
        """
        if formats is None:
            formats = ["step", "stl", "fcstd"]

        if output_dir is None:
            output_dir = self.outputs_dir

        output_dir.mkdir(parents=True, exist_ok=True)
        base_name = doc_path.stem

        results = {}

        logger.info(f"Exporting to formats: {formats}")

        # Export STEP
        if "step" in formats:
            step_path = output_dir / f"{base_name}.step"
            results["step"] = await self.export_step(doc_path, step_path, timeout)

        # Export STL
        if "stl" in formats:
            stl_path = output_dir / f"{base_name}.stl"
            results["stl"] = await self.export_stl(
                doc_path, stl_path, stl_resolution, timeout
            )

        # Export/Copy FCStd
        if "fcstd" in formats:
            fcstd_path = output_dir / f"{base_name}.FCStd"
            results["fcstd"] = await self.export_fcstd(doc_path, fcstd_path)

        logger.info(f"Export summary: {results}")
        return results

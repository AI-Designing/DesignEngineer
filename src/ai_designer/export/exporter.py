"""
CAD Exporter with Metadata and Caching

Wrapper around HeadlessRunner export functionality with:
- Enhanced metadata tracking (prompt hash, timestamps, file sizes)
- Export caching to avoid regenerating identical designs
- Multi-format export (STEP, STL, FCStd)
- JSON sidecar files for metadata
- Audit logging integration

Version: 1.0.0
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import UUID

from ..freecad.headless_runner import HeadlessRunner

logger = logging.getLogger(__name__)


@dataclass
class ExportMetadata:
    """Metadata for an exported CAD file."""

    prompt: str
    prompt_hash: str
    request_id: str
    format: str
    file_path: str
    file_size_bytes: int
    created_at: str
    freecad_version: Optional[str] = None
    export_settings: Dict[str, any] = field(default_factory=dict)
    cache_hit: bool = False


@dataclass
class ExportResult:
    """Result from export operation."""

    success: bool
    format: str
    file_path: Optional[Path] = None
    metadata: Optional[ExportMetadata] = None
    error: Optional[str] = None
    cache_hit: bool = False


class CADExporter:
    """
    CAD export engine with metadata tracking and caching.

    Wraps HeadlessRunner export methods with:
    - Prompt hashing for deduplication
    - Metadata generation and JSON sidecar files
    - Cache lookup to avoid redundant exports
    - Multi-format export with parallel processing
    """

    def __init__(
        self,
        headless_runner: Optional[HeadlessRunner] = None,
        outputs_dir: str = "outputs",
        enable_cache: bool = True,
        cache_dir: Optional[str] = None,
    ):
        """
        Initialize CAD exporter.

        Args:
            headless_runner: HeadlessRunner instance (creates new if None)
            outputs_dir: Directory for exports (default: "outputs")
            enable_cache: Enable export caching (default: True)
            cache_dir: Cache directory (default: outputs_dir/.cache)
        """
        self.runner = headless_runner or HeadlessRunner(outputs_dir=outputs_dir)
        self.outputs_dir = Path(outputs_dir)
        self.enable_cache = enable_cache

        # Cache directory structure
        self.cache_dir = Path(cache_dir) if cache_dir else self.outputs_dir / ".cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache index: prompt_hash -> {format: file_path}
        self.cache_index_path = self.cache_dir / "export_cache_index.json"
        self._cache_index = self._load_cache_index()

        # Ensure cache index file exists
        if not self.cache_index_path.exists():
            self._save_cache_index()

        logger.info(
            f"Initialized CADExporter: outputs_dir={outputs_dir}, "
            f"cache_enabled={enable_cache}"
        )

    def _load_cache_index(self) -> Dict[str, Dict[str, str]]:
        """Load export cache index from disk."""
        if not self.cache_index_path.exists():
            return {}

        try:
            with open(self.cache_index_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache index: {e}")
            return {}

    def _save_cache_index(self):
        """Save export cache index to disk."""
        try:
            with open(self.cache_index_path, "w") as f:
                json.dump(self._cache_index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache index: {e}")

    @staticmethod
    def compute_prompt_hash(prompt: str) -> str:
        """
        Compute SHA-256 hash of prompt for caching.

        Args:
            prompt: User prompt text

        Returns:
            Hex string of SHA-256 hash (first 16 chars)

        Example:
            >>> CADExporter.compute_prompt_hash("Create a box")
            'a1b2c3d4e5f6g7h8'
        """
        hash_obj = hashlib.sha256(prompt.encode("utf-8"))
        return hash_obj.hexdigest()[:16]  # Use first 16 chars for brevity

    def _check_cache(self, prompt_hash: str, format: str) -> Optional[Path]:
        """
        Check if export exists in cache.

        Args:
            prompt_hash: Hash of user prompt
            format: Export format (step, stl, fcstd)

        Returns:
            Path to cached file if exists and valid, None otherwise
        """
        if not self.enable_cache:
            return None

        # Check index
        cached_entry = self._cache_index.get(prompt_hash, {}).get(format)
        if not cached_entry:
            return None

        # Verify file exists
        cached_path = Path(cached_entry)
        if cached_path.exists():
            logger.info(f"Cache HIT: {format} for prompt_hash={prompt_hash}")
            return cached_path

        # Stale cache entry
        logger.warning(f"Stale cache entry for {prompt_hash}/{format}, removing")
        del self._cache_index[prompt_hash][format]
        self._save_cache_index()
        return None

    def _update_cache(self, prompt_hash: str, format: str, file_path: Path):
        """
        Update cache index with new export.

        Args:
            prompt_hash: Hash of user prompt
            format: Export format
            file_path: Path to exported file
        """
        if not self.enable_cache:
            return

        if prompt_hash not in self._cache_index:
            self._cache_index[prompt_hash] = {}

        self._cache_index[prompt_hash][format] = str(file_path)
        self._save_cache_index()

        logger.info(f"Cache updated: {format} -> {file_path}")

    def _generate_metadata(
        self,
        prompt: str,
        prompt_hash: str,
        request_id: str,
        format: str,
        file_path: Path,
        export_settings: Dict[str, any] = None,
        cache_hit: bool = False,
    ) -> ExportMetadata:
        """
        Generate export metadata.

        Args:
            prompt: Original user prompt
            prompt_hash: SHA-256 hash of prompt
            request_id: Design request ID
            format: Export format
            file_path: Path to exported file
            export_settings: Format-specific export settings
            cache_hit: Whether this was a cache hit

        Returns:
            ExportMetadata object
        """
        file_size = file_path.stat().st_size if file_path.exists() else 0

        return ExportMetadata(
            prompt=prompt,
            prompt_hash=prompt_hash,
            request_id=str(request_id),
            format=format,
            file_path=str(file_path),
            file_size_bytes=file_size,
            created_at=datetime.utcnow().isoformat(),
            freecad_version=self.runner.freecad_version,
            export_settings=export_settings or {},
            cache_hit=cache_hit,
        )

    def _save_metadata_sidecar(self, file_path: Path, metadata: ExportMetadata):
        """
        Save metadata JSON sidecar file.

        Creates .json file alongside export (e.g., design.step.json)

        Args:
            file_path: Path to exported file
            metadata: Metadata to save
        """
        sidecar_path = file_path.with_suffix(file_path.suffix + ".json")

        try:
            metadata_dict = {
                "prompt": metadata.prompt,
                "prompt_hash": metadata.prompt_hash,
                "request_id": metadata.request_id,
                "format": metadata.format,
                "file_path": metadata.file_path,
                "file_size_bytes": metadata.file_size_bytes,
                "created_at": metadata.created_at,
                "freecad_version": metadata.freecad_version,
                "export_settings": metadata.export_settings,
                "cache_hit": metadata.cache_hit,
            }

            with open(sidecar_path, "w") as f:
                json.dump(metadata_dict, f, indent=2)

            logger.info(f"Metadata saved: {sidecar_path}")

        except Exception as e:
            logger.error(f"Failed to save metadata sidecar: {e}")

    async def export_format(
        self,
        doc_path: Path,
        format: str,
        prompt: str,
        request_id: UUID,
        output_path: Optional[Path] = None,
        **export_kwargs,
    ) -> ExportResult:
        """
        Export to single format with metadata and caching.

        Args:
            doc_path: Path to FreeCAD document (.FCStd)
            format: Export format ('step', 'stl', 'fcstd')
            prompt: Original user prompt
            request_id: Design request ID
            output_path: Optional output path (auto-generated if None)
            **export_kwargs: Format-specific kwargs (e.g., resolution for STL)

        Returns:
            ExportResult with success status and metadata

        Example:
            >>> result = await exporter.export_format(
            ...     doc_path=Path("design.FCStd"),
            ...     format="step",
            ...     prompt="Create a box",
            ...     request_id=uuid4()
            ... )
            >>> result.success
            True
        """
        format = format.lower()
        if format not in ["step", "stl", "fcstd"]:
            return ExportResult(
                success=False,
                format=format,
                error=f"Unsupported format: {format}. Use step, stl, or fcstd.",
            )

        # Compute prompt hash for caching
        prompt_hash = self.compute_prompt_hash(prompt)

        # Check cache
        cached_path = self._check_cache(prompt_hash, format)
        if cached_path:
            metadata = self._generate_metadata(
                prompt=prompt,
                prompt_hash=prompt_hash,
                request_id=str(request_id),
                format=format,
                file_path=cached_path,
                export_settings=export_kwargs,
                cache_hit=True,
            )
            return ExportResult(
                success=True,
                format=format,
                file_path=cached_path,
                metadata=metadata,
                cache_hit=True,
            )

        # Generate output path if not provided
        if output_path is None:
            base_name = f"{request_id}_{prompt_hash}"
            suffix = {"step": ".step", "stl": ".stl", "fcstd": ".FCStd"}[format]
            output_path = self.outputs_dir / f"{base_name}{suffix}"

        # Call appropriate export method
        try:
            if format == "step":
                result_path = await self.runner.export_step(
                    doc_path, output_path, **export_kwargs
                )
            elif format == "stl":
                result_path = await self.runner.export_stl(
                    doc_path, output_path, **export_kwargs
                )
            elif format == "fcstd":
                result_path = await self.runner.export_fcstd(
                    doc_path, output_path, **export_kwargs
                )

            if result_path is None:
                return ExportResult(
                    success=False,
                    format=format,
                    error=f"Export failed for format: {format}",
                )

            # Update cache
            self._update_cache(prompt_hash, format, result_path)

            # Generate and save metadata
            metadata = self._generate_metadata(
                prompt=prompt,
                prompt_hash=prompt_hash,
                request_id=str(request_id),
                format=format,
                file_path=result_path,
                export_settings=export_kwargs,
                cache_hit=False,
            )
            self._save_metadata_sidecar(result_path, metadata)

            return ExportResult(
                success=True,
                format=format,
                file_path=result_path,
                metadata=metadata,
                cache_hit=False,
            )

        except Exception as e:
            logger.error(f"Export error ({format}): {e}")
            return ExportResult(
                success=False, format=format, error=f"Export exception: {str(e)}"
            )

    async def export_multiple_formats(
        self,
        doc_path: Path,
        formats: List[str],
        prompt: str,
        request_id: UUID,
        **export_kwargs,
    ) -> Dict[str, ExportResult]:
        """
        Export to multiple formats concurrently.

        Args:
            doc_path: Path to FreeCAD document (.FCStd)
            formats: List of export formats ['step', 'stl', 'fcstd']
            prompt: Original user prompt
            request_id: Design request ID
            **export_kwargs: Format-specific kwargs applied to all formats

        Returns:
            Dictionary mapping format to ExportResult

        Example:
            >>> results = await exporter.export_multiple_formats(
            ...     doc_path=Path("design.FCStd"),
            ...     formats=["step", "stl"],
            ...     prompt="Create a box",
            ...     request_id=uuid4()
            ... )
            >>> results["step"].success
            True
        """
        # Create export tasks for each format
        tasks = []
        for format in formats:
            task = self.export_format(
                doc_path=doc_path,
                format=format,
                prompt=prompt,
                request_id=request_id,
                **export_kwargs,
            )
            tasks.append((format, task))

        # Execute concurrently
        results = {}
        completed = await asyncio.gather(*[task for _, task in tasks])

        for (format, _), result in zip(tasks, completed):
            results[format] = result

        # Log summary
        success_count = sum(1 for r in results.values() if r.success)
        cache_hits = sum(1 for r in results.values() if r.cache_hit)
        logger.info(
            f"Multi-format export complete: {success_count}/{len(formats)} succeeded, "
            f"{cache_hits} cache hits"
        )

        return results

    def get_export_path(
        self, request_id: UUID, format: str, prompt_hash: Optional[str] = None
    ) -> Path:
        """
        Get expected export file path for a request.

        Args:
            request_id: Design request ID
            format: Export format
            prompt_hash: Optional prompt hash (computed if None)

        Returns:
            Path where export file should be located
        """
        if prompt_hash is None:
            # Path without hash (fallback)
            suffix = {"step": ".step", "stl": ".stl", "fcstd": ".FCStd"}[format.lower()]
            return self.outputs_dir / f"{request_id}{suffix}"

        base_name = f"{request_id}_{prompt_hash}"
        suffix = {"step": ".step", "stl": ".stl", "fcstd": ".FCStd"}[format.lower()]
        return self.outputs_dir / f"{base_name}{suffix}"

    def list_exports(self, request_id: Optional[UUID] = None) -> List[Path]:
        """
        List all exported files, optionally filtered by request_id.

        Args:
            request_id: Optional request ID to filter by

        Returns:
            List of exported file paths
        """
        if not self.outputs_dir.exists():
            return []

        # Find all export files
        patterns = ["*.step", "*.stl", "*.FCStd"]
        files = []

        for pattern in patterns:
            files.extend(self.outputs_dir.glob(pattern))

        # Filter by request_id if provided
        if request_id:
            request_str = str(request_id)
            files = [f for f in files if request_str in f.name]

        return sorted(files)

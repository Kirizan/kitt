"""GGUF quantization discovery and model path resolution."""

import fnmatch
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Regex matching all common GGUF quantization names.
# Covers: Q2_K through Q8_0, IQ1_S through IQ4_XS, FP16, BF16, F32
_QUANT_PATTERN = re.compile(
    r'(IQ[1-4]_[A-Za-z]+|[Qq][2-8]_[Kk0](?:_[SMLsml])?|[Ff][Pp]16|[Bb][Ff]16|[Ff]32)'
)

# Shard file pattern: -00001-of-00002.gguf
_SHARD_PATTERN = re.compile(r'-(\d{5})-of-(\d{5})\.gguf$')


@dataclass
class GGUFQuantInfo:
    """Information about a single quantization variant."""

    quant_name: str
    files: List[str] = field(default_factory=list)
    include_pattern: str = ""
    total_size_bytes: int = 0

    @property
    def is_sharded(self) -> bool:
        return len(self.files) > 1

    @property
    def primary_file(self) -> str:
        """First file (or first shard) for loading."""
        return self.files[0] if self.files else ""


def extract_quant_name(filename: str) -> str:
    """Extract quantization name from a GGUF filename.

    Always operates on the filename part only (no directory components).

    Examples:
        Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf -> Q4_K_M
        qwen2.5-7b-instruct-q4_k_m.gguf -> q4_k_m
        model-IQ4_XS.gguf -> IQ4_XS
        model-IQ3_M.gguf -> IQ3_M
    """
    # Strip to filename only — never match against directory names
    name = Path(filename).name
    # Remove .gguf extension explicitly (Path.stem breaks on names with dots
    # like "Llama-3.3-70B-Q4_K_M" where it misinterprets ".3-70B-Q4_K_M" as extension)
    if name.lower().endswith(".gguf"):
        name = name[:-5]
    match = _QUANT_PATTERN.search(name)
    return match.group(0) if match else name


def discover_gguf_quants(repo_id: str) -> List[GGUFQuantInfo]:
    """List available GGUF quantization variants in a HuggingFace repo.

    Groups sharded files into single entries and builds appropriate
    include patterns for downloading.

    Args:
        repo_id: HuggingFace repository ID (e.g. "bartowski/Llama-3.1-8B-GGUF").

    Returns:
        List of GGUFQuantInfo, one per quantization variant.
    """
    try:
        from huggingface_hub import list_repo_files
        all_files = list(list_repo_files(repo_id))
        gguf_files = sorted(f for f in all_files if f.endswith(".gguf"))
    except Exception as e:
        logger.error(f"Failed to list GGUF files for {repo_id}: {e}")
        return []

    if not gguf_files:
        return []

    # Group files by quant name
    quant_groups: dict[str, List[str]] = {}

    for filepath in gguf_files:
        # Always extract quant from the filename, not the full path
        filename = Path(filepath).name
        shard_match = _SHARD_PATTERN.search(filename)

        if shard_match:
            # Shard file — strip shard suffix to get base name
            base = _SHARD_PATTERN.sub('', filename)
            quant_name = extract_quant_name(base)
        else:
            quant_name = extract_quant_name(filename)

        quant_groups.setdefault(quant_name, []).append(filepath)

    quants = []
    for quant_name, files in quant_groups.items():
        files = sorted(files)

        if len(files) == 1:
            include_pattern = files[0]
        else:
            # Multiple shards — use glob pattern
            common_dir = str(Path(files[0]).parent)
            if common_dir and common_dir != ".":
                include_pattern = f"{common_dir}/*.gguf"
            else:
                prefix = _common_prefix(files)
                include_pattern = f"{prefix}*.gguf"

        quants.append(GGUFQuantInfo(
            quant_name=quant_name,
            files=files,
            include_pattern=include_pattern,
        ))

    logger.info(
        f"Found {len(quants)} GGUF quant variants "
        f"({len(gguf_files)} files) in {repo_id}"
    )
    return quants


def discover_ollama_tags(base_tag: str) -> List[str]:
    """Discover available Ollama tags for a model.

    Scrapes the Ollama library page and filters to quant variants
    matching the base tag's parameter size.

    Falls back to the base tag if discovery fails.

    Args:
        base_tag: Ollama tag like "llama3.1:8b".

    Returns:
        List of full tags like ["llama3.1:8b-instruct-q4_0", ...].
    """
    model_name = base_tag.split(":")[0]
    target_size = base_tag.split(":")[-1] if ":" in base_tag else None

    try:
        import urllib.request
        url = f"https://ollama.com/library/{model_name}/tags"
        req = urllib.request.Request(url, headers={"User-Agent": "kitt/1.1"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Parse tags from href patterns
        raw_tags = re.findall(
            rf'/library/{re.escape(model_name)}:([^"&\s]+)', html
        )

        # Deduplicate preserving order
        seen = set()
        unique_tags = []
        for tag in raw_tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        if unique_tags:
            filtered = []
            for tag in unique_tags:
                if target_size and target_size != "latest":
                    if not tag.startswith(target_size):
                        continue
                if "-text-" in tag or tag.endswith("-text"):
                    continue
                filtered.append(f"{model_name}:{tag}")

            if filtered:
                logger.info(f"Found {len(filtered)} Ollama tags for {base_tag}")
                return sorted(filtered)

    except Exception as e:
        logger.warning(f"Ollama tag discovery failed for {model_name}: {e}")

    logger.info(f"Using base tag only for {model_name}: {base_tag}")
    return [base_tag]


def find_model_path(
    repo_id: str,
    gguf_relative_path: Optional[str] = None,
    storage_root: Optional[Path] = None,
) -> Optional[str]:
    """Find the local path for a downloaded model.

    Args:
        repo_id: HuggingFace repository ID.
        gguf_relative_path: Full relative path of GGUF file within repo
            (e.g. "subdir/model-Q4_K_M-00001-of-00002.gguf").
            Pass the full relative path, not just the filename.
        storage_root: Devon storage root. Defaults to ~/models.

    Returns:
        Path to model file or directory, or None if not found.
    """
    root = storage_root or (Path.home() / "models")
    base = root / "huggingface" / repo_id

    if not base.exists():
        logger.warning(f"Model directory not found: {base}")
        return None

    if gguf_relative_path:
        # Try the full relative path first (handles subdirectories)
        gguf_path = base / gguf_relative_path
        if gguf_path.exists():
            return str(gguf_path)

        # Fallback: search recursively by filename
        filename = Path(gguf_relative_path).name
        for p in base.rglob(filename):
            return str(p)

        logger.warning(
            f"GGUF file not found: {gguf_relative_path} in {base}"
        )
        return None

    # For safetensors: return the directory
    return str(base)


def filter_quants(
    quants: List[GGUFQuantInfo],
    skip_patterns: Optional[List[str]] = None,
    include_only: Optional[List[str]] = None,
) -> List[GGUFQuantInfo]:
    """Filter quantization variants by name patterns.

    Args:
        quants: List of discovered quants.
        skip_patterns: Glob patterns to exclude (e.g. ["IQ1_*", "IQ2_*"]).
        include_only: If set, only keep quants matching these patterns.

    Returns:
        Filtered list.
    """
    result = quants

    if skip_patterns:
        result = [
            q for q in result
            if not any(fnmatch.fnmatch(q.quant_name, pat) for pat in skip_patterns)
        ]

    if include_only:
        result = [
            q for q in result
            if any(fnmatch.fnmatch(q.quant_name, pat) for pat in include_only)
        ]

    return result


def _common_prefix(strings: List[str]) -> str:
    """Find the longest common prefix of a list of strings."""
    if not strings:
        return ""
    prefix = strings[0]
    for s in strings[1:]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix

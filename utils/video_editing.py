"""
Shared video editing utilities for the post processing pipeline.

This module provides common functions for video manipulation operations
like cutting, concatenating segments, and probing video properties.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Sequence


def probe_duration(path: Path) -> float:
    """
    Probe video duration using ffprobe.
    
    Parameters
    ----------
    path:
        Path to the video file
        
    Returns
    -------
    float:
        Duration in seconds
        
    Raises
    ------
    RuntimeError:
        If ffprobe fails or cannot parse duration
    """
    process = subprocess.Popen(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    stdout, stderr = process.communicate()
    return_code = process.returncode

    if return_code != 0:
        raise RuntimeError(f"ffprobe failed for '{path.name}': {stderr.strip()}")

    try:
        return float(stdout.strip())
    except ValueError:
        raise RuntimeError(f"Unable to parse duration from ffprobe output: {stdout!r}")


def concatenate_segments(
    source: Path,
    destination: Path,
    segments: Sequence[Tuple[float, float]],
    audio_bitrate: str = "192k",
) -> None:
    """
    Concatenate video segments using stream copy for efficient editing.
    
    This function uses ffmpeg's concat demuxer with stream copy, which allows
    for extremely fast concatenation without re-encoding the video. The audio
    is re-encoded to AAC to ensure perfect synchronization.
    
    **IMPORTANT**: This function requires an all-intra encoded source video
    (e.g., created with 'post -convert'). Using non-intra sources will result
    in visual artifacts at cut points.
    
    Parameters
    ----------
    source:
        Path to the source video (must be all-intra encoded)
    destination:
        Path where the output video will be saved
    segments:
        List of (start_time, end_time) tuples in seconds representing
        the segments to keep and concatenate
    audio_bitrate:
        Audio bitrate for AAC encoding (default: "192k")
        
    Raises
    ------
    ValueError:
        If no segments are provided or all segments are invalid
    RuntimeError:
        If ffmpeg fails during concatenation
        
    Examples
    --------
    >>> concatenate_segments(
    ...     Path("video-intra-rough.mp4"),
    ...     Path("video-intra-rough-cut.mp4"),
    ...     [(0.0, 10.5), (15.2, 30.0), (35.5, 60.0)]
    ... )
    """
    if not segments:
        raise ValueError("No segments provided for concatenation.")

    concat_lines: List[str] = []
    resolved_source = source.resolve()

    def _escape(path: Path) -> str:
        """Escape path for ffmpeg concat file format."""
        safe = str(path).replace("'", "'\\''")
        return f"'{safe}'"

    for start, end in segments:
        if end <= start:
            continue
        concat_lines.append(f"file {_escape(resolved_source)}\n")
        concat_lines.append(f"inpoint {start:.6f}\n")
        concat_lines.append(f"outpoint {end:.6f}\n")

    if not concat_lines:
        raise ValueError("No valid segments remained after filtering.")

    # Create temporary concat file
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".txt"
    ) as concat_file:
        concat_file.writelines(concat_lines)
        concat_path = Path(concat_file.name)

    try:
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            audio_bitrate,
            "-fflags",
            "+genpts",
            "-avoid_negative_ts",
            "make_zero",
            "-movflags",
            "+faststart",
            str(destination),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {result.stderr.strip()}")
    finally:
        concat_path.unlink(missing_ok=True)


def build_keep_segments_from_cuts(
    duration: float,
    cut_ranges: Sequence[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    """
    Convert cut ranges (segments to remove) into keep segments.
    
    This function takes a list of time ranges to remove and calculates
    the inverse - the segments that should be kept in the final video.
    
    Parameters
    ----------
    duration:
        Total duration of the video in seconds
    cut_ranges:
        List of (start, end) tuples representing segments to REMOVE
        
    Returns
    -------
    List[Tuple[float, float]]:
        List of (start, end) tuples representing segments to KEEP
        
    Examples
    --------
    >>> build_keep_segments_from_cuts(100.0, [(10.0, 20.0), (50.0, 60.0)])
    [(0.0, 10.0), (20.0, 50.0), (60.0, 100.0)]
    
    >>> build_keep_segments_from_cuts(100.0, [])
    [(0.0, 100.0)]
    """
    if not cut_ranges:
        return [(0.0, duration)]
    
    # Sort cut ranges by start time
    sorted_cuts = sorted(cut_ranges, key=lambda x: x[0])
    
    keep_segments: List[Tuple[float, float]] = []
    cursor = 0.0
    
    for cut_start, cut_end in sorted_cuts:
        # Clamp cut range to valid bounds
        cut_start = max(0.0, min(cut_start, duration))
        cut_end = max(0.0, min(cut_end, duration))
        
        # If there's a gap between cursor and this cut, keep that segment
        if cursor < cut_start:
            keep_segments.append((cursor, cut_start))
        
        # Move cursor to end of cut
        cursor = max(cursor, cut_end)
    
    # Keep any remaining segment after last cut
    if cursor < duration:
        keep_segments.append((cursor, duration))
    
    # Filter out segments that are too small (< 1ms)
    keep_segments = [(s, e) for s, e in keep_segments if e - s > 1e-3]
    
    return keep_segments if keep_segments else [(0.0, duration)]


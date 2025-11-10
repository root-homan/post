import re
import subprocess
from pathlib import Path

try:
    from .common import StageEnvironment, build_cli_parser
except ImportError:
    from common import StageEnvironment, build_cli_parser


def parse_timestamp(timestamp_str: str) -> float:
    """
    Convert timestamp in MM:SS:MS format to seconds.
    
    Parameters
    ----------
    timestamp_str:
        Timestamp string in format MM:SS:MS (minutes:seconds:milliseconds)
        
    Returns
    -------
    float:
        Time in seconds (with milliseconds as decimal)
    """
    parts = timestamp_str.split(':')
    if len(parts) != 3:
        raise ValueError(f"Invalid timestamp format: {timestamp_str}. Expected MM:SS:MS")
    
    minutes = int(parts[0])
    seconds = int(parts[1])
    milliseconds = int(parts[2])
    
    total_seconds = minutes * 60 + seconds + milliseconds / 100.0
    return total_seconds


def parse_takes_file(txt_path: Path) -> list[tuple[int, float, float]]:
    """
    Parse the takes file to extract take information.
    
    Parameters
    ----------
    txt_path:
        Path to the .txt file containing take timestamps
        
    Returns
    -------
    list[tuple[int, float, float]]:
        List of tuples (take_number, start_time_seconds, end_time_seconds)
    """
    takes = []
    with open(txt_path, 'r') as f:
        content = f.read().strip()
    
    # Parse each line that contains take information
    # Format: <take_number> <start_timestamp> <end_timestamp>
    pattern = r'(\d+)\s+(\d+:\d+:\d+)\s+(\d+:\d+:\d+)'
    matches = re.findall(pattern, content)
    
    for match in matches:
        take_number = int(match[0])
        start_time = parse_timestamp(match[1])
        end_time = parse_timestamp(match[2])
        takes.append((take_number, start_time, end_time))
    
    return takes


def extract_segment(input_video: Path, output_video: Path, start_time: float, end_time: float) -> None:
    """
    Extract a segment from the input video using ffmpeg.
    
    Parameters
    ----------
    input_video:
        Path to the source video file
    output_video:
        Path where the extracted segment should be saved
    start_time:
        Start time in seconds
    end_time:
        End time in seconds
    """
    duration = end_time - start_time
    
    cmd = [
        'ffmpeg',
        '-i', str(input_video),
        '-ss', str(start_time),
        '-t', str(duration),
        '-c', 'copy',
        '-y',  # Overwrite output file if it exists
        str(output_video)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed with error:\n{result.stderr}")


def run(args):
    """
    Extract multiple takes from a video file based on timestamps in a .txt file.
    
    Dependencies:
        - Exactly one .mp4 file named `<title>.mp4` must exist in the target directory.
        - Exactly one .txt file named `<title>.txt` must exist in the target directory.
        - The .txt file should contain take information in the format:
          <take_number> <start_time> <end_time>
          where timestamps are in MM:SS:MS format (minutes:seconds:milliseconds)
          
    Failure behaviour:
        - Exits if the .mp4 or .txt file is missing or if multiple files are found.
        - Exits if the timestamp format in the .txt file is invalid.
        - If a take folder already exists, the user is prompted to allow overwriting
          unless `--yes` is provided.
          
    Output:
        - Creates folders named `take-1`, `take-2`, etc. as siblings to the input files.
        - In each folder, produces `<title>-<take_id>-rough.mp4` containing the extracted segment.
    """
    parser = build_cli_parser(
        stage="cuttakes",
        summary="Extract multiple takes from a video file based on timestamps.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="cuttakes",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    # Find the single .mp4 and .txt file
    video_file = env.expect_single_file("*.mp4", "video file")
    title = video_file.stem
    txt_file = video_file.with_suffix('.txt')
    
    if not txt_file.exists():
        env.abort(f"Expected timestamp file '{txt_file.name}' to exist alongside '{video_file.name}'.")
    
    # Parse the takes from the .txt file
    try:
        takes = parse_takes_file(txt_file)
    except Exception as e:
        env.abort(f"Failed to parse takes file: {e}")
    
    if not takes:
        env.abort(f"No takes found in '{txt_file.name}'. Expected format: <take_number> MM:SS:MS MM:SS:MS")
    
    env.announce_checks_passed(
        f"Found {len(takes)} take(s) in '{txt_file.name}'. Ready to extract segments from '{video_file.name}'."
    )
    
    # Process each take
    for take_number, start_time, end_time in takes:
        take_folder = env.directory / f"take-{take_number}"
        
        # Create the take folder if it doesn't exist
        if take_folder.exists() and not env.auto_confirm:
            answer = input(
                f"Folder '{take_folder.name}' already exists. Continue and overwrite contents? [y/N]: "
            ).strip().lower()
            if answer not in {"y", "yes"}:
                print(f"⏭️  Skipping take {take_number}.")
                continue
        
        take_folder.mkdir(exist_ok=True)
        
        # Create the output video path
        output_video = take_folder / f"{title}-{take_number}-rough.mp4"
        
        print(f"📹 Extracting take {take_number} ({start_time:.2f}s - {end_time:.2f}s) to '{output_video.relative_to(env.directory)}'...")
        
        try:
            extract_segment(video_file, output_video, start_time, end_time)
            print(f"✅ Successfully created '{output_video.relative_to(env.directory)}'")
        except Exception as e:
            print(f"❌ Failed to extract take {take_number}: {e}")
            continue
    
    print(f"🎬 Done! Processed {len(takes)} take(s).")

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List
from openai import OpenAI


def build_cli_parser(stage: str, summary: str) -> argparse.ArgumentParser:
    """
    Create a CLI parser that provides the shared flags across post-production stages.

    Parameters
    ----------
    stage:
        Short stage name that will be shown in the usage banner (e.g. "tighten").
    summary:
        Human readable description that appears in the help text.
    """
    parser = argparse.ArgumentParser(
        prog=f"post -{stage}",
        description=summary,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dir",
        "-d",
        default=".",
        help="Directory containing the take artefacts for this stage.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Automatically overwrite outputs when they already exist.",
    )
    return parser


@dataclass(frozen=True)
class StageEnvironment:
    """
    Encapsulates the filesystem context for a processing stage and centralises safety checks.
    """

    stage: str
    directory: Path
    auto_confirm: bool

    @classmethod
    def create(cls, stage: str, directory: str, auto_confirm: bool) -> "StageEnvironment":
        dir_path = Path(directory).expanduser().resolve()
        if not dir_path.exists():
            print(f"❌ post -{stage}: directory '{dir_path}' does not exist.")
            raise SystemExit(1)
        if not dir_path.is_dir():
            print(f"❌ post -{stage}: '{dir_path}' is not a directory.")
            raise SystemExit(1)
        return cls(stage=stage, directory=dir_path, auto_confirm=auto_confirm)

    def expect_single_file(self, pattern: str, description: str) -> Path:
        """
        Locate a single file matching the provided glob pattern within the stage directory.

        Aborts if zero or multiple files match, preventing accidental processing of the wrong artefact.
        """
        candidates = sorted(self.directory.glob(pattern))
        candidates = [path for path in candidates if path.is_file()]

        if not candidates:
            self.abort(
                f"Expected {description} matching '{pattern}' in '{self.directory}', but nothing was found."
            )

        if len(candidates) > 1:
            names = ", ".join(path.name for path in candidates)
            self.abort(
                f"Found multiple {description}s that match '{pattern}': {names}. "
                "Resolve the ambiguity and run the command again."
            )

        return candidates[0]

    def ensure_output_path(self, output_path: Path) -> Path:
        """
        Confirm that an output path can be written, optionally prompting for overwrite permission.
        """
        if output_path.exists():
            if self.auto_confirm:
                print(f"⚠️  post -{self.stage}: overwriting existing '{output_path.name}' via --yes.")
                return output_path

            answer = input(
                f"post -{self.stage}: '{output_path.name}' already exists. Overwrite? [y/N]: "
            ).strip().lower()
            if answer not in {"y", "yes"}:
                self.abort("User declined to overwrite the existing output.")

        return output_path

    def abort(self, message: str, exit_code: int = 1) -> None:
        print(f"❌ post -{self.stage}: {message}")
        raise SystemExit(exit_code)

    def announce_checks_passed(self, details: str) -> None:
        print(f"🔍 post -{self.stage}: {details}")


def _list_rough_videos(directory: Path) -> List[Path]:
    return [
        path
        for path in sorted(directory.glob("*-rough.mp4"))
        if path.is_file()
    ]


def find_original_rough_video(env: StageEnvironment) -> Path:
    """
    Locate the original rough cut (without '-intra-' inserted).
    """
    candidates = _list_rough_videos(env.directory)
    originals = [path for path in candidates if "-intra-" not in path.stem]

    if not originals:
        env.abort(
            "No original '-rough.mp4' video found. "
            "If you already converted to an intra-frame proxy, rerun with --yes to overwrite."
        )

    if len(originals) > 1:
        names = ", ".join(path.name for path in originals)
        env.abort(
            f"Found multiple rough cuts eligible for conversion: {names}. "
            "Move or rename the extras, then try again."
        )

    return originals[0]


def find_preferred_rough_video(env: StageEnvironment) -> Path:
    """
    Prefer the LONGEST filename ending with '-rough.mp4' to handle multiple rough cuts.
    Prefers intra-frame versions when available.
    """
    candidates = _list_rough_videos(env.directory)

    if not candidates:
        env.abort(
            f"Expected rough cut video matching '*-rough.mp4' in '{env.directory}', but nothing was found."
        )

    # Prefer intra-frame versions
    intra_versions = [path for path in candidates if "-intra-" in path.stem]
    if intra_versions:
        # Return the longest intra-frame filename
        longest = max(intra_versions, key=lambda p: len(p.name))
        if len(intra_versions) > 1:
            print(f"ℹ️  Found {len(intra_versions)} intra-frame rough cuts. Using longest: '{longest.name}'")
        return longest

    # Fall back to originals and return the longest
    originals = [path for path in candidates if "-intra-" not in path.stem]
    if originals:
        longest = max(originals, key=lambda p: len(p.name))
        if len(originals) > 1:
            print(f"ℹ️  Found {len(originals)} rough cuts. Using longest: '{longest.name}'")
        return longest

    env.abort(
        f"No suitable rough cut found in '{env.directory}'."
    )
    raise AssertionError("unreachable")


def call_gpt5(system_prompt: str, user_prompt: str, response_format=None, model: str = "gpt-5", timeout: int = 120) -> str:
    """
    Common function to call GPT-5 API.
    
    Parameters
    ----------
    system_prompt:
        The system message to set the context/instructions.
    user_prompt:
        The user message with the content to process.
    response_format:
        Optional response format specification (e.g., {"type": "json_object"}).
    model:
        The model to use (default: "gpt-5"). Can be "gpt-5-mini" for faster/cheaper responses.
    timeout:
        Request timeout in seconds (default: 120).
        
    Returns
    -------
    str:
        The response content from GPT-5.
        
    Raises
    ------
    SystemExit:
        If OPENAI_API_KEY is not set or API call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable is not set.")
        raise SystemExit(1)
    
    try:
        print(f"🔄 Calling OpenAI API (model: {model}, timeout: {timeout}s)...")
        client = OpenAI(api_key=api_key, timeout=timeout)
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        
        # Debug output
        print(f"✅ API call successful")
        print(f"📊 Response stats: {len(content)} characters, finish_reason: {response.choices[0].finish_reason}")
        
        # Show first 200 chars of response for debugging
        preview = content[:200] + "..." if len(content) > 200 else content
        print(f"📝 Response preview: {preview}")
        
        return content
        
    except TimeoutError as e:
        print(f"❌ OpenAI API call timed out after {timeout}s")
        print(f"   Error details: {e}")
        raise SystemExit(1)
    except Exception as e:
        print(f"❌ OpenAI API call failed")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {e}")
        import traceback
        print(f"   Traceback:")
        traceback.print_exc()
        raise SystemExit(1)



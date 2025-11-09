import argparse
from dataclasses import dataclass
from pathlib import Path


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



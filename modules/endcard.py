from pathlib import Path

from .common import StageEnvironment, build_cli_parser


def run(args):
    """
    Dependencies:
        - Requires a captioned take named `<title>-<take_id>-rough-tight-captions.mp4` in the working directory.
        - Optional Figma-exported endcard assets should reside alongside the video (exact handling TBD).
    Failure behaviour:
        - Exits safely when the captioned video is missing or when multiple candidates are discovered.
        - Prompts before overwriting `<title>-<take_id>-rough-tight-captions-withclosing.mp4`
          unless `--yes` is supplied.
    Output:
        - Produces `<title>-<take_id>-rough-tight-captions-withclosing.mp4`, appending an endcard/closing scene
          to the captioned take.
    """
    parser = build_cli_parser(
        stage="endcard",
        summary="Append the designed closing scene to the captioned take.",
    )
    parser.add_argument(
        "--assets",
        type=Path,
        default=None,
        help="Optional directory containing exported endcard assets.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="endcard",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    captioned_video = env.expect_single_file(
        "*-rough-tight-captions.mp4", "captioned video with burnt-in captions"
    )
    final_video = captioned_video.with_name(f"{captioned_video.stem}-withclosing.mp4")

    env.ensure_output_path(final_video)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to append endcard assets to '{captioned_video.name}' "
        f"and export '{final_video.name}'."
    )


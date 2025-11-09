from .common import StageEnvironment, build_cli_parser


def run(args):
    """
    Dependencies:
        - Requires one tightened video named `<title>-<take_id>-rough-tight.mp4` in the working directory.
    Failure behaviour:
        - Aborts when the tightened video is missing or when multiple candidates are present.
        - Prompts before overwriting an existing `<title>-<take_id>-rough-tight.srt` unless `--yes` is supplied.
    Output:
        - Produces `<title>-<take_id>-rough-tight.srt`, sharing the exact basename with the tightened video but
          switching the extension to `.srt`.
    """
    parser = build_cli_parser(
        stage="srt",
        summary="Generate an SRT subtitle file from the tightened take.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="srt",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    tightened_video = env.expect_single_file("*-rough-tight.mp4", "tightened video")
    srt_file = tightened_video.with_suffix(".srt")

    env.ensure_output_path(srt_file)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to derive subtitles '{srt_file.name}' from '{tightened_video.name}'."
    )


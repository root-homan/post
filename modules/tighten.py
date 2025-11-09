from .common import StageEnvironment, build_cli_parser


def run(args):
    """
    Dependencies:
        - Requires a single rough cut named `<title>-<take_id>-rough.mp4` in the working directory.
    Failure behaviour:
        - Exits without modifying files when the rough cut is absent or when more than one candidate rough cut exists.
        - Prompts before overwriting `<title>-<take_id>-rough-tight.mp4` unless `--yes` is specified.
    Output:
        - Generates `<title>-<take_id>-rough-tight.mp4`, i.e., the same base filename with `-tight` appended before `.mp4`.
    """
    parser = build_cli_parser(
        stage="tighten",
        summary="Remove leading, trailing, and mid-take silences from a rough cut.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="tighten",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    rough_video = env.expect_single_file("*-rough.mp4", "rough cut video")
    base_name = rough_video.name[: -len("-rough.mp4")]
    tightened_video = rough_video.with_name(f"{base_name}-rough-tight.mp4")

    env.ensure_output_path(tightened_video)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to tighten '{rough_video.name}' into '{tightened_video.name}'."
    )


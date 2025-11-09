from .common import StageEnvironment, build_cli_parser


def run(args):
    """
    Dependencies:
        - Exactly one raw capture named `<title>-<take_id>-raw.mp4` must exist in the target directory.
        - Any per-take metadata (e.g., JSON of in/out points) should live alongside the raw capture
          and will be consumed in a future implementation.
    Failure behaviour:
        - Exits without side effects when the raw file is missing or when multiple raw captures are detected.
        - If a derived `<title>-<take_id>-rough.mp4` already exists, the user is prompted to allow overwriting
          unless `--yes` is provided.
    Output:
        - Produces `<title>-<take_id>-rough.mp4` (4:3 aspect) for the take; the filename keeps the same base name
          as the raw capture, replacing the `-raw` suffix with `-rough`.
    """
    parser = build_cli_parser(
        stage="cut",
        summary="Extract a single take from the raw capture and adapt it to 4:3.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="cut",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    raw_video = env.expect_single_file("*-raw.mp4", "raw source video")
    base_name = raw_video.name[: -len("-raw.mp4")]
    rough_video = raw_video.with_name(f"{base_name}-rough.mp4")

    env.ensure_output_path(rough_video)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to derive '{rough_video.name}' from '{raw_video.name}'."
    )


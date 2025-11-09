from .common import StageEnvironment, build_cli_parser


def run(args):
    """
    Dependencies:
        - A tightened video `<title>-<take_id>-rough-tight.mp4` must be present in the working directory.
        - A matching subtitle file `<title>-<take_id>-rough-tight.srt` (same basename as the video) must exist.
    Failure behaviour:
        - Aborts when either artefact is missing, when multiple candidates exist, or when the basenames differ.
        - Prompts before overwriting `<title>-<take_id>-rough-tight-captions.mp4` unless `--yes` is provided.
    Output:
        - Produces `<title>-<take_id>-rough-tight-captions.mp4`, augmenting the tightened video with burnt-in captions.
    """
    parser = build_cli_parser(
        stage="captions",
        summary="Render the tightened take with burnt-in captions from the SRT file.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="captions",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    tightened_video = env.expect_single_file("*-rough-tight.mp4", "tightened video")
    srt_file = env.expect_single_file("*-rough-tight.srt", "subtitle file required for captions")

    if tightened_video.stem != srt_file.stem:
        env.abort(
            "Subtitle file and video do not share the same basename. "
            f"Expected '{tightened_video.stem}', found '{srt_file.stem}'."
        )

    captions_video = tightened_video.with_name(f"{tightened_video.stem}-captions.mp4")

    env.ensure_output_path(captions_video)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to render '{captions_video.name}' using '{tightened_video.name}' and '{srt_file.name}'."
    )


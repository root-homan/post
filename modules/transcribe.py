from .common import StageEnvironment, build_cli_parser


def run(args):
    """
    Dependencies:
        - Needs a single subtitle file named `<title>-<take_id>-rough-tight.srt` in the target directory.
    Failure behaviour:
        - Exits safely when the subtitle file is missing or when multiple candidates are detected.
        - Prompts before overwriting `<title>-<take_id>-rough-tight-transcription.txt` unless `--yes` is passed.
    Output:
        - Produces `<title>-<take_id>-rough-tight-transcription.txt`, i.e., the SRT basename with
          `-transcription.txt` appended.
    """
    parser = build_cli_parser(
        stage="transcribe",
        summary="Build a human-friendly transcript from the SRT captions.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="transcribe",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    srt_file = env.expect_single_file("*-rough-tight.srt", "subtitle file")
    transcription = srt_file.with_name(f"{srt_file.stem}-transcription.txt")

    env.ensure_output_path(transcription)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to write transcript '{transcription.name}' from '{srt_file.name}'."
    )


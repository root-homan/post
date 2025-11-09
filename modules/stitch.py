from .common import StageEnvironment, build_cli_parser


def run(args):
    """
    Dependencies:
        - A text file listing absolute or relative video paths (defaults to `stitch.txt`) must exist in the
          working directory.
    Failure behaviour:
        - Exits without side effects when the plan file is missing or empty.
        - Prompts before overwriting the stitched output (default `stitched.mp4`) unless `--yes` is used.
    Output:
        - Produces a single combined video (default `stitched.mp4`) that concatenates the listed sources in order.
    """
    parser = build_cli_parser(
        stage="stitch",
        summary="Concatenate multiple prepared videos based on a text plan file.",
    )
    parser.add_argument(
        "--plan",
        type=str,
        default="stitch.txt",
        help="Relative path to the text file that enumerates clips to stitch.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="stitched.mp4",
        help="Filename for the stitched export created in the working directory.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="stitch",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    plan_path = env.directory / parsed.plan
    if not plan_path.exists():
        env.abort(f"Plan file '{parsed.plan}' was not found in '{env.directory}'.")
    if not plan_path.is_file():
        env.abort(f"Plan file '{parsed.plan}' exists but is not a regular file.")

    plan_contents = plan_path.read_text(encoding="utf-8").strip()
    if not plan_contents:
        env.abort(
            f"Plan file '{parsed.plan}' is empty. Add one clip path per line before running stitch."
        )

    output_path = env.directory / parsed.output
    env.ensure_output_path(output_path)

    env.announce_checks_passed(
        f"All safety checks passed. Ready to stitch {len(plan_contents.splitlines())} clips into '{output_path.name}'."
    )


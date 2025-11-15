import json
from pathlib import Path

try:
    from .common import StageEnvironment, build_cli_parser, call_gpt5
except ImportError:
    from common import StageEnvironment, build_cli_parser, call_gpt5


def run(args):
    """
    Dependencies:
        - Needs a single word timestamps file named `<title>-<take_id>-rough-tight.json` in the target directory.
        - Needs a matching subtitle file `<title>-<take_id>-rough-tight.srt` in the target directory.
        - Requires OPENAI_API_KEY environment variable to be set.
    Failure behaviour:
        - Exits safely when the timestamps or subtitle file is missing or when multiple candidates are detected.
        - Aborts if OPENAI_API_KEY is not set.
        - Prompts before overwriting `<title>-<take_id>-rough-tight-essay.txt` unless `--yes` is passed.
    Output:
        - Produces `<title>-<take_id>-rough-tight-essay.txt`, i.e., the JSON basename with
          `-essay.txt` appended.
    """
    parser = build_cli_parser(
        stage="essay",
        summary="Build a human-friendly essay/transcript from the word timestamps.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="essay",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    # Find the JSON and SRT files
    json_file = env.expect_single_file("*-rough-tight.json", "word timestamps file")
    srt_file = env.expect_single_file("*-rough-tight.srt", "subtitle SRT file")

    if json_file.stem != srt_file.stem:
        env.abort(
            "Word timestamps file and subtitle file do not share the same basename. "
            f"Expected '{json_file.stem}', found '{srt_file.stem}'."
        )

    essay_file = json_file.with_name(f"{json_file.stem}-essay.txt")

    env.ensure_output_path(essay_file)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to write essay '{essay_file.name}' from '{srt_file.name}'."
    )

    # Read the JSON file to sanity check availability of word timestamps
    print(f"📖 post -essay: reading word timestamps from '{json_file.name}'...")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            word_data = json.load(f)
        if not isinstance(word_data, list):
            env.abort("Word timestamps JSON is not a list.")
        print(f"📘 post -essay: verified word timestamps file contains {len(word_data)} entries.")
    except Exception as e:
        env.abort(f"Failed to read JSON file: {e}")

    # Read the SRT file to feed into GPT
    print(f"🎞️ post -essay: reading subtitles from '{srt_file.name}'...")
    try:
        srt_content = srt_file.read_text(encoding="utf-8")
        if not srt_content.strip():
            env.abort(f"Subtitle file '{srt_file.name}' is empty.")
    except Exception as e:
        env.abort(f"Failed to read SRT file: {e}")

    # Read the feedback guidelines
    guidelines_path = Path(__file__).parent / "feedback-guidelines.md"
    if not guidelines_path.exists():
        env.abort(f"Feedback guidelines not found at '{guidelines_path}'")
    
    print(f"📖 post -essay: reading feedback guidelines...")
    try:
        guidelines_content = guidelines_path.read_text(encoding="utf-8")
    except Exception as e:
        env.abort(f"Failed to read feedback guidelines: {e}")

    # Make API call to OpenAI
    print(f"🤖 post -essay: calling GPT-5 API...")
    print(f"📤 post -essay: sending {len(srt_content)} characters of SRT content...")
    try:
        essay_content = call_gpt5(
            system_prompt=guidelines_content,
            user_prompt=(
                "Please process the following subtitle file (SRT format) according to the format "
                "specified in your guidelines:\n\n"
                f"{srt_content}"
            ),
            timeout=180  # 3 minutes for longer transcripts
        )
    except SystemExit:
        env.abort("GPT-5 API call failed")

    # Write the essay output
    print(f"💾 post -essay: writing essay to '{essay_file.name}'...")
    try:
        essay_file.write_text(essay_content, encoding="utf-8")
        print(f"✅ post -essay: successfully created '{essay_file.name}'")
    except Exception as e:
        env.abort(f"Failed to write essay file: {e}")

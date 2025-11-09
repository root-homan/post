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
        - Requires OPENAI_API_KEY environment variable to be set.
    Failure behaviour:
        - Exits safely when the timestamps file is missing or when multiple candidates are detected.
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

    # Find the JSON file
    json_file = env.expect_single_file("*-rough-tight.json", "word timestamps file")
    essay_file = json_file.with_name(f"{json_file.stem}-essay.txt")

    env.ensure_output_path(essay_file)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to write essay '{essay_file.name}' from '{json_file.name}'."
    )

    # Read the JSON file and convert to transcript text
    print(f"📖 post -essay: reading word timestamps from '{json_file.name}'...")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            words = json.load(f)
        
        # Convert word list to a simple transcript text
        transcript_text = ' '.join(word['word'] for word in words)
        
    except Exception as e:
        env.abort(f"Failed to read JSON file: {e}")

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
    try:
        essay_content = call_gpt5(
            system_prompt=guidelines_content,
            user_prompt=f"Please process this video transcript according to the format specified in your guidelines:\n\n{transcript_text}"
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

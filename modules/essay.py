import os
from pathlib import Path
from openai import OpenAI

try:
    from .common import StageEnvironment, build_cli_parser
except ImportError:
    from common import StageEnvironment, build_cli_parser


def run(args):
    """
    Dependencies:
        - Needs a single subtitle file named `<title>-<take_id>-rough-tight.srt` in the target directory.
        - Requires OPENAI_API_KEY environment variable to be set.
    Failure behaviour:
        - Exits safely when the subtitle file is missing or when multiple candidates are detected.
        - Aborts if OPENAI_API_KEY is not set.
        - Prompts before overwriting `<title>-<take_id>-rough-tight-essay.txt` unless `--yes` is passed.
    Output:
        - Produces `<title>-<take_id>-rough-tight-essay.txt`, i.e., the SRT basename with
          `-essay.txt` appended.
    """
    parser = build_cli_parser(
        stage="essay",
        summary="Build a human-friendly essay/transcript from the SRT captions.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="essay",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        env.abort("OPENAI_API_KEY environment variable is not set.")

    # Find the SRT file
    srt_file = env.expect_single_file("*-rough-tight.srt", "subtitle file")
    essay_file = srt_file.with_name(f"{srt_file.stem}-essay.txt")

    env.ensure_output_path(essay_file)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to write essay '{essay_file.name}' from '{srt_file.name}'."
    )

    # Read the SRT file content
    print(f"📖 post -essay: reading SRT file '{srt_file.name}'...")
    try:
        srt_content = srt_file.read_text(encoding="utf-8")
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
    print(f"🤖 post -essay: calling OpenAI API...")
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-5",  # or "gpt-4-turbo" or whichever model you prefer
            messages=[
                {
                    "role": "system",
                    "content": guidelines_content
                },
                {
                    "role": "user",
                    "content": f"Please process this video transcript according to the format specified in your guidelines:\n\n{srt_content}"
                }
            ],
        )
        
        essay_content = response.choices[0].message.content
        
    except Exception as e:
        env.abort(f"OpenAI API call failed: {e}")

    # Write the essay output
    print(f"💾 post -essay: writing essay to '{essay_file.name}'...")
    try:
        essay_file.write_text(essay_content, encoding="utf-8")
        print(f"✅ post -essay: successfully created '{essay_file.name}'")
    except Exception as e:
        env.abort(f"Failed to write essay file: {e}")

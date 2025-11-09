import sys
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

try:
    from .common import StageEnvironment, build_cli_parser
    from . import tighten, transcribe, essay, captions
except ImportError:
    from common import StageEnvironment, build_cli_parser
    import tighten, transcribe, essay, captions


def check_completion_status(directory: Path, rough_video: Path):
    """
    Check which steps are complete.
    
    Returns a dict with keys: 'tighten', 'transcribe', 'essay', 'captions'
    Each value is the Path to the output file if complete, or None if not.
    """
    base_name = rough_video.name[:-len("-rough.mp4")]
    
    status = {
        'tighten': None,
        'transcribe': None,
        'essay': None,
        'captions': None
    }
    
    # Check for tightened video
    tight_video = directory / f"{base_name}-rough-tight.mp4"
    if tight_video.exists():
        status['tighten'] = tight_video
    
    # Check for transcription
    json_file = directory / f"{base_name}-rough-tight.json"
    if json_file.exists():
        status['transcribe'] = json_file
    
    # Check for essay
    essay_file = directory / f"{base_name}-rough-tight-essay.txt"
    if essay_file.exists():
        status['essay'] = essay_file
    
    # Check for final captioned video
    captions_file = directory / f"{base_name}-rough-tight-captions.mp4"
    if captions_file.exists():
        status['captions'] = captions_file
    
    return status


def prompt_rerun(step_name: str, file_path: Path, auto_confirm: bool) -> bool:
    """
    Ask user if they want to rerun a completed step.
    
    Returns True if user wants to rerun, False to skip.
    """
    if auto_confirm:
        print(f"⚠️  Step '{step_name}' already complete (output: '{file_path.name}'). Auto-confirming overwrite via --yes.")
        return True
    
    print(f"✓ Step '{step_name}' already complete (output: '{file_path.name}').")
    response = input(f"Do you want to re-run '{step_name}'? [y/N]: ").strip().lower()
    return response in ('y', 'yes')


def run(args):
    """
    Process a rough video through all post-production steps.
    
    This command orchestrates the full pipeline:
    1. tighten - Remove silence from video
    2. transcribe - Generate word-level timestamps
    3. essay - Generate essay/transcript from timestamps
    4. captions - Add captions to video
    
    Dependencies:
        - Requires a single rough cut named `<title>-<take_id>-rough.mp4` in the working directory.
        - All dependencies required by individual steps (ffmpeg, stable-ts, node.js, OPENAI_API_KEY).
    
    Behavior:
        - Checks which steps are already complete
        - For completed steps, prompts whether to re-run (unless --yes is provided)
        - For incomplete steps, runs them in order
        - If all steps are complete, prompts whether to re-run the entire pipeline
    
    Output:
        - Produces all intermediate and final outputs from the pipeline:
          - `<title>-<take_id>-rough-tight.mp4` (tightened video)
          - `<title>-<take_id>-rough-tight.json` (word timestamps)
          - `<title>-<take_id>-rough-tight-essay.txt` (essay/transcript)
          - `<title>-<take_id>-rough-tight-captions.mp4` (final captioned video)
    """
    parser = build_cli_parser(
        stage="process",
        summary="Run the complete post-production pipeline from rough cut to captioned video.",
    )
    parsed = parser.parse_args(args)
    
    env = StageEnvironment.create(
        stage="process",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )
    
    # Find the rough video
    rough_video = env.expect_single_file("*-rough.mp4", "rough cut video")
    
    print(f"🔍 post -process: analyzing completion status for '{rough_video.name}'...")
    status = check_completion_status(env.directory, rough_video)
    
    # Determine what needs to be done
    steps_to_run = []
    
    # Check each step in order
    if status['tighten'] is None:
        print(f"⏭  Step 'tighten' not complete. Will run.")
        steps_to_run.append('tighten')
    elif prompt_rerun('tighten', status['tighten'], env.auto_confirm):
        steps_to_run.append('tighten')
    
    if status['transcribe'] is None:
        print(f"⏭  Step 'transcribe' not complete. Will run.")
        steps_to_run.append('transcribe')
    elif prompt_rerun('transcribe', status['transcribe'], env.auto_confirm):
        steps_to_run.append('transcribe')
    
    if status['essay'] is None:
        print(f"⏭  Step 'essay' not complete. Will run.")
        steps_to_run.append('essay')
    elif prompt_rerun('essay', status['essay'], env.auto_confirm):
        steps_to_run.append('essay')
    
    if status['captions'] is None:
        print(f"⏭  Step 'captions' not complete. Will run.")
        steps_to_run.append('captions')
    elif prompt_rerun('captions', status['captions'], env.auto_confirm):
        steps_to_run.append('captions')
    
    # If nothing to run, we're done
    if not steps_to_run:
        print(f"✅ post -process: All steps complete! No work to do.")
        print(f"📹 Final output: '{status['captions'].name}'")
        return
    
    # Show execution plan
    print(f"\n📋 post -process: Execution plan:")
    for step in steps_to_run:
        print(f"   • {step}")
    print()
    
    # Prepare common arguments for sub-commands
    sub_args = ["--dir", str(env.directory)]
    if env.auto_confirm:
        sub_args.append("--yes")
    
    # Run each step in sequence
    for step in steps_to_run:
        print(f"\n{'='*80}")
        print(f"🚀 post -process: Starting step '{step}'...")
        print(f"{'='*80}\n")
        
        try:
            if step == 'tighten':
                tighten.run(sub_args)
            elif step == 'transcribe':
                # Add default model for transcribe if not specified
                transcribe.run(sub_args)
            elif step == 'essay':
                essay.run(sub_args)
            elif step == 'captions':
                captions.run(sub_args)
            
            print(f"\n✅ post -process: Step '{step}' completed successfully!")
        
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, KeyboardInterrupt):
                print(f"\n⚠️  post -process: Interrupted by user during '{step}'.")
            else:
                print(f"\n❌ post -process: Step '{step}' failed.")
            print(f"You can re-run 'post -process' to continue from where you left off.")
            raise
        except Exception as e:
            print(f"\n❌ post -process: Step '{step}' failed with error: {e}")
            print(f"You can re-run 'post -process' to continue from where you left off.")
            raise SystemExit(1)
    
    # All steps complete!
    print(f"\n{'='*80}")
    print(f"🎉 post -process: All steps completed successfully!")
    print(f"{'='*80}\n")
    
    # Show final outputs
    final_status = check_completion_status(env.directory, rough_video)
    print(f"📦 Generated outputs:")
    if final_status['tighten']:
        print(f"   • {final_status['tighten'].name} (tightened video)")
    if final_status['transcribe']:
        print(f"   • {final_status['transcribe'].name} (word timestamps)")
    if final_status['essay']:
        print(f"   • {final_status['essay'].name} (essay/transcript)")
    if final_status['captions']:
        print(f"   • {final_status['captions'].name} (final captioned video)")
    
    print(f"\n✨ Your captioned video is ready: '{final_status['captions'].name}'")


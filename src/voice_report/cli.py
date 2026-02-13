"""CLI entry point for voice-report."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing_extensions import Annotated

from voice_report.audio import check_ffmpeg, get_audio_duration, validate_audio_file
from voice_report.config import Settings
from voice_report.models import TranscriptResult
from voice_report.report import generate_report, load_template
from voice_report.transcribe import transcribe_audio

app = typer.Typer(
    name="voice-report",
    help="Convert voice recordings into structured meeting reports.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def convert(
    audio_file: Annotated[
        Path,
        typer.Argument(help="Path to the audio file (.m4a, .wav, .mp3)"),
    ],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output file path (default: <input>.md)"),
    ] = None,
    model: Annotated[
        str,
        typer.Option("--model", "-m", help="Whisper model size"),
    ] = "large-v2",
    language: Annotated[
        str,
        typer.Option("--lang", "-l", help="Language code (e.g. ko, en)"),
    ] = "ko",
    prompt: Annotated[
        Optional[str],
        typer.Option("--prompt", "-p", help="Custom instruction for report generation"),
    ] = None,
    template: Annotated[
        Optional[str],
        typer.Option("--template", "-t", help="Prompt template name from templates/ directory"),
    ] = None,
    speakers: Annotated[
        Optional[str],
        typer.Option(
            "--speakers",
            "-s",
            help="Speaker name mapping: 'SPEAKER_00:Name,SPEAKER_01:Name'",
        ),
    ] = None,
    gemini_model: Annotated[
        str,
        typer.Option("--gemini-model", help="Gemini model for report generation"),
    ] = "gemini-2.0-flash",
    device: Annotated[
        str,
        typer.Option("--device", "-d", help="Compute device: cuda, cpu"),
    ] = "cpu",
    no_diarize: Annotated[
        bool,
        typer.Option("--no-diarize", help="Skip speaker diarization"),
    ] = False,
    transcript_only: Annotated[
        bool,
        typer.Option("--transcript-only", help="Output transcript without generating report"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging"),
    ] = False,
) -> None:
    """Convert a voice recording into a meeting report."""
    if prompt and template:
        console.print("[red]Error: --prompt and --template are mutually exclusive.[/red]")
        raise typer.Exit(code=1)

    # Validate audio file
    try:
        validate_audio_file(audio_file)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

    if not check_ffmpeg():
        console.print(
            "[red]Error: ffmpeg is not installed.[/red]\n"
            "Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Ubuntu)"
        )
        raise typer.Exit(code=1)

    settings = Settings()

    # Check API keys
    if not transcript_only and not settings.gemini_api_key:
        console.print(
            "[red]Error: GEMINI_API_KEY not set.[/red]\n"
            "Get your key at: https://aistudio.google.com/apikey\n"
            "Add it to .env file or set as environment variable."
        )
        raise typer.Exit(code=1)

    if not no_diarize and not settings.hf_token:
        console.print(
            "[yellow]Warning: HF_TOKEN not set. Skipping speaker diarization.[/yellow]\n"
            "To enable diarization, get a token at: https://huggingface.co/settings/tokens\n"
            "You must also accept model agreements at:\n"
            "  https://huggingface.co/pyannote/segmentation-3.0\n"
            "  https://huggingface.co/pyannote/speaker-diarization-3.1"
        )
        no_diarize = True

    if verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    # Set output path
    if output is None:
        output = audio_file.with_suffix(".txt" if transcript_only else ".md")

    # Show audio info
    try:
        duration = get_audio_duration(audio_file)
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        console.print(f"Audio: {audio_file.name} ({minutes}m {seconds}s)")
    except Exception:
        console.print(f"Audio: {audio_file.name}")

    speaker_map = _parse_speaker_map(speakers) if speakers else None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Step 1: Transcribe
        task = progress.add_task("Transcribing audio...", total=None)
        transcript_result = transcribe_audio(
            audio_path=audio_file,
            model_size=model,
            language=language,
            device=device,
            diarize=not no_diarize,
            hf_token=settings.hf_token,
        )
        progress.update(task, completed=True, description="Transcription complete")

        if not transcript_result.segments:
            console.print("[yellow]No speech detected in audio file.[/yellow]")
            raise typer.Exit(code=0)

        if transcript_only:
            text = transcript_result.to_text(speaker_map=speaker_map)
            output.write_text(text, encoding="utf-8")
            console.print(f"\n[green]Transcript saved to {output}[/green]")
            return

        # Step 2: Generate report
        task = progress.add_task("Generating meeting report...", total=None)

        system_prompt = None
        if prompt:
            system_prompt = prompt
        elif template:
            try:
                system_prompt = load_template(template)
            except FileNotFoundError as e:
                console.print(f"[red]Error: {e}[/red]")
                raise typer.Exit(code=1)

        transcript_text = transcript_result.to_text(speaker_map=speaker_map)

        try:
            report = generate_report(
                transcript=transcript_text,
                api_key=settings.gemini_api_key,
                system_prompt=system_prompt,
                model=gemini_model,
            )
        except Exception as e:
            console.print(f"[red]Gemini API error: {e}[/red]")
            console.print("[yellow]Saving transcript as fallback...[/yellow]")
            fallback = audio_file.with_suffix(".txt")
            fallback.write_text(transcript_text, encoding="utf-8")
            console.print(f"Transcript saved to {fallback}")
            raise typer.Exit(code=1)

        progress.update(task, completed=True, description="Report generated")

    output.write_text(report, encoding="utf-8")
    console.print(f"\n[green]Report saved to {output}[/green]")


def _parse_speaker_map(raw: str) -> dict[str, str]:
    """Parse 'SPEAKER_00:Name,SPEAKER_01:Name' into a dict."""
    result = {}
    for pair in raw.split(","):
        key, _, value = pair.partition(":")
        if key.strip() and value.strip():
            result[key.strip()] = value.strip()
    return result


if __name__ == "__main__":
    app()

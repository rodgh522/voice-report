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


@app.callback()
def main():
    """
    Voice Report CLI
    """


@app.command()
def version():
    """Show the version and exit."""
    from voice_report import __version__
    console.print(f"voice-report version: {__version__}")


@app.command()
def convert(
    input_file: Annotated[
        Path,
        typer.Argument(help="Path to the input file (audio or .txt transcript)"),
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
    ] = "gemini-2.5-flash",
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
    is_text_input = input_file.suffix.lower() == ".txt"

    if prompt and template:
        console.print("[red]Error: --prompt and --template are mutually exclusive.[/red]")
        raise typer.Exit(code=1)

    if is_text_input:
        if not input_file.exists() or not input_file.is_file():
            console.print(f"[red]Error: Transcript file not found: {input_file}[/red]")
            raise typer.Exit(code=1)
    else:
        # Validate audio file
        try:
            validate_audio_file(input_file)
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

    if not is_text_input and not no_diarize and not settings.hf_token:
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

    # Set output paths
    if output is None:
        output_dir = Path("result") / input_file.stem
        output_dir.mkdir(parents=True, exist_ok=True)
        txt_out = output_dir / f"{input_file.stem}.txt"
        md_out = output_dir / f"{input_file.stem}.md"
    else:
        if output.is_dir() or not output.suffix:
            output.mkdir(parents=True, exist_ok=True)
            txt_out = output / f"{input_file.stem}.txt"
            md_out = output / f"{input_file.stem}.md"
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            txt_out = output.with_suffix(".txt")
            md_out = output.with_suffix(".md")

    if is_text_input:
        console.print(f"Transcript: {input_file.name}")
    else:
        # Show audio info
        try:
            duration = get_audio_duration(input_file)
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            console.print(f"Audio: {input_file.name} ({minutes}m {seconds}s)")
        except Exception:
            console.print(f"Audio: {input_file.name}")

    speaker_map = _parse_speaker_map(speakers) if speakers else None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        if is_text_input:
            transcript_text = input_file.read_text(encoding="utf-8")
        else:
            # Step 1: Transcribe
            task = progress.add_task("Transcribing audio...", total=None)
            transcript_result = transcribe_audio(
                audio_path=input_file,
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

            transcript_text = transcript_result.to_text(speaker_map=speaker_map)
            txt_out.write_text(transcript_text, encoding="utf-8")
            console.print(f"[green]Transcript saved to {txt_out}[/green]")

            if transcript_only:
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
        else:
            try:
                system_prompt = load_template("default")
            except FileNotFoundError:
                pass

        try:
            report = generate_report(
                transcript=transcript_text,
                api_key=settings.gemini_api_key,
                system_prompt=system_prompt,
                model=gemini_model,
            )
        except Exception as e:
            console.print(f"[red]Gemini API error: {e}[/red]")
            raise typer.Exit(code=1)

        progress.update(task, completed=True, description="Report generated")

    md_out.write_text(report, encoding="utf-8")
    console.print(f"[green]Report saved to {md_out}[/green]")


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

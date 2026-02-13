"""WhisperX transcription with alignment and optional diarization."""

import gc
from pathlib import Path

import whisperx

from voice_report.models import Segment, TranscriptResult, Word


def transcribe_audio(
    audio_path: Path,
    model_size: str = "large-v2",
    language: str = "ko",
    device: str = "cpu",
    batch_size: int = 16,
    diarize: bool = True,
    hf_token: str = "",
) -> TranscriptResult:
    """Transcribe audio file using WhisperX with optional diarization."""
    compute_type = "float16" if device == "cuda" else "int8"
    if device == "cpu":
        batch_size = min(batch_size, 4)

    # 1. Load and transcribe
    model = whisperx.load_model(
        model_size,
        device,
        compute_type=compute_type,
        language=language,
    )
    audio = whisperx.load_audio(str(audio_path))
    result = model.transcribe(audio, batch_size=batch_size, language=language)

    del model
    gc.collect()

    # 2. Align for word-level timestamps
    try:
        model_a, metadata = whisperx.load_align_model(
            language_code=language,
            device=device,
        )
        result = whisperx.align(
            result["segments"],
            model_a,
            metadata,
            audio,
            device,
            return_char_alignments=False,
        )
        del model_a
        gc.collect()
    except Exception:
        # Alignment model may not be available for all languages
        pass

    # 3. Diarize (speaker identification)
    if diarize and hf_token:
        diarize_model = whisperx.DiarizationPipeline(
            use_auth_token=hf_token,
            device=device,
        )
        diarize_segments = diarize_model(audio)
        result = whisperx.assign_word_speakers(diarize_segments, result)
        del diarize_model
        gc.collect()

    # 4. Convert to data model
    return _to_transcript_result(result, language)


def _to_transcript_result(result: dict, language: str) -> TranscriptResult:
    """Convert WhisperX output dict to TranscriptResult."""
    segments = []
    for seg in result.get("segments", []):
        words = [
            Word(
                text=w.get("word", ""),
                start=w.get("start", 0.0),
                end=w.get("end", 0.0),
                speaker=w.get("speaker", ""),
            )
            for w in seg.get("words", [])
        ]
        segments.append(
            Segment(
                start=seg.get("start", 0.0),
                end=seg.get("end", 0.0),
                text=seg.get("text", ""),
                speaker=seg.get("speaker", ""),
                words=words,
            )
        )
    return TranscriptResult(segments=segments, language=language)

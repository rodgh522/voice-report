"""Data models for transcription results."""

from dataclasses import dataclass, field


@dataclass
class Word:
    text: str
    start: float
    end: float
    speaker: str = ""


@dataclass
class Segment:
    start: float
    end: float
    text: str
    speaker: str = ""
    words: list[Word] = field(default_factory=list)


@dataclass
class TranscriptResult:
    segments: list[Segment]
    language: str = "ko"

    def to_text(self, speaker_map: dict[str, str] | None = None) -> str:
        """Format transcript as readable text with speaker labels and timestamps."""
        lines = []
        current_speaker = None
        for seg in self.segments:
            timestamp = f"[{_format_time(seg.start)} - {_format_time(seg.end)}]"
            speaker_label = seg.speaker
            if speaker_map and seg.speaker in speaker_map:
                speaker_label = speaker_map[seg.speaker]

            if seg.speaker and seg.speaker != current_speaker:
                current_speaker = seg.speaker
                lines.append(f"\n{speaker_label} {timestamp}")
            else:
                lines.append(timestamp)
            lines.append(f"  {seg.text}")
        return "\n".join(lines).strip()


def _format_time(seconds: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

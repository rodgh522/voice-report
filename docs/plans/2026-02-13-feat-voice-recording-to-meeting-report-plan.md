---
title: "feat: Voice Recording to Meeting Report CLI"
type: feat
date: 2026-02-13
---

# Voice Recording to Meeting Report CLI

## Overview

Build a Python CLI tool (`voice-report`) that converts voice recordings (.m4a, .wav, .mp3) of meetings into structured markdown reports. The pipeline: audio -> WhisperX (local speech-to-text with speaker diarization) -> Google Gemini (report generation with custom prompts) -> markdown output.

## Problem Statement / Motivation

Meeting recordings are time-consuming to review manually. This tool automates the transcription and report generation process, producing structured reports with speaker attribution, action items, and key decisions -- all from a single CLI command.

## Proposed Solution

A modular Python CLI with 3 core stages:

1. **Transcribe** - WhisperX converts audio to text with word-level timestamps
2. **Diarize** - Speaker identification assigns labels (SPEAKER_00, SPEAKER_01, etc.)
3. **Report** - Gemini generates a structured markdown report from the diarized transcript

### User Flows

```bash
# Full pipeline with defaults
voice-report convert recording.m4a

# Custom inline prompt
voice-report convert recording.m4a --prompt "summarize in bullet points"

# Use saved template
voice-report convert recording.m4a --template standup

# Transcript only (no Gemini)
voice-report convert recording.m4a --transcript-only

# Skip speaker diarization
voice-report convert recording.m4a --no-diarize

# Custom output path
voice-report convert recording.m4a -o report.md

# Map speaker names
voice-report convert recording.m4a --speakers "SPEAKER_00:Kim,SPEAKER_01:Lee"

# GPU acceleration
voice-report convert recording.m4a --device cuda
```

## Technical Approach

### Architecture

```
voice-report/
├── pyproject.toml                # PEP 621 project metadata + deps
├── .env.example                  # Template for required env vars
├── .gitignore
├── src/
│   └── voice_report/
│       ├── __init__.py
│       ├── cli.py                # Typer CLI entry point
│       ├── transcribe.py         # WhisperX transcription + alignment
│       ├── diarize.py            # Speaker diarization (pyannote via WhisperX)
│       ├── report.py             # Gemini report generation
│       ├── audio.py              # Audio validation + preprocessing
│       ├── config.py             # Settings from .env (pydantic-settings)
│       └── models.py             # Data models (Segment, Word, TranscriptResult)
├── templates/                    # Reusable prompt templates
│   └── default.txt              # Default meeting report prompt (Korean)
└── tests/
    ├── conftest.py
    ├── test_cli.py
    ├── test_transcribe.py
    └── test_report.py
```

### Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| CLI Framework | **Typer** (with Rich) | Type-hint driven, auto-generated help, Rich progress bars |
| Speech-to-Text | **WhisperX** (`large-v2`) | Batched inference, word-level timestamps, diarization support |
| Speaker Diarization | **pyannote.audio** (via WhisperX) | State-of-the-art diarization, integrated into WhisperX pipeline |
| Report Generation | **Google Gemini** (`gemini-2.0-flash`) | 1M token context, fast, cost-effective, good Korean support |
| Python SDK | **google-genai** (new SDK) | Current recommended SDK, `from google import genai` |
| Config | **pydantic-settings** | Type-safe .env loading |
| Audio Processing | **FFmpeg** (system dep) | Required by WhisperX for audio decoding |

### Key Technical Decisions

1. **`large-v2` over `large-v3` for Korean** - More reliable for CJK languages based on community reports
2. **`int8` compute type on CPU, `float16` on GPU** - Balance accuracy and memory usage
3. **`google-genai` (not `google-generativeai`)** - New SDK with `Client` pattern, actively maintained
4. **`gemini-2.0-flash` as default** - 1M token context handles multi-hour meetings; fast and cheap
5. **Explicit `language="ko"`** - Never rely on auto-detection for Korean

### Implementation Phases

#### Phase 1: Project Scaffolding

- [x] Initialize `pyproject.toml` with hatchling build backend
- [x] Create `src/voice_report/` package structure
- [x] Set up `config.py` with pydantic-settings loading from `.env`
- [x] Create `.env.example` with required variables
- [x] Create `.gitignore` (Python defaults + .env)
- [x] Set up basic Typer CLI skeleton in `cli.py`

**Files:** `pyproject.toml`, `src/voice_report/__init__.py`, `src/voice_report/cli.py`, `src/voice_report/config.py`, `.env.example`, `.gitignore`

#### Phase 2: Audio + Transcription

- [x] Implement `audio.py` - file validation, FFmpeg check, supported formats
- [x] Implement `models.py` - `Word`, `Segment`, `TranscriptResult` dataclasses with `to_text()` formatter
- [x] Implement `transcribe.py` - WhisperX load, transcribe, align pipeline
- [x] Diarization integrated into `transcribe.py` (combined for simplicity)
- [x] Wire up `--transcript-only` flow in CLI

**Files:** `src/voice_report/audio.py`, `src/voice_report/models.py`, `src/voice_report/transcribe.py`, `src/voice_report/diarize.py`

**Key code pattern - transcribe.py:**

```python
import whisperx

def transcribe_audio(audio_path, model_size="large-v2", language="ko", device="cpu"):
    compute_type = "float16" if device == "cuda" else "int8"
    batch_size = 16 if device == "cuda" else 4

    model = whisperx.load_model(model_size, device, compute_type=compute_type, language=language)
    audio = whisperx.load_audio(str(audio_path))
    result = model.transcribe(audio, batch_size=batch_size, language=language)
    del model  # free memory before alignment

    # Align for word-level timestamps
    model_a, metadata = whisperx.load_align_model(language_code=language, device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device)
    del model_a

    return result
```

**Key code pattern - diarize.py:**

```python
import whisperx

def diarize_transcript(audio, result, hf_token, device="cpu", min_speakers=None, max_speakers=None):
    diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
    diarize_segments = diarize_model(audio, min_speakers=min_speakers, max_speakers=max_speakers)
    result = whisperx.assign_word_speakers(diarize_segments, result)
    return result
```

#### Phase 3: Report Generation

- [x] Implement `report.py` - Gemini client, prompt building, report generation
- [x] Create `templates/default.txt` - default Korean meeting report prompt
- [x] Implement template loading (from `templates/` directory)
- [x] Support `--prompt` inline and `--template` name CLI options
- [x] Wire up full pipeline in CLI `convert` command

**Files:** `src/voice_report/report.py`, `templates/default.txt`

**Key code pattern - report.py:**

```python
from google import genai
from google.genai import types

def generate_report(transcript, api_key, system_prompt=None, model="gemini-2.0-flash"):
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=transcript,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt or DEFAULT_SYSTEM_PROMPT,
            temperature=0.3,
        ),
    )
    return response.text
```

**Default prompt template (`templates/default.txt`):**

```
당신은 전문 회의록 작성자입니다. 아래의 회의 녹취록을 분석하여 체계적인 회의 보고서를 마크다운 형식으로 작성해주세요.

## 작성 규칙
1. 한국어로 작성하세요
2. 핵심 내용을 중심으로 간결하게 정리하세요
3. 각 발언자의 주요 의견을 구분하여 정리하세요
4. 결정사항과 후속조치(Action Items)를 명확히 구분하세요

## 보고서 형식

### 회의 개요
- 참석자:
- 주요 안건:

### 논의 내용
(안건별로 구분하여 정리)

### 결정 사항
(번호를 매겨 명확하게 기술)

### 후속 조치 (Action Items)
(담당자, 기한이 언급된 경우 포함)

### 기타 메모
(추가 논의가 필요한 사항, 보류된 안건 등)
```

#### Phase 4: CLI Polish + UX

- [x] Add Rich progress spinners for each pipeline stage
- [x] Implement `--speakers` name mapping parser
- [x] Add `--verbose` flag for debug logging
- [x] Add audio duration display before processing
- [x] Handle error cases gracefully (missing API keys, FFmpeg not found, invalid audio)

**Files:** `src/voice_report/cli.py` (main updates)

## Acceptance Criteria

### Functional Requirements

- [ ] `voice-report convert <audio_file>` produces a markdown report from an .m4a file
- [ ] Speaker diarization correctly labels different speakers in the transcript
- [ ] `--prompt` allows inline custom instructions to Gemini
- [ ] `--template <name>` loads a prompt template from `templates/<name>.txt`
- [ ] `--transcript-only` outputs just the transcript without calling Gemini
- [ ] `--no-diarize` skips speaker identification
- [ ] `--speakers` maps SPEAKER_XX labels to actual names in the report
- [ ] `-o` / `--output` controls the output file path
- [ ] Default output is `<input_filename>.md` (or `.txt` for transcript-only)
- [ ] `--device cuda|cpu` switches compute device
- [ ] `--lang` sets the transcription language (default: `ko`)

### Error Handling

- [ ] Missing `GEMINI_API_KEY` -> clear error message with setup instructions
- [ ] Missing `HF_TOKEN` when diarization requested -> warn and offer `--no-diarize`
- [ ] FFmpeg not installed -> clear error with install instructions (brew/apt)
- [ ] Unsupported audio format -> list supported formats
- [ ] Audio file not found -> standard file-not-found error
- [ ] Gemini API failure -> display error, save transcript as fallback

## Dependencies & Prerequisites

### System Dependencies

| Dependency | Purpose | Install |
|------------|---------|---------|
| FFmpeg | Audio decoding for WhisperX | `brew install ffmpeg` (macOS) |
| Python 3.10+ | Runtime | System or pyenv |

### Python Dependencies

```toml
[project]
dependencies = [
    "whisperx>=3.1.0",
    "google-genai>=1.0.0",
    "typer[all]>=0.12.0",
    "pydantic-settings>=2.0",
    "python-dotenv>=1.0.0",
    "rich>=13.0",
    "torch>=2.0.0",
    "torchaudio>=2.0.0",
]
```

### API Keys Required

| Key | Source | Purpose |
|-----|--------|---------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) | Gemini report generation |
| `HF_TOKEN` | [HuggingFace](https://huggingface.co/settings/tokens) | Speaker diarization models |

**HuggingFace model agreements required** (must accept before first use):
- https://huggingface.co/pyannote/segmentation-3.0
- https://huggingface.co/pyannote/speaker-diarization-3.1

## Risk Analysis & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Korean alignment model unavailable | No word-level timestamps | Gracefully fall back to segment-level timestamps |
| WhisperX hallucination on silence | Garbage text in transcript | WhisperX VAD handles this; document as known limitation |
| Large audio files on CPU | Very slow processing | Display estimated time; recommend `--device cuda` in docs |
| Gemini safety filter blocks response | No report generated | Save transcript as fallback; log the block reason |
| HuggingFace 403 on diarization | Diarization fails | Clear error message linking to model agreement pages |
| `google-genai` SDK API changes | Import/method errors | Pin version in pyproject.toml |

## Edge Cases to Handle

- **Empty audio / silence only** - WhisperX returns empty segments -> report "No speech detected"
- **Single speaker** - Diarization labels everything SPEAKER_00 -> still works, just one speaker in report
- **Very long recordings (3+ hours)** - WhisperX batched inference handles this; Gemini 1M context fits easily
- **Mixed language audio** - Set `--lang` to primary language; Whisper handles code-switching reasonably
- **Both `--prompt` and `--template` provided** - Error: mutually exclusive options
- **Template not found** - Error: list available templates from `templates/` directory

## Development Setup

```bash
# 1. Create conda environment (recommended for PyTorch)
conda create -n voice-report python=3.10
conda activate voice-report

# 2. Install PyTorch (CPU or CUDA)
# CPU:
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
# CUDA 11.8:
# pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# 3. Install project in editable mode
pip install -e ".[dev]"

# 4. Copy and configure env vars
cp .env.example .env
# Edit .env with your GEMINI_API_KEY and HF_TOKEN

# 5. Verify FFmpeg
ffmpeg -version

# 6. Test with a short audio clip
voice-report convert test_audio.m4a --device cpu --lang ko
```

## References & Research

### Libraries

- WhisperX: https://github.com/m-bain/whisperX
- google-genai SDK: https://pypi.org/project/google-genai/
- Typer: https://typer.tiangolo.com/
- pyannote.audio: https://github.com/pyannote/pyannote-audio

### Models

- Whisper `large-v2`: Best for Korean (CJK) transcription
- Gemini `gemini-2.0-flash`: 1M token context, fast summarization
- pyannote `speaker-diarization-3.1`: Speaker identification backbone

### Gotchas Documented

1. **Two Google SDKs exist**: Use `google-genai` (new), NOT `google-generativeai` (old). They have incompatible import patterns.
2. **HuggingFace model agreements**: Must accept on the web UI before the token works. 403 errors mean you haven't accepted.
3. **Memory management**: Delete WhisperX models between stages (`del model`) to avoid OOM on GPU.
4. **Korean alignment**: May not have a wav2vec2 model available. Skip alignment gracefully -- segment-level timestamps are sufficient for reports.
5. **`int8` on CPU, `float16` on GPU**: Using `float16` on CPU will crash.

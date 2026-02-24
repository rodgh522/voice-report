# Voice Report (음성 보고서)

회의의 음성 녹음 파일(`.m4a`, `.wav`, `.mp3`)을 구조화된 마크다운 형식의 보고서로 변환해주는 CLI 도구입니다. 이 파이프라인은 화자 분할(Speaker Diarization) 기술이 포함된 WhisperX를 사용하여 로컬에서 음성을 텍스트로 변환(STT)하며, Google Gemini를 활용하여 회의 보고서를 자동으로 생성합니다.

## 🐳 Docker 기반 실행 (권장 - 모든 OS 지원)

Windows, macOS, Linux 등 운영체제와 상관없이 가장 빠르고 쉽게 실행할 수 있는 방법입니다. 별도 의존성 설치 없이 동작합니다.

### 1. 요구 사항

- [Docker Desktop](https://www.docker.com/products/docker-desktop) 설치
- API 키 설정 (아래 'API 키 설정' 참고)

### 2. 실행 스크립트 사용법

내장된 실행 래퍼(wrapper) 스크립트를 통해 로컬 CLI처럼 쉽게 사용할 수 있습니다.

- **macOS / Linux**:
  ```bash
  chmod +x voice-report.sh
  ./voice-report.sh convert <오디오_파일>
  ```
- **Windows** (명령 프롬프트 또는 PowerShell):
  ```cmd
  .\voice-report.bat convert <오디오_파일>
  ```

> 💡 **참고**: 스크립트는 내부적으로 `docker compose run --rm voice-report ...` 명령어를 호출하며 현재 폴더를 컨테이너 내부(`/app`)로 마운트합니다. 변환할 오디오 파일은 프로젝트 폴더 내부 또는 하위에 위치해야 결과를 정상적으로 받아볼 수 있습니다.

---

## 🛠 로컬 개발 환경 설정 (선택 사항)

이 프로젝트는 `pyenv` 및 `venv`를 통해 Python 3.12를 사용하도록 설정되어 있습니다. (개발 환경 구성 시에만 필요)

### 1. 요구 사항

- 시스템 의존성 패키지: `brew install pyenv ffmpeg` (macOS)
- Python 3.12 설치: `pyenv install 3.12`

### 2. 가상 환경 구성

프로젝트 루트 디렉토리에서 다음 명령어를 실행하여 가상 환경을 설정하세요:

```bash
# 이 프로젝트에 사용할 Python 3.12 버전을 고정합니다.
pyenv local 3.12

# 가상 환경(.venv)을 생성합니다.
python -m venv .venv

# 가상 환경을 활성화합니다.
source .venv/bin/activate

# 프로젝트 및 개발용 의존성 패키지를 설치합니다.
pip install -e ".[dev]"
```

### 3. API 키 설정 (공통)

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고, 본인의 API 키를 입력하세요:

```bash
cp .env.example .env
```
- `GEMINI_API_KEY`: 보고서 생성에 필수적으로 사용됩니다. ([Google AI Studio](https://aistudio.google.com/apikey)에서 발급)
- `HF_TOKEN`: 화자 분리(Speaker Diarization)를 위해 필수적으로 사용됩니다. ([HuggingFace](https://huggingface.co/settings/tokens)에서 발급)
  *참고: 토큰을 사용하기 전에 HuggingFace에서 `pyannote/segmentation-3.0` 및 `pyannote/speaker-diarization-3.1` 모델의 이용 약관에 동의해야 합니다.*

## 사용 방법

### 오디오 파일 위치 (.m4a 등의 파일)

오디오 기록 파일(예: `recording.m4a`)은 프로젝트 루트 디렉토리나 원하는 어떠한 폴더에 두어도 됩니다. 명령어를 실행할 때, 해당 오디오 파일의 경로만 지정해주면 됩니다.
기본적으로 변환된 출력 파일(스크립트 텍스트 파일 및 마크다운 보고서)은 현재 작업 중인 디렉토리 하위의 `result/<오디오_파일명>/` 경로에 생성 및 저장됩니다.

### 기본 명령어

오디오 파일을 회의 보고서로 변환하는 핵심 명령어는 `convert` 입니다. 로컬 환경에서 설치한 경우 `voice-report`를 호출하고, Docker 환경의 경우 래퍼 스크립트를 사용합니다:

```bash
# Docker 래퍼 스크립트 사용 시 (Mac/Linux)
./voice-report.sh convert recording.m4a

# Windows 래퍼 스크립트 사용 시
.\voice-report.bat convert recording.m4a

# 로컬 개발 환경 사용 시
voice-report convert recording.m4a
```

### CLI 옵션 상세

| 인수 / 옵션 | 설명 | 사용 예시 |
|---|---|---|
| `input_file` | **(필수)** 입력할 오디오 파일 또는 `.txt` 스크립트 파일의 경로. | `voice-report convert recording.m4a` |
| `--output`, `-o` | 출력될 파일 경로를 사용자 정의 형식으로 지정합니다. | `-o my_report.md` |
| `--model`, `-m` | Whisper 모델 크기를 지정합니다. (기본값: `large-v2`) | `-m small` |
| `--lang`, `-l` | 언어 코드를 지정합니다. (기본값: `ko`) | `-l en` |
| `--prompt`, `-p` | 보고서 생성을 위한 사용자 정의 프롬프트(지시문)를 직접 입력합니다. | `-p "간단하게 요약해줘"` |
| `--template`, `-t` | `templates/` 디렉토리에 저장된 프롬프트 템플릿 이름을 사용합니다. | `-t standup` |
| `--speakers`, `-s` | 화자 ID를 실제 이름으로 매핑(연결)합니다. | `-s "SPEAKER_00:Alice,SPEAKER_01:Bob"` |
| `--gemini-model` | 보고서 생성에 사용할 Gemini 모델. (기본값: `gemini-2.5-flash`) | `--gemini-model gemini-2.0-pro` |
| `--device`, `-d` | 연산 자원 장치를 설정합니다(`cpu` 또는 `cuda`). (기본값: `cpu`) | `-d cuda` |
| `--no-diarize` | 화자 식별 및 분할(Speaker Diarization)을 생략합니다. | `--no-diarize` |
| `--transcript-only`| 보고서를 생성하지 않고 음성을 텍스트로만 변환(스크립트)하여 출력합니다. | `--transcript-only` |
| `--verbose`, `-v`| 상세한 디버그 로그 출력을 활성화합니다. | `-v` |

### 사용 예시

**전체 파이프라인 처리 (기본 설정):**
```bash
# 예시: Unix Docker 스크립트 기준 (Windows인 경우 .\voice-report.bat 사용)
./voice-report.sh convert meeting.m4a
```

**음성 기록(Transcript)만 생성:**
```bash
./voice-report.sh convert meeting.m4a --transcript-only
```

**사용자 지정 프롬프트 또는 템플릿 사용:**
```bash
./voice-report.sh convert meeting.m4a --prompt "Action item 위주로 포커스해서 정리해줘."
./voice-report.sh convert meeting.m4a --template default
```

**매핑된 화자 이름 사용:**
```bash
./voice-report.sh convert meeting.m4a --speakers "SPEAKER_00:요한,SPEAKER_01:사라"
```

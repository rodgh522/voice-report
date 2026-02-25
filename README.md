# Voice Report (음성 보고서)

회의의 음성 녹음 파일(`.m4a`, `.wav`, `.mp3`)을 구조화된 마크다운 형식의 보고서로 변환해주는 CLI 도구입니다. 이 파이프라인은 화자 분할(Speaker Diarization) 기술이 포함된 WhisperX를 사용하여 로컬에서 음성을 텍스트로 변환(STT)하며, Google Gemini를 활용하여 회의 보고서를 자동으로 생성합니다.

## 🚀 시작하기 (Web UI 버전 - 권장)

가장 쉽고 직관적인 브라우저 기반의 웹 화면에서 모든 작업을 수행할 수 있습니다. 

### 1. 요구 사항

- [Docker Desktop](https://www.docker.com/products/docker-desktop) 설치
- 변환할 오디오 파일 (`.m4a`, `.wav`, `.mp3` 등)
- (선택) API 키. 별도로 설정하지 않아도 웹 화면 내에서 직접 입력할 수 있습니다.

### 2. 웹 서버 시작하기

프로젝트 폴더에서 운영체제에 맞는 런처 스크립트를 더블클릭 하거나 터미널에서 실행하세요:

- **Windows** (가장 쉬운 방법: 탐색기에서 더블클릭):
  ```cmd
  .\start-web.bat
  ```
- **macOS** (가장 쉬운 방법: Finder에서 더블클릭):
  - `start-web.command` 파일을 더블클릭하세요.
  *(권한 오류 발생 시 우클릭 -> 다음으로 열기 -> 터미널(Terminal) 선택)*
- **Linux** (터미널 사용):
  ```bash
  chmod +x start-web.sh
  ./start-web.sh
  ```

### 3. 웹 접속
스크립트가 실행되면 브라우저를 열고 `http://localhost:8501` 에 접속하여 마우스 드래그 앤 드롭으로 사용하세요!

---

## 💻 CLI (터미널) 기반 실행 (기존 방식)

CLI 및 스크립트 기반 동작을 원하신다면 이전과 동일하게 제공되는 래퍼(wrapper) 스크립트를 통해 사용할 수 있습니다.

### CLI 실행 방법

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

---

## 💻 요구 사항 및 컴퓨팅 사양 (Hardware Requirements)

Voice Report 파이프라인 중 **LLM 요약(Gemini 2.5 Flash)**은 구글 서버 파워를 빌려 사용하지만, **음성 인식(STT, Whisper `large-v2`)** 및 **화자 분리(pyannote)** 모델은 **사용자의 로컬 기기 리소스**를 직접 활용합니다. 각 모델의 크기가 커서 넉넉한 하드웨어 사양이 필요합니다.

### 🟩 최소 사양 (초기 설정 유지 시)
- **CPU**: Intel Core i5 (8세대 이상) / Apple M1 기본형
- **RAM**: **16GB 이상 (절대적 필수)**
  - Whisper `large-v2`와 pyannote 모델이 Docker 컨테이너 내에서 구동되려면 최고조에서 약 8~12GB의 메모리가 필요합니다. 시스템 메모리가 8GB인 경우 메모리 부족(OOM) 에러로 강제 종료될 확률이 매우 높습니다.
- **Docker 제한**: Docker Desktop 설정(Settings > Resources)에서 컨테이너 사용 최대 메모리를 **최소 12GB 이상**으로 설정 권장.

### 🟦 권장 사양 (빠른 변환)
- **CPU**: Intel Core i7 / AMD Ryzen 7 / Apple M2 Pro 이상
- **RAM**: **32GB 이상**
- **GPU (선택적 가속)**: 
  - Windows/Linux 환경인 경우 **VRAM 12GB 이상의 NVIDIA 그래픽 카드** (예: RTX 3060 12GB, RTX 4070 이상)를 강력히 권장합니다.
  - VRAM이 8GB 이하인 GPU를 사용할 경우 런타임 중 종종 모델 탑재에 실패할 수 있습니다.

### 💡 리소스 점유율을 대폭 낮추고 속도를 올리는 방법
PC 사양이 낮거나 단순한 용도라면 **웹 인터페이스(Web GUI) 좌측 옵션**을 통해 다음 설정을 변경하세요. 품질 하락 없이 리소스를 획기적으로 아낄 수 있습니다.

1. **Whisper 모델 사이즈 낮추기 (가장 효과적)**
   - `large-v2` (기본값) ➔ **`small`** 또는 **`base`**로 변경해 보세요. 메모리 사용량을 절반 이하로 줄이고 변환 시간을 최대 5배 이상 앞당깁니다.
2. **화자 분리(Diarization) 끄기**
   - 1인 발성 녹음이나 인터뷰 등 화자 식별(`SPEAKER_01` 등)이 크게 중요하지 않다면 **"Enable Speaker Diarization" 체크를 해제**하세요. 메모리 소모가 극적으로 줄어듭니다.

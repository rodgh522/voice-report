"""Streamlit web interface for voice-report."""

import os
import tempfile
from pathlib import Path

import streamlit as st
from pydantic_settings import BaseSettings

from voice_report.audio import get_audio_duration, validate_audio_file
from voice_report.config import Settings
from voice_report.report import TEMPLATES_DIR, generate_report, load_template
from voice_report.transcribe import transcribe_audio

# Set page configuration
st.set_page_config(
    page_title="Voice Report Web",
    page_icon="🎙️",
    layout="wide",
)

st.title("🎙️ Voice Report")
st.markdown("음성 녹음 파일을 구조화된 마크다운 회의 보고서로 변환합니다.")

# Load settings from .env if present
try:
    settings = Settings()
    default_gemini_key = settings.gemini_api_key
    default_hf_token = settings.hf_token
except Exception:
    default_gemini_key = ""
    default_hf_token = ""

# Sidebar for configuration
with st.sidebar:
    st.header("🔑 API Settings")
    
    gemini_key = st.text_input(
        "Gemini API Key", 
        value=default_gemini_key, 
        type="password",
        help="Google AI Studio에서 발급받은 API 키"
    )
    
    hf_token = st.text_input(
        "HuggingFace Token (Optional)", 
        value=default_hf_token, 
        type="password",
        help="화자 분리(Speaker Diarization)를 위한 토큰"
    )
    
    st.divider()
    st.header("⚙️ Configuration")
    
    model_size = st.selectbox(
        "Whisper Model Size",
        options=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
        index=4  # default to large-v2
    )
    
    language = st.text_input("Language Code", value="ko")
    
    device = st.selectbox(
        "Device",
        options=["cpu", "cuda", "mps"],
        index=0
    )
    
    use_diarize = st.checkbox("Enable Speaker Diarization", value=bool(hf_token))
    if use_diarize and not hf_token:
        st.warning("화자 분리를 사용하려면 HuggingFace 토큰이 필요합니다.")
        
    st.divider()
    st.header("📝 Report Options")
    
    gemini_model = st.selectbox(
        "Gemini Model",
        options=["gemini-2.5-flash", "gemini-2.0-pro"],
        index=0
    )
    
    # Get available templates
    available_templates = ["default"]
    if TEMPLATES_DIR.exists():
        available_templates.extend([f.stem for f in TEMPLATES_DIR.glob("*.txt") if f.stem != "default"])
    # Remove duplicates
    available_templates = list(dict.fromkeys(available_templates))
    
    template_choice = st.selectbox("Prompt Template", options=["Custom..."] + available_templates, index=1)
    
    if template_choice == "Custom...":
        custom_prompt = st.text_area("Custom Prompt", value="")
    else:
        custom_prompt = None
        
    speakers_input = st.text_input(
        "Speaker Mapping (Optional)",
        placeholder="SPEAKER_00:Alice, SPEAKER_01:Bob",
        help="콤마(,)로 구분하여 '화자ID:이름' 형태로 입력하세요."
    )

def parse_speaker_map(raw: str) -> dict[str, str]:
    if not raw:
        return {}
    result = {}
    for pair in raw.split(","):
        key, _, value = pair.partition(":")
        if key.strip() and value.strip():
            result[key.strip()] = value.strip()
    return result

# State Management
if "transcript" not in st.session_state:
    st.session_state.transcript = None
if "report" not in st.session_state:
    st.session_state.report = None
if "current_file" not in st.session_state:
    st.session_state.current_file = None

# Main area
uploaded_file = st.file_uploader("Upload Audio or Text File", type=["m4a", "wav", "mp3", "flac", "ogg", "txt"])

if uploaded_file is not None:
    is_text_input = uploaded_file.name.lower().endswith(".txt")
    
    if not is_text_input:
        st.audio(uploaded_file)
    else:
        with st.expander("미리보기 (Uploaded Text)"):
            st.text(uploaded_file.getvalue().decode("utf-8"))
    
    # If the user uploads a new file, reset the state
    if st.session_state.current_file != uploaded_file.name:
        st.session_state.transcript = None
        st.session_state.report = None
        st.session_state.current_file = uploaded_file.name
    
    if st.button("🚀 변환 시작 (Generate Report)", type="primary"):
        if not gemini_key:
            st.error("Gemini API Key가 필요합니다. 좌측 메뉴에 입력해주세요.")
            st.stop()
            
        # Parse speaker mapping
        speaker_map = parse_speaker_map(speakers_input)
            
        if is_text_input:
            st.session_state.transcript = uploaded_file.getvalue().decode("utf-8")
        else:
            # Save uploaded file to temp directory
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_audio_path = Path(tmp_file.name)
                
            try:
                validate_audio_file(tmp_audio_path)
                
                # 1. Transcribe
                with st.spinner("음성을 텍스트로 변환하는 중입니다... (모델 크기와 오디오 길이에 따라 몇 분 정도 소요될 수 있습니다)"):
                    transcript_result = transcribe_audio(
                        audio_path=tmp_audio_path,
                        model_size=model_size,
                        language=language,
                        device=device,
                        diarize=use_diarize,
                        hf_token=hf_token,
                    )
                
                if not transcript_result.segments:
                    st.warning("오디오에서 음성을 감지하지 못했습니다.")
                    st.stop()
                    
                st.session_state.transcript = transcript_result.to_text(speaker_map=speaker_map)
                
                # Clean up temp file immediately after STT is done successfully
                if tmp_audio_path.exists():
                    tmp_audio_path.unlink()
                    
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")
                if tmp_audio_path.exists():
                    tmp_audio_path.unlink()
                st.stop()
                
        # 2. Generate Report
        if st.session_state.transcript:
            with st.spinner("AI가 보고서를 작성하고 있습니다..."):
                system_prompt = None
                if template_choice == "Custom...":
                    system_prompt = custom_prompt
                else:
                    try:
                        system_prompt = load_template(template_choice)
                    except FileNotFoundError:
                         system_prompt = None
                         
                try:
                    st.session_state.report = generate_report(
                        transcript=st.session_state.transcript,
                        api_key=gemini_key,
                        system_prompt=system_prompt,
                        model=gemini_model,
                    )
                except Exception as e:
                    st.error(f"보고서 생성 중 오류가 발생했습니다: {str(e)}")

    # Display results if available in session state
    if st.session_state.transcript and st.session_state.report:
        st.success("변환 및 보고서 생성 완료!")
        
        with st.expander("인식된 텍스트 확인 (Transcript)"):
            st.text(st.session_state.transcript)
            st.download_button(
                label="텍스트 파일 다운로드 (.txt)",
                data=st.session_state.transcript,
                file_name=f"{Path(uploaded_file.name).stem}.txt",
                mime="text/plain"
            )
            
        st.markdown("---")
        st.markdown("### 📝 변환 결과")
        st.markdown(st.session_state.report)
        
        st.markdown("---")
        st.download_button(
            label="📥 마크다운 파일 다운로드 (.md)",
            data=st.session_state.report,
            file_name=f"{Path(uploaded_file.name).stem}.md",
            mime="text/markdown",
            type="primary"
        )

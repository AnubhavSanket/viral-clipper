# ViralClipper AI 

**ViralClipper AI** is a local, privacy-first desktop application that uses AI to automatically detect, transcribe, and edit viral-worthy clips from long-form videos.

![Dashboard Screenshot](screenshot.jpg)

##  Key Features
- **Local Processing**: Runs 100% offline using `Ollama` and `WhisperX`. No data is uploaded to the cloud.
- **AI Virality Score**: Uses `Gemma 2 (4B)` or `Llama 3` to analyze transcript sentiment and hook potential.
- **"Hormozi" Style Captions**: Automatically generates punchy, color-coded subtitles (Word-level timestamps).
- **Smart Context**: Expands clips automatically to include context (e.g., the setup to a joke).

##  Tech Stack
- **Python 3.10** (Core Logic)
- **PyQt6** (Modern GUI)
- **WhisperX** (Transcription & Forced Alignment)
- **Ollama** (Local LLM Inference)
- **FFmpeg & HandBrake** (Video Rendering Pipeline)

##  Installation
1. Install **Python 3.10** and [Ollama](https://ollama.com/).
2. Clone this repository.
3. Download `ffmpeg.exe`, `ffprobe.exe`, and `HandBrakeCLI.exe` and place them in the `bin/` folder.
4. Install dependencies:
   ```bash
   pip install -r requirements.txt


    Run Start_App.bat.

 How It Works

    Transcribe: Converts video audio to text using faster-whisper.

    Analyze: The transcript is fed into an LLM which scores segments (0-100) based on engagement criteria.

    Edit: FFmpeg cuts the video and burns in subtitles without re-encoding the whole stream (Smart Rendering).


# Viral Video Automation Pipeline

## Overview
This pipeline automates the creation of viral short-form clips (Shorts/Reels) from long-form videos. It uses a hybrid CPU/GPU workflow to ensure high speed and professional quality.

## Requirements
- **Python 3.10+** (Conda recommended)
- **NVIDIA GPU** (Minimum 4GB VRAM recommended)
- **CUDA Toolkit** (Compatible with your GPU)
- **Ollama** (Running locally for AI analysis)
- **HandBrakeCLI** (Placed in the project root)

## Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/AnubhavSanket/viral-clipper.git
    cd viral-clipper
    ```

2.  **Install Python Dependencies**
    ```bash
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    pip install whisperx ollama matplotlib
    ```
    *(Note: WhisperX may require `git+https://github.com/m-bain/whisperx.git` depending on your OS)*

3.  **Setup External Tools**
    - **Ollama:** Download from [ollama.com](https://ollama.com), install, and run `ollama pull gemma3:4b`.
    - **HandBrakeCLI:** Download the command-line version from [handbrake.fr](https://handbrake.fr/downloads.php) and place `HandBrakeCLI.exe` in this folder.

## How to Run

1.  **Prepare Videos:** Drop your raw video files (`.mp4`, `.mov`, `.mkv`) into the `input_videos/` folder.
2.  **Start AI Server:** Open a separate terminal and run:
    ```bash
    ollama serve
    ```
3.  **Run the Pipeline:** In your main terminal, run:
    ```bash
    python 4_batch_runner.py
    ```

## Pipeline Stages

| Step | Script | Description |
| :--- | :--- | :--- |
| **0** | `4_batch_runner.py` | **Conversion:** Uses `HandBrakeCLI` (GPU) to convert raw footage (ProRes/10-bit) into high-quality, constant frame-rate MP4. |
| **1** | `1_transcribe.py` | **Transcription:** Uses `WhisperX` (Int8) to generate word-level timestamps. Creates "Hormozi-style" subtitle chunks (2-3 words/line). |
| **2** | `2_analyze.py` | **AI Analysis:** Sends the transcript to `Gemma 3` (via Ollama) to identify the 3 most viral segments based on hooks and narrative flow. |
| **3** | `3_process_clips.py` | **Editing:** Uses `FFmpeg` to crop clips to 9:16 (vertical), burn in styled `.ass` subtitles, and render final MP4s. |
| **4** | `5_generate_report.py` | **Reporting:** Generates a `VIRALITY_REPORT.md` and an engagement timeline chart for review. |

## Output
Final clips are saved in:
`processed_videos/<Video_Name>/`

Each folder contains:
- `clip_1.mp4`, `clip_2.mp4`... (Ready to post)
- `VIRALITY_REPORT.md` (AI reasoning)
- `engagement_chart.png` (Visual retention graph)

## Common Issues & Fixes

-   **"HandBrakeCLI not found":** Ensure the `.exe` is in the same folder as the scripts, not in a subfolder.
-   **"Ollama connection failed":** Ensure `ollama serve` is running in a separate window.
-   **"Out of Memory":** If using a 4GB GPU, ensure `1_transcribe.py` is set to `batch_size=4` and `compute_type="int8"`.


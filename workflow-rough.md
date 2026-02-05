<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# okay, create a proper workflow for this app for me, from importing the video to burning the subtitles.

Step 1: Load Whisper, transcribe audio, save JSON. Unload Whisper from memory.
Step 2: Load Ollama/LLM, read JSON, find viral clips. Kill Ollama process.
Step 3: Run MediaPipe (CPU) to find crop coordinates.
Step 4: Run FFmpeg (NVENC) to crop and burn subtitles.
include each step and verify if any important step is missing.

Here is the comprehensive, optimized workflow for your "Viral Clip Generator" app. This workflow is specifically designed for your **Aspire 7 hardware (GTX 1650 4GB)** to prevent crashing while ensuring high quality.

### **Phase 1: Ingestion \& Transcription (GPU - VRAM Heavy)**

* **Goal:** Turn audio into structured text with precise timestamps.
* **Action:**

1. **Extract Audio:** Use FFmpeg to strip audio from the video file to a temporary WAV file (faster than loading the whole video into memory).
2. **Transcribe:** Load **WhisperX** (using `int8` compute type).
3. **Align:** Run the alignment model to ensure word-level timestamp accuracy (crucial for subtitles).
4. **Save:** Export data to `transcript.json`.
5. **Critical Cleanup:** `del model`, `gc.collect()`, `torch.cuda.empty_cache()` to fully clear VRAM.


### **Phase 2: Intelligence \& Selection (GPU/RAM - VRAM Heavy)**

* **Goal:** Identify the viral "needle" in the haystack.
* **Action:**

1. **Load LLM:** Initialize **Ollama** (Llama 3.2 3B).
2. **Prompting:** Feed the `transcript.json` in chunks (if video is long) to the LLM.
        * *Prompt:* "Identify 3 distinct segments (30-60s) with a strong hook, clear value, and conclusion. Return valid JSON with `start_time`, `end_time`, and `virality_score`."
3. **Sanity Check (Missing Step Added):** Verify the LLM's timestamps actually exist in the video duration. Fix any "hallucinated" timestamps.
4. **Save:** Export selected clips to `clips_manifest.json`.
5. **Critical Cleanup:** Kill the Ollama process or unload the model to free up RAM/VRAM.


### **Phase 3: Visual Tracking (CPU - Compute Optimized)**

* **Goal:** Convert horizontal (16:9) footage to vertical (9:16) without losing the speaker.
* **Action:**

1. **Iterate Clips:** For each clip in `clips_manifest.json`:
2. **Detect Faces:** Run **MediaPipe Face Detection** on the video frames corresponding to the clip's timestamps.
3. **Calculate Crop:**
        * Identify the "active speaker" (largest face or moving lips).
        * Compute the center `x` coordinate for a 9:16 crop window.
        * *Smoothing:* Apply a "Moving Average" filter to the `x` coordinates so the camera doesn't jitter wildly between frames.
4. **Save:** Store the crop coordinates map for each clip.


### **Phase 4: Composition \& Rendering (GPU - Encode Engine)**

* **Goal:** Burn everything together into the final file.
* **Action:**

1. **Format Subtitles (Missing Step Added):** Convert the specific segment's words from `transcript.json` into a styled `.ass` or `.srt` subtitle file (yellow text, bold font, etc.).
2. **Compose:** Use **FFmpeg** with the `h264_nvenc` encoder.
        * **Filter Complex:** Apply the `crop` filter using your smoothed coordinates + `subtitles` filter using your .ass file.
3. **Render:** Output the final `.mp4` file.
4. **Cleanup:** Delete temporary audio and subtitle files.


### **Summary of Missing/Refined Steps:**

1. **Audio Extraction:** Explicitly separate this to avoid loading video into RAM during transcription.
2. **Sanity Check:** LLMs sometimes output timestamps like "100:00" for a 10-minute video. You need a code block to validate this.
3. **Subtitle Formatting:** FFmpeg cannot burn raw JSON. You must convert the chosen segment's JSON to a subtitle format (`.srt` or `.ass`) before rendering.

This linear pipeline ensures you never run two heavy models at once, respecting your 4GB VRAM limit.

Synopsis: A portable desktop tool that uses local AI to automatically detect, crop, and caption viral moments from long-form videos. It replaces manual editing by using specialized AI models for transcription (Whisper) and content analysis (Ollama LLMs).

Workflow: 
Input Validation (pipeline_manager.py)
The app checks the video file integrity using ffprobe.
It determines resolution and duration.
Transcription (1_transcribe.py)
Engine: WhisperX (Local AI).
Action: Converts speech to text with precise word-level timestamps.
User Control: You can select the model size (base, small, medium) in the UI.
Viral Analysis (2_analyze.py)
Engine: Ollama (running local LLMs like Gemma 3, Llama 3, or Mistral).
Action: The LLM reads the transcript and identifies the "most viral" segments based on a prompt (hooks, humor, engagement).
User Control: You select the specific "Viral AI Model" in the UI.
Clip Generation (3_process_clips.py)
Engine: FFmpeg / HandBrake.
Action:
Cuts the video at the exact AI-identified timestamps.
Smart Crop: If the video is landscape (16:9), it attempts to crop it to vertical (9:16) for Shorts/TikTok.
Reporting (4_generate_report.py)
Generates a summary file (Markdown/Text) listing the created clips and their viral reasoning.
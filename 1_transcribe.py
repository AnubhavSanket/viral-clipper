import os
import sys
import torch
import warnings
import inspect

# ==============================================================================
# 🔧 CRITICAL HOTFIXES (Must run before other imports)
# ==============================================================================

# --- FIX 1: Prevent 'Weights only load failed' in PyTorch 2.6+ ---
_original_torch_load = torch.load
def safe_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = safe_torch_load

# --- FIX 2: Prevent 'RecursionError' in SpeechBrain ---
# The SpeechBrain lazy-loader crashes when inspecting stack frames.
# We temporarily disable frame inspection during imports.
_original_getframeinfo = inspect.getframeinfo

def safe_getframeinfo(frame, context=1):
    try:
        return _original_getframeinfo(frame, context)
    except Exception:
        # If inspection fails (recursion/etc), return a dummy frame info
        return inspect.Traceback(filename="unknown", lineno=0, function="unknown", code_context=None, index=0)

inspect.getframeinfo = safe_getframeinfo

# Force-load SpeechBrain to stabilize the environment
try:
    import speechbrain
    import speechbrain.lobes.models.ECAPA_TDNN
    import speechbrain.processing.features.spectral
except:
    pass
# ==============================================================================

import whisperx
import gc
import json

# --- CONFIGURED DEFAULTS ---
DEFAULT_MODEL_SIZE = "small"
DEFAULT_COMPUTE_TYPE = "int8"
DEFAULT_BATCH_SIZE = 4


# --- HORMOZI STYLE CONFIG ---
MAX_WORDS_PER_LINE = 2  # Keep it fast (2-3 words max)
MAX_CHARS_PER_LINE = 18 # Force break if words are long


def format_timestamp_ass(seconds):
    """Converts seconds to ASS timestamp format (H:MM:SS.cs)"""
    if seconds is None: return "0:00:00.00"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centis:02}"


def create_word_chunks(segments):
    """
    Splits long whisper segments into punchy 2-3 word chunks based on word-level timing.
    """
    chunks = []
    
    for segment in segments:
        if "words" not in segment:
            continue
            
        current_chunk = []
        current_char_count = 0
        
        for word_obj in segment["words"]:
            word = word_obj.get("word", "").strip()
            start = word_obj.get("start")
            end = word_obj.get("end")
            
            if start is None or end is None:
                continue

            if len(current_chunk) >= MAX_WORDS_PER_LINE or \
               (current_char_count + len(word)) > MAX_CHARS_PER_LINE:
                
                if current_chunk:
                    chunks.append({
                        "text": " ".join([w["word"] for w in current_chunk]),
                        "start": current_chunk[0]["start"],
                        "end": current_chunk[-1]["end"]
                    })
                    current_chunk = []
                    current_char_count = 0
            
            current_chunk.append({"word": word, "start": start, "end": end})
            current_char_count += len(word) + 1 
            
        if current_chunk:
            chunks.append({
                "text": " ".join([w["word"] for w in current_chunk]).upper(),
                "start": current_chunk[0]["start"],
                "end": current_chunk[-1]["end"]
            })
            
    return chunks 


def save_ass_hormozi(chunks, filename):
    print(f"--- Saving Hormozi-style subtitles to {filename} ---")
    
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,85,&H0000FFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,10,10,550,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(header)
        for chunk in chunks:
            start = format_timestamp_ass(chunk['start'])
            end = format_timestamp_ass(chunk['end'])
            text = chunk['text']
            f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")


def transcribe_video(video_path, output_json, output_ass, model_size=DEFAULT_MODEL_SIZE, compute_type="int8", batch_size=DEFAULT_BATCH_SIZE):
    # FORCE CPU to prevent CTranslate2 crashes on Windows
    device = "cpu"
    compute_type = "int8" 
    print(f"--- Loading WhisperX Model ({model_size} | {compute_type} | {device}) ---\n")

    try:
        model = whisperx.load_model(model_size, device, compute_type=compute_type)
        
        print(f"--- Transcribing Audio from {video_path} ---")
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        audio = whisperx.load_audio(video_path)
        result = model.transcribe(audio, batch_size=batch_size)
        
        print("--- Cleaning up Whisper Model ---")
        del model
        gc.collect()
        torch.cuda.empty_cache()
        
        print("--- Aligning Timestamps (Critical for Hormozi Style) ---")
        try:
            model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
            result = whisperx.align(result["segments"], model_a, metadata, audio, device=device, return_char_alignments=False)
            del model_a
            gc.collect()
            torch.cuda.empty_cache()
        except Exception as e:
            print(f"⚠️ Alignment failed: {e}. Subtitles might be less accurate.")

        print(f"--- Saving to {output_json} ---")
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(result["segments"], f, indent=2)

        # PROCESS WORD CHUNKS
        print("--- Chunking words for viral style... ---")
        word_chunks = create_word_chunks(result["segments"])
        
        # Generate the Styled ASS file
        save_ass_hormozi(word_chunks, output_ass)
        
        print(f"✅ Done! Created {len(word_chunks)} punchy subtitle chunks.")
        
    except Exception as e:
        print(f"❌ Transcribe failed: {e}")
        raise e


if __name__ == "__main__":
    VIDEO_PATH = "input_video.mp4"
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ Error: {VIDEO_PATH} not found.")
    else:
        transcribe_video(VIDEO_PATH, "transcript.json", "subtitles.ass")

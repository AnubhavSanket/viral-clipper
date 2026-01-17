import whisperx
import gc
import json
import torch
import os

# CONFIGURATION
VIDEO_PATH = "input_video.mp4"
OUTPUT_JSON = "transcript.json"
OUTPUT_ASS = "subtitles.ass"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 4
COMPUTE_TYPE = "int8"
MODEL_SIZE = "small"

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
    
    # Styles:
    # Fontname=Arial Black (Thick font)
    # PrimaryColour=&H0000FFFF (Yellow in BGR)
    # Outline=3 (Thick black border)
    # MarginV=550 (Positioned lower-middle, closer to center)
    
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

def transcribe_video():
    print(f"--- Loading WhisperX Model ({MODEL_SIZE} | {COMPUTE_TYPE}) ---\n")
    model = whisperx.load_model(MODEL_SIZE, DEVICE, compute_type=COMPUTE_TYPE)
    
    print("--- Transcribing Audio ---")
    audio = whisperx.load_audio(VIDEO_PATH)
    result = model.transcribe(audio, batch_size=BATCH_SIZE)
    
    print("--- Cleaning up Whisper Model ---")
    del model
    gc.collect()
    torch.cuda.empty_cache()
    
    print("--- Aligning Timestamps (Critical for Hormozi Style) ---")
    try:
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=DEVICE)
        # return_char_alignments=False is fine, we just need word timings
        result = whisperx.align(result["segments"], model_a, metadata, audio, device=DEVICE, return_char_alignments=False)
        del model_a
        gc.collect()
        torch.cuda.empty_cache()
    except Exception as e:
        print(f"⚠️ Alignment failed: {e}. Subtitles might be less accurate.")

    print(f"--- Saving to {OUTPUT_JSON} ---")
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result["segments"], f, indent=2)

    # PROCESS WORD CHUNKS
    print("--- Chunking words for viral style... ---")
    word_chunks = create_word_chunks(result["segments"])
    
    # Generate the Styled ASS file
    save_ass_hormozi(word_chunks, OUTPUT_ASS)
    
    print(f"✅ Done! Created {len(word_chunks)} punchy subtitle chunks.")

if __name__ == "__main__":
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ Error: {VIDEO_PATH} not found.")
    else:
        transcribe_video()

import os
import shutil
import subprocess
import time

# --- CONFIGURATION ---
INPUT_FOLDER = "input_videos"
PROCESSED_FOLDER = "processed_videos"
TEMP_INPUT_NAME = "input_video.mp4"
TEMP_OUTPUT_DIR = "final_clips"
HANDBRAKE_PATH = "HandBrakeCLI.exe" # Ensure this file is in your folder

os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def check_tools():
    if not os.path.exists(HANDBRAKE_PATH):
        print(f"❌ Error: {HANDBRAKE_PATH} not found!")
        print("   Please download it from: https://handbrake.fr/downloads.php (Command Line Version)")
        print("   and place it in this folder.")
        return False
    return True

def convert_video_handbrake(src, dest):
    """
    Robust Conversion using HandBrakeCLI + NVENC (GPU).
    HandBrake automatically fixes VFR (Variable Frame Rate) and Sync issues.
    """
    print(f"⚡ Converting {src} with HandBrake (GPU Mode)...")
    
    # HANDBRAKE COMMAND EXPLANATION:
    # --encoder nvenc_h264    : Use NVIDIA GPU
    # --quality 20            : High quality (similar to CRF 20)
    # --aencoder copy         : Pass audio through without quality loss (if compatible)
    # --fallback-aencoder aac : Convert audio if "copy" isn't supported
    # --cfr                   : Force Constant Frame Rate (Fixes sync issues!)
    
    cmd = [
        HANDBRAKE_PATH,
        "--input", src,
        "--output", dest,
        "--format", "av_mp4",
        "--encoder", "nvenc_h264",
        "--quality", "20",
        "--cfr",                # Critical: Forces constant frame rate to fix desync
        "--aencoder", "copy",
        "--audio-fallback", "aac",
        "--ab", "192"           # 192kbps audio could be alterted for different qualities
    ]

    # HandBrake prints progress to stderr, so we capture it to keep console clean
    # or let it print if you want to see the % bar.
    try:
        subprocess.run(cmd, check=True) # Let it print progress bar
        print("✅ Conversion successful.")
    except subprocess.CalledProcessError as e:
        print(f"❌ HandBrake failed: {e}")
        raise e

def process_video(filename):
    print(f"\n" + "="*50)
    print(f"🎬 PROCESSING: {filename}")
    print(f"="*50)
    
    start_time = time.time()
    src = os.path.join(INPUT_FOLDER, filename)
    
    if os.path.exists(TEMP_INPUT_NAME):
        os.remove(TEMP_INPUT_NAME)

    # STEP 0: Robust Conversion
    try:
        convert_video_handbrake(src, TEMP_INPUT_NAME)
    except Exception:
        print("⚠️ Skipping file due to conversion error.")
        return
    
    # Cleanup previous runs
    if os.path.exists(TEMP_OUTPUT_DIR):
        shutil.rmtree(TEMP_OUTPUT_DIR)
    os.makedirs(TEMP_OUTPUT_DIR)
    
    try:
        # Step 1: Transcribe
        print("\n[1/5] Transcribing Audio (WhisperX)...")
        subprocess.run(["python", "1_transcribe.py"], check=True)
        
        # Step 2: Analyze
        print("\n[2/5] Analyzing Viral Hooks (Gemma 3)...")
        subprocess.run(["python", "2_analyze.py"], check=True)
        
        # Step 3: Process Clips
        print("\n[3/5] Cropping, Centering & Subtitling...")
        subprocess.run(["python", "3_process_clips.py"], check=True)
        
        # Step 4: Report
        print("\n[4/5] Generating Virality Report...")
        subprocess.run(["python", "5_generate_report.py"], check=True)
        
        # Step 5: Finalize
        print("\n[5/5] Finalizing...")
        video_name_no_ext = os.path.splitext(filename)[0]
        final_dest = os.path.join(PROCESSED_FOLDER, video_name_no_ext)
        if os.path.exists(final_dest): shutil.rmtree(final_dest)
        shutil.move(TEMP_OUTPUT_DIR, final_dest)
        
        duration = int(time.time() - start_time)
        print(f"✅ DONE! Results saved to: {final_dest}")
        print(f"Time taken: {duration} seconds")
        
    except subprocess.CalledProcessError:
        print(f"❌ ERROR: Pipeline failed at {filename}.")
        
    finally:
        if os.path.exists(TEMP_INPUT_NAME): os.remove(TEMP_INPUT_NAME)

if __name__ == "__main__":
    if not check_tools():
        exit(1)

    valid_exts = (".mp4", ".mov", ".mkv", ".avi", ".webm")
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_exts)]
    
    if not files:
        print(f"⚠️  No videos found in '{INPUT_FOLDER}'.")
    else:
        print(f"Found {len(files)} videos. Starting Batch Pipeline...")
        for i, f in enumerate(files):
            process_video(f)

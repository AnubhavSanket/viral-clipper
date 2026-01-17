import json
import os
import subprocess
import sys

# --- CONFIGURATION ---
INPUT_VIDEO = "input_video.mp4"
CLIPS_JSON = "clips.json"
OUTPUT_DIR = "final_clips"
SUBTITLES_FILE = "subtitles.ass"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_clip(start_time, end_time, index):
    output_filename = os.path.join(OUTPUT_DIR, f"clip_{index+1}.mp4")
    print(f"\n--- Processing Clip {index+1} (Sync-Safe Mode): {start_time}s to {end_time}s ---")

    # SYNC FIX EXPLANATION:
    # 1. We do NOT use -ss before -i. This loads the video from 0:00.
    # 2. We apply subtitles immediately. Since video is at 0:00, subs align perfectly.
    # 3. We use the 'trim' filter to cut the video AFTER subs are burned.
    # 4. We use 'setpts=PTS-STARTPTS' to reset the clip timestamp to 0 so it plays correctly.
    
    # Filter Chain:
    # [0:v] -> Burn Subs -> Crop -> Trim -> Reset PTS -> [v_out]
    # [0:a] -> Trim -> Reset PTS -> [a_out]
    
    # Note: 'ass' filter requires escaping the filename properly in complex filters, 
    # but usually simple path works if no spaces.
    
    filter_complex = (
        f"[0:v]ass={SUBTITLES_FILE},"
        f"crop=w=ih*(9/16):h=ih:x=(iw-ow)/2:y=0,"
        f"trim=start={start_time}:end={end_time},"
        f"setpts=PTS-STARTPTS[v];"
        f"[0:a]atrim=start={start_time}:end={end_time},"
        f"asetpts=PTS-STARTPTS[a]"
    )

    cmd_gpu = [
        "ffmpeg", "-y",
        "-i", INPUT_VIDEO,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "h264_nvenc",
        "-pix_fmt", "yuv420p",
        "-preset", "p6",       # High Quality could be alterted for different qualities
        "-b:v", "15M",         # 15Mbps Bitrate could be alterted for different qualities
        "-c:a", "aac",
        "-b:a", "192k",
        output_filename
    ]
    
    # CPU Fallback
    cmd_cpu = [
        "ffmpeg", "-y",
        "-i", INPUT_VIDEO,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        output_filename
    ]

    try:
        subprocess.run(cmd_gpu, check=True, stderr=subprocess.PIPE)
        print(f"✅ Clip {index+1} created (HQ GPU).")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ GPU failed. Error:\n{e.stderr.decode()}")
        print("🔄 Falling back to CPU...")
        try:
            subprocess.run(cmd_cpu, check=True)
            print(f"✅ Clip {index+1} created (HQ CPU).")
        except subprocess.CalledProcessError as e_cpu:
            print(f"❌ Clip {index+1} failed.")

if __name__ == "__main__":
    if not os.path.exists(CLIPS_JSON): sys.exit(1)
    if not os.path.exists(SUBTITLES_FILE): sys.exit(1)

    with open(CLIPS_JSON, "r") as f:
        clips = json.load(f)

    for i, clip in enumerate(clips):
        create_clip(float(clip["start_time"]), float(clip["end_time"]), i)

    print("\n--- All Clips Processed! ---")

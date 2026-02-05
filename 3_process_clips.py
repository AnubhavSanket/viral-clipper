import json
import os
import subprocess
import sys

def create_clip(start_time, end_time, index, input_video, subtitles_file, output_dir):
    output_filename = os.path.join(output_dir, f"clip_{index+1}.mp4")
    print(f"\n--- Processing Clip {index+1} (Sync-Safe Mode): {start_time}s to {end_time}s ---")

    # SYNC FIX EXPLANATION:
    # 1. We do NOT use -ss before -i. This loads the video from 0:00.
    # 2. We apply subtitles immediately. Since video is at 0:00, subs align perfectly.
    # 3. We use the 'trim' filter to cut the video AFTER subs are burned.
    # 4. We use the 'setpts=PTS-STARTPTS' to reset the clip timestamp to 0 so it plays correctly.
    
    # Filter Chain:
    # [0:v] -> Burn Subs -> Crop -> Trim -> Reset PTS -> [v_out]
    # [0:a] -> Trim -> Reset PTS -> [a_out]
    
    # Note: 'ass' filter requires escaping the filename properly in complex filters, 
    # but usually simple path works if no spaces.
    # IMPORTANT: Start time in filter should be float string
    
    # Clean paths for ffmpeg (escaped backslashes can be tricky, use forward slashes)
    sub_path = subtitles_file.replace("\\", "/").replace(":", "\\:")
    
    filter_complex = (
        f"[0:v]ass='{sub_path}',"
        f"crop=w=ih*(9/16):h=ih:x=(iw-ow)/2:y=0,"
        f"trim=start={start_time}:end={end_time},"
        f"setpts=PTS-STARTPTS[v];"
        f"[0:a]atrim=start={start_time}:end={end_time},"
        f"asetpts=PTS-STARTPTS[a]"
    )

    cmd_gpu = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "h264_nvenc",
        "-pix_fmt", "yuv420p",
        "-preset", "p6",       # High Quality 
        "-b:v", "15M",         # 15Mbps Bitrate
        "-c:a", "aac",
        "-b:a", "192k",
        output_filename
    ]
    
    # CPU Fallback
    cmd_cpu = [
        "ffmpeg", "-y",
        "-i", input_video,
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
        # Check for NVIDIA GPU
        try:
            subprocess.run(["ffmpeg", "-f", "lavfi", "-i", "nullsrc", "-c:v", "h264_nvenc", "-t", "0.1", "-f", "null", "-"], 
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            has_gpu = True
        except:
            has_gpu = False

        if has_gpu:
            subprocess.run(cmd_gpu, check=True, stderr=subprocess.PIPE)
            print(f"✅ Clip {index+1} created (HQ GPU).")
        else:
            print("⚠️ GPU not detected or failed check. Using CPU.")
            subprocess.run(cmd_cpu, check=True)
            print(f"✅ Clip {index+1} created (HQ CPU).")
            
    except subprocess.CalledProcessError as e:
        print(f"⚠️ GPU failed. Error:\n{e.stderr.decode() if e.stderr else 'Unknown Error'}")
        print("🔄 Falling back to CPU...")
        try:
            subprocess.run(cmd_cpu, check=True)
            print(f"✅ Clip {index+1} created (HQ CPU).")
        except subprocess.CalledProcessError as e_cpu:
            print(f"❌ Clip {index+1} failed.")
            raise e_cpu

def process_clips(input_video, clips_json, subtitles_file, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(clips_json): 
        print(f"Error: {clips_json} not found.")
        return
    if not os.path.exists(subtitles_file): 
        print(f"Error: {subtitles_file} not found.")
        return

    with open(clips_json, "r") as f:
        clips = json.load(f)

    for i, clip in enumerate(clips):
        create_clip(float(clip["start_time"]), float(clip["end_time"]), i, input_video, subtitles_file, output_dir)

    print("\n--- All Clips Processed! ---")

if __name__ == "__main__":
    # Backwards compatibility
    INPUT_VIDEO = "input_video.mp4"
    CLIPS_JSON = "clips.json"
    OUTPUT_DIR = "final_clips"
    SUBTITLES_FILE = "subtitles.ass"
    
    if os.path.exists(CLIPS_JSON):
        process_clips(INPUT_VIDEO, CLIPS_JSON, SUBTITLES_FILE, OUTPUT_DIR)


import json
import os
import matplotlib.pyplot as plt

# CONFIGURATION
CLIPS_JSON = "clips.json"
TRANSCRIPT_JSON = "transcript.json"
OUTPUT_DIR = "final_clips"  # Or where your batch runner puts the final folder
REPORT_FILE = os.path.join(OUTPUT_DIR, "VIRALITY_REPORT.md")
CHART_FILE = os.path.join(OUTPUT_DIR, "engagement_chart.png")

def generate_report():
    if not os.path.exists(CLIPS_JSON) or not os.path.exists(TRANSCRIPT_JSON):
        print("Error: JSON files not found. Run analysis first.")
        return

    # Load Data
    with open(CLIPS_JSON, "r", encoding="utf-8") as f:
        clips = json.load(f)
        
    with open(TRANSCRIPT_JSON, "r", encoding="utf-8") as f:
        transcript = json.load(f)
        video_duration = transcript[-1]['end'] if transcript else 0

    # 1. Generate Markdown Text
    md_content = f"## AI Virality Report\n\n"
    md_content += f"**Total Video Duration:** {video_duration/60:.2f} minutes\n"
    md_content += f"**Clips Generated:** {len(clips)}\n\n"
    
    md_content += "## Viral Clips Summary\n"
    md_content += "| Clip # | Time Range | Duration | Score | Reasoning |\n"
    md_content += "| :--- | :--- | :--- | :--- | :--- |\n"
    
    for i, clip in enumerate(clips):
        start = f"{int(clip['start_time'] // 60)}:{int(clip['start_time'] % 60):02d}"
        end = f"{int(clip['end_time'] // 60)}:{int(clip['end_time'] % 60):02d}"
        score = clip.get('virality_score', 'N/A')
        reason = clip.get('reasoning', 'No reasoning provided.').replace('\n', ' ')
        
        md_content += f"| {i+1} | {start} - {end} | {clip['duration']}s | **{score}/100** | {reason} |\n"
        
    md_content += "\n## Visual Timeline\n"
    md_content += "![Engagement Chart](./engagement_chart.png)\n"
    
    # 2. Generate Chart (Matplotlib)
    plt.figure(figsize=(10, 4))
    
    # Draw gray background bar for full video
    plt.barh(y=1, width=video_duration, left=0, height=0.5, color='#e0e0e0', label='Full Video')
    
    # Draw colored bars for clips
    colors = ['#FF4B4B', '#FF8F4B', '#FFD44B'] # Red -> Orange -> Yellow
    
    for i, clip in enumerate(clips):
        c = colors[i % len(colors)]
        plt.barh(y=1, width=clip['duration'], left=clip['start_time'], height=0.5, color=c, edgecolor='black', label=f"Clip {i+1}")
        # Add label above bar
        plt.text(clip['start_time'], 1.3, f"Clip {i+1} ({clip['virality_score']})", fontsize=9, rotation=45)

    plt.yticks([])
    plt.xlabel("Time (seconds)")
    plt.title("Viral Segments Timeline")
    plt.xlim(0, video_duration + 10)
    plt.tight_layout()
    
    # Ensure output dir exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    plt.savefig(CHART_FILE)
    print(f"--- Chart saved to {CHART_FILE} ---")
    
    # 3. Save Markdown
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print(f"--- Report saved to {REPORT_FILE} ---")

if __name__ == "__main__":
    generate_report()

import json
import os
import matplotlib.pyplot as plt

def generate_report(clips_json, transcript_json, output_dir):
    report_file = os.path.join(output_dir, "VIRALITY_REPORT.md")
    chart_file = os.path.join(output_dir, "engagement_chart.png")

    if not os.path.exists(clips_json) or not os.path.exists(transcript_json):
        print("Error: JSON files not found. Run analysis first.")
        return

    # Load Data
    with open(clips_json, "r", encoding="utf-8") as f:
        clips = json.load(f)
        
    with open(transcript_json, "r", encoding="utf-8") as f:
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
    plt.switch_backend('Agg')
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
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    plt.savefig(chart_file)
    print(f"--- Chart saved to {chart_file} ---")
    
    # 3. Save Markdown
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print(f"--- Report saved to {report_file} ---")

if __name__ == "__main__":
    # Compatibility
    generate_report("clips.json", "transcript.json", "final_clips")

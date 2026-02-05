import json
import ollama
import math
import os

# --- CONFIGURED DEFAULTS ---
DEFAULT_MODEL = "gemma3:4b"

def analyze_transcript(input_json, output_clips, model_name=DEFAULT_MODEL):
    print(f"--- Loading {input_json} ---")
    if not os.path.exists(input_json):
        print(f"Error: {input_json} not found.")
        return

    with open(input_json, "r", encoding="utf-8") as f:
        segments = json.load(f)

    # 1. Prepare text chunks
    full_text = ""
    for seg in segments:
        start = round(seg['start'], 2)
        end = round(seg['end'], 2)
        text = seg['text'].strip()
        full_text += f"[{start}-{end}] {text}\n"

    print(f"--- Sending to Ollama ({model_name})... ---")
    
    # 2. Construct the Prompt
    prompt = f"""
    You are a viral content editor. Analyze the transcript below from a YouTube video.
    Identify the TOP most engaging segments suitable for YouTube Shorts and Instagram Reels.
    
    CRITICAL RULES:
    1. EACH CLIP MUST BE 30 TO 180 SECONDS LONG.
    2. Context is key: Include the full setup (intro), the main hook, and the conclusion. Do not rush.
    
    Transcript:
    {full_text}

    RETURN ONLY RAW JSON. Structure:
    [
      {{
        "start_time": 12.0,
        "end_time": 145.0,
        "virality_score": 95,
        "reasoning": "Complete story about X, starting from the setup."
      }}
    ]
    """

    try:
        response = ollama.chat(model=model_name, messages=[
            {'role': 'user', 'content': prompt},
        ])
        content = response['message']['content']
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        raise e

    print("\n--- Raw Response from LLM ---")
    print(content)

    # 3. Clean and Parse JSON
    cleaned_content = content.replace("```json", "").replace("```", "").strip()
    
    try:
        clips_data = json.loads(cleaned_content)
        
        valid_clips = []
        max_time = segments[-1]['end']
        
        print("\n--- Applying Smart Context Expansion ---")

        for clip in clips_data:
            original_start = clip['start_time']
            original_end = clip['end_time']
            
            # --- SMART CONTEXT EXPANSION LOGIC ---
            
            # 1. Find the segment indices corresponding to the LLM timestamps
            start_index = -1
            end_index = -1
            
            for i, seg in enumerate(segments):
                if start_index == -1 and seg['end'] >= original_start:
                    start_index = i
                if seg['start'] <= original_end:
                    end_index = i
            
            if start_index == -1: start_index = 0
            if end_index == -1: end_index = len(segments) - 1
            if end_index < start_index: end_index = start_index

            # 2. Look Back (Add Intro/Setup)
            current_start = segments[start_index]['start']
            steps_back = 0
            while start_index > 0 and steps_back < 2:
                prev_seg = segments[start_index - 1]
                gap = current_start - prev_seg['end']
                current_duration = segments[end_index]['end'] - current_start
                
                # Condition: Small gap (flow) OR Clip is currently too short (< 20s)
                if gap < 1.5 or current_duration < 20:
                    print(f"   [Context] Adding previous line: '{prev_seg['text'].strip()[:30]}...'")
                    start_index -= 1
                    current_start = prev_seg['start']
                    steps_back += 1
                else:
                    break
            
            # 3. Look Forward (Finish the Thought)
            # UPDATED: Allow expansion up to ~175 seconds (near the 180s limit)
            current_end = segments[end_index]['end']
            while end_index < len(segments) - 1:
                next_seg = segments[end_index + 1]
                current_duration = current_end - segments[start_index]['start']
                
                # Stop hard if we exceed 175 seconds (leave buffer for safety)
                if current_duration > 175: 
                    break
                    
                gap = next_seg['start'] - current_end
                
                # Condition: Add if gap is small OR we are still under 30s duration
                if gap < 1.0 or current_duration < 30:
                    print(f"   [Context] Adding next line: '{next_seg['text'].strip()[:30]}...'")
                    end_index += 1
                    current_end = next_seg['end']
                else:
                    break

            # 4. Finalize Timestamps
            final_start = segments[start_index]['start']
            final_end = segments[end_index]['end']
            
            # Clamp to video end
            if final_end > max_time: final_end = max_time
            
            # Hard limit check for 180s (Shorts/Reels max)
            if (final_end - final_start) > 179.0:
                 print(f"   [Limit] Clip duration {final_end - final_start:.2f}s exceeds 180s. Trimming.")
                 final_end = final_start + 179.0
            
            clip['start_time'] = round(final_start, 2)
            clip['end_time'] = round(final_end, 2)
            clip['duration'] = round(final_end - final_start, 2)
            
            print(f"   Final Clip: {original_start}-{original_end} -> {clip['start_time']}-{clip['end_time']} (Dur: {clip['duration']}s)")
            valid_clips.append(clip)

        with open(output_clips, "w", encoding="utf-8") as f:
            json.dump(valid_clips, f, indent=2)
            
        print(f"\n--- Saved {len(valid_clips)} expanded clips to {output_clips} ---")
        
    except json.JSONDecodeError:
        print("Error: LLM did not return valid JSON. Check the raw response above.")
        raise ValueError("Invalid JSON from LLM")
    except Exception as e:
        print(f"Error processing clips: {e}")
        raise e

if __name__ == "__main__":
    analyze_transcript("transcript.json", "clips.json")

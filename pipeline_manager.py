import os
import shutil
import subprocess
import time
import sys
import threading
import requests

# Import refactored modules
try:
    import builtins
    if getattr(sys, 'frozen', False):
        BASE_DIR = sys._MEIPASS
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    if BASE_DIR not in sys.path:
        sys.path.append(BASE_DIR)
except Exception:
    BASE_DIR = os.getcwd()

from importlib import import_module

try:
    transcribe_module = import_module("1_transcribe")
    analyze_module = import_module("2_analyze")
    process_module = import_module("3_process_clips")
    report_module = import_module("4_generate_report")
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import backend modules: {e}")

class PipelineManager:
    def __init__(self, log_callback=None, progress_callback=None):
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.should_stop = False
        self.ollama_process = None
        self.is_running = False 

    def stop(self):
        self.should_stop = True
        self.log("⚠️ Stop signal received. Pipeline will halt safely.")

    def log(self, message):
        print(message)
        if self.log_callback:
            self.log_callback(message)

    def check_tools(self):
        tools = ["HandBrakeCLI.exe", "ffmpeg.exe", "ffprobe.exe"]
        missing = []
        
        # Search paths: Root, Bin, Script Dir, Script/Bin
        search_paths = [
            os.getcwd(),
            os.path.join(os.getcwd(), "bin"),
            os.path.dirname(sys.argv[0]),
            os.path.join(os.path.dirname(sys.argv[0]), "bin"),
            BASE_DIR,
            os.path.join(BASE_DIR, "bin")
        ]

        found_hb = None

        for tool in tools:
            found = False
            for path in search_paths:
                full_path = os.path.join(path, tool)
                if os.path.exists(full_path):
                    if tool == "HandBrakeCLI.exe":
                        found_hb = full_path
                    
                    # Add to PATH so subprocess finds them
                    if path not in os.environ["PATH"]:
                        os.environ["PATH"] += os.pathsep + path
                    
                    found = True
                    break
            
            if not found:
                missing.append(tool)

        if missing:
            self.log(f"❌ Missing tools: {', '.join(missing)}")
            self.log("Please ensure they are in the 'bin' folder.")
            return False, None
        
        self.log(f"✅ Found HandBrake at: {found_hb}")
        return True, found_hb

    def ensure_ollama_running(self):
        try:
            requests.get("http://127.0.0.1:11434", timeout=2)
            self.log("✅ Ollama is already running.")
            return True
        except requests.exceptions.ConnectionError:
            self.log("⚠️ Ollama not detected. Starting background service...")
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                self.ollama_process = subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags
                )
                for _ in range(10):
                    try:
                        time.sleep(1)
                        requests.get("http://127.0.0.1:11434", timeout=1)
                        self.log("✅ Ollama started successfully.")
                        return True
                    except:
                        pass
                self.log("❌ Failed to start Ollama automatically.")
                return False
            except FileNotFoundError:
                self.log("❌ 'ollama' command not found. Please install Ollama.")
                return False

    def convert_video_handbrake(self, src, dest, hb_path):
        self.log(f"Converting {src} with HandBrake (GPU Mode)...")
        
        # ⚠️ IMPORTANT: If you do NOT have an NVIDIA GPU, change "nvenc_h264" to "x264" below.
        encoder_preset = "nvenc_h264" 
        
        cmd = [
            hb_path, "--input", src, "--output", dest, "--format", "av_mp4",
            "--encoder", encoder_preset, "--quality", "20", "--cfr",
            "--aencoder", "copy", "--audio-fallback", "aac", "--ab", "192"
        ]

        try:
            # We must use bufsize=1 and read stdout to avoid deadlocks!
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read output continuously to keep the pipe flowing
            for line in process.stdout:
                if self.should_stop:
                    process.terminate()
                    raise Exception("Process stopped by user.")
                
                # We can uncomment this to debug, but it might spam the logs
                # if "Encoding" in line: print(line.strip(), end='\r')

            process.wait()
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd)
                
            self.log("✅ Conversion successful.")
            
        except subprocess.CalledProcessError as e:
            self.log(f"❌ HandBrake failed (Code {e.returncode}).")
            self.log("💡 Tip: If you don't have an NVIDIA GPU, edit 'pipeline_manager.py' and change 'nvenc_h264' to 'x264'.")
            raise e

    def run_pipeline(self, video_path, model_name, prompt, output_dir=None, whisper_model="base"):
        if self.is_running: return
        self.is_running = True
        self.should_stop = False
        start_time = time.time()
        
        try:
            valid, hb_path = self.check_tools()
            if not valid:
                raise FileNotFoundError("Tools missing. check logs.")

            if not self.ensure_ollama_running():
                raise Exception("Ollama service could not be started.")

            if not output_dir:
                output_dir = os.path.join(os.path.dirname(video_path), "processed_output")
                
            temp_dir = os.path.join(output_dir, "temp_work")
            os.makedirs(temp_dir, exist_ok=True)
            
            temp_input = os.path.join(temp_dir, "temp_input.mp4")
            transcript_json = os.path.join(temp_dir, "transcript.json")
            subtitles_ass = os.path.join(temp_dir, "subtitles.ass")
            clips_json = os.path.join(temp_dir, "clips.json")
            final_clips_dir = os.path.join(output_dir, os.path.splitext(os.path.basename(video_path))[0])
            
            # Step 0
            if self.should_stop: return
            self.log("Step 0: Pre-processing Video...")
            self.convert_video_handbrake(video_path, temp_input, hb_path)
            if self.progress_callback: self.progress_callback(10)

            # Step 1
            if self.should_stop: return
            self.log(f"Step 1: Transcribing ({whisper_model})...")
            transcribe_module.transcribe_video(temp_input, transcript_json, subtitles_ass, model_size=whisper_model)
            if self.progress_callback: self.progress_callback(30)

            # Step 2
            if self.should_stop: return
            self.log(f"Step 2: Analyzing for Viral Clips ({model_name})...")
            analyze_module.analyze_transcript(transcript_json, clips_json, model_name=model_name)
            if self.progress_callback: self.progress_callback(50)

            # Step 3
            if self.should_stop: return
            self.log("Step 3: Rendering Clips (FFmpeg)...")
            process_module.process_clips(temp_input, clips_json, subtitles_ass, final_clips_dir)
            if self.progress_callback: self.progress_callback(80)

            # Step 4
            if self.should_stop: return
            self.log("Step 4: Generating Report...")
            report_module.generate_report(clips_json, transcript_json, final_clips_dir)
            if self.progress_callback: self.progress_callback(95)
            
            duration = int(time.time() - start_time)
            self.log(f"✅ Pipeline Completed in {duration}s. Output: {final_clips_dir}")
            if self.progress_callback: self.progress_callback(100)
            
        except Exception as e:
            self.log(f"❌ Pipeline Failed: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            self.is_running = False

    def start_thread(self, video_path, model_name, prompt, output_dir=None, whisper_model="base"):
        if not self.is_running:
            t = threading.Thread(
                target=self.run_pipeline,
                args=(video_path, model_name, prompt, output_dir, whisper_model),
                daemon=True
            )
            t.start()
        else:
            self.log("⚠️ Pipeline is already running.")

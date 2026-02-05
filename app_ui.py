import sys
import subprocess
import os
import importlib.util
import json

# --- 1. CRITICAL PATH FIX FOR PORTABLE PYTHON ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# --- 2. DEPENDENCY AUTO-INSTALLER ---
def install_dependencies():
    """Checks for GUI libs and installs them to the embedded python."""
    required = ["PyQt6", "requests", "pillow"] 
    missing = []

    for lib in required:
        if importlib.util.find_spec(lib) is None:
            missing.append(lib)

    if missing:
        print(f"⚠️ First Run: Installing UI libraries ({', '.join(missing)})...")
        print("   This might take a minute...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "--upgrade", "pip", "--no-warn-script-location"
            ])
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "--prefer-binary", *missing, "--no-warn-script-location"
            ])
            print("✅ Dependencies installed. Launching UI...")
        except Exception as e:
            print(f"❌ Failed to install dependencies: {e}")
            input("Press Enter to exit...")
            sys.exit(1)

if __name__ == "__main__":
    install_dependencies()

# --- 3. IMPORTS ---
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFileDialog, 
                             QProgressBar, QTextEdit, QComboBox, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon

# Import backend logic safely
try:
    import pipeline_manager
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import pipeline_manager.\nError: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

# --- 4. SIGNALS CLASS ---
class StreamSignals(QObject):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

# --- 5. MAIN UI CLASS ---
class ViralClipperUI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Viral Clipper AI - Pro Dashboard")
        self.resize(1000, 750)

        # 1. SETUP UI FIRST
        self.setup_ui()
        self.apply_dark_theme()

        # 2. Initialize Signals
        self.signals = StreamSignals()
        self.signals.log_signal.connect(self.append_log)
        self.signals.progress_signal.connect(self.update_progress)

        # 3. Initialize Pipeline
        self.pipeline = pipeline_manager.PipelineManager(
            log_callback=self.signals.log_signal.emit,
            progress_callback=self.signals.progress_signal.emit
        )

        # Initial Log
        self.append_log("✅ System Ready. HandBrakeCLI bundled successfully.")
        self.append_log(f"📂 Root Directory: {current_dir}")

        # 4. Fetch Ollama Models
        self.fetch_ollama_models()

    def fetch_ollama_models(self):
        """Fetches available models from Ollama and updates the combo box."""
        self.append_log("🔍 Scanning for local Ollama models...")
        try:
            # Run 'ollama list' command
            # Using creationflags to hide the console window on Windows
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                creationflags=creationflags
            )

            if result.returncode == 0:
                # Parse output. Output format is typically:
                # NAME            ID              SIZE      MODIFIED
                # gemma:2b        b50d6c999e59    1.7 GB    2 hours ago

                lines = result.stdout.strip().split('\n')
                models = []

                # Skip header row (NAME, ID, etc.)
                for line in lines[1:]:
                    parts = line.split()
                    if parts:
                        models.append(parts[0]) # The name is the first column

                if models:
                    self.llm_combo.clear()
                    self.llm_combo.addItems(models)
                    self.append_log(f"✅ Found {len(models)} local AI models.")
                else:
                    self.append_log("⚠️ No models found in Ollama. Using defaults.")
            else:
                self.append_log("⚠️ Could not contact Ollama. Is it running?")

        except FileNotFoundError:
            self.append_log("❌ Error: 'ollama' command not found. Please install Ollama.")
        except Exception as e:
            self.append_log(f"❌ Error fetching models: {e}")

    def setup_ui(self):
        # Main Widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # --- HEADER ---
        header_label = QLabel("🚀 Viral Clipper AI Pipeline")
        header_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("color: #E0E0E0; margin-bottom: 20px;")
        main_layout.addWidget(header_label)

        # --- INPUT ROW ---
        input_layout = QHBoxLayout()
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Select Video File...")
        self.input_field.setFixedHeight(45)
        self.input_field.setReadOnly(True)
        self.input_field.setStyleSheet("background-color: #2D2D2D; color: #CCC; border: 1px solid #444; border-radius: 5px; padding: 5px;")

        browse_input_btn = QPushButton("Browse Input")
        browse_input_btn.setFixedSize(130, 45)
        browse_input_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_input_btn.setStyleSheet("""
            QPushButton { background-color: #007ACC; color: white; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #0069B4; }
        """)
        browse_input_btn.clicked.connect(self.select_video)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(browse_input_btn)
        main_layout.addLayout(input_layout)

        # --- OUTPUT ROW ---
        output_layout = QHBoxLayout()
        self.output_field = QTextEdit()
        self.output_field.setPlaceholderText("Select Output Folder (Optional)...")
        self.output_field.setFixedHeight(45)
        self.output_field.setReadOnly(True)
        self.output_field.setStyleSheet("background-color: #2D2D2D; color: #CCC; border: 1px solid #444; border-radius: 5px; padding: 5px;")

        browse_output_btn = QPushButton("Browse Output")
        browse_output_btn.setFixedSize(130, 45)
        browse_output_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_output_btn.setStyleSheet("""
            QPushButton { background-color: #007ACC; color: white; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #0069B4; }
        """)
        browse_output_btn.clicked.connect(self.select_output)

        output_layout.addWidget(self.output_field)
        output_layout.addWidget(browse_output_btn)
        main_layout.addLayout(output_layout)

        # --- SETTINGS ROW (Whisper & LLM) ---
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(15)
        settings_layout.setContentsMargins(0, 10, 0, 10)

        # Whisper Label & Combo
        lbl_whisper = QLabel("Whisper Model:")
        lbl_whisper.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems(["base", "small", "medium", "large"])
        self.whisper_combo.setFixedWidth(100)
        self.whisper_combo.setStyleSheet("padding: 5px; background-color: #333; color: white; border: 1px solid #555;")

        # LLM Label & Combo
        lbl_llm = QLabel("Viral AI Model:")
        lbl_llm.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.llm_combo = QComboBox()
        # Default items in case fetch fails
        self.llm_combo.addItems(["gemma:2b", "mistral:7b", "llama3:8b"])
        self.llm_combo.setEditable(True)
        self.llm_combo.setFixedWidth(150)
        self.llm_combo.setStyleSheet("padding: 5px; background-color: #333; color: white; border: 1px solid #555;")

        settings_layout.addWidget(lbl_whisper)
        settings_layout.addWidget(self.whisper_combo)
        settings_layout.addSpacing(20)
        settings_layout.addWidget(lbl_llm)
        settings_layout.addWidget(self.llm_combo)
        settings_layout.addStretch()

        main_layout.addLayout(settings_layout)

        # --- ACTION BUTTONS ---
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("START PROCESSING")
        self.start_btn.setFixedHeight(55)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.start_btn.setStyleSheet("""
            QPushButton { background-color: #00C853; color: white; border-radius: 5px; }
            QPushButton:hover { background-color: #00B248; }
            QPushButton:disabled { background-color: #444; color: #888; }
        """)
        self.start_btn.clicked.connect(self.start_pipeline)

        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setFixedHeight(55)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.stop_btn.setStyleSheet("""
            QPushButton { background-color: #D50000; color: white; border-radius: 5px; }
            QPushButton:hover { background-color: #B71C1C; }
        """)
        self.stop_btn.clicked.connect(self.stop_pipeline)
        self.stop_btn.setEnabled(False)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        main_layout.addLayout(btn_layout)

        # --- PROGRESS BAR ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: none; background-color: #333; border-radius: 5px; }
            QProgressBar::chunk { background-color: #4CAF50; border-radius: 5px; }
        """)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # --- LOGS HEADER ---
        lbl_logs = QLabel("System Logs:")
        lbl_logs.setFont(QFont("Segoe UI", 10))
        lbl_logs.setStyleSheet("color: #AAA; margin-top: 10px;")
        main_layout.addWidget(lbl_logs)

        # --- LOG WINDOW ---
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #0A0A0A; 
                color: #00E676; 
                font-family: Consolas; 
                font-size: 10pt; 
                border: 1px solid #333;
                border-radius: 3px;
            }
        """)
        main_layout.addWidget(self.log_output)

    def apply_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        self.setPalette(palette)

    def select_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video Files (*.mp4 *.mkv *.mov)")
        if file_path:
            self.selected_file = file_path
            self.input_field.setText(file_path)
            self.append_log(f"📄 Input Selected: {os.path.basename(file_path)}")

    def select_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_field.setText(folder)
            self.append_log(f"📂 Output Folder Set: {folder}")

    def start_pipeline(self):
        if not hasattr(self, 'selected_file'):
            QMessageBox.warning(self, "No File", "Please select a video file first!")
            return

        # Get settings
        whisper_model = self.whisper_combo.currentText()
        llm_model = self.llm_combo.currentText()
        prompt = "Identify the most viral, funny, or engaging moments."

        # Determine output dir
        target_dir = self.output_folder if hasattr(self, 'output_folder') else os.path.dirname(self.selected_file)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log_output.clear()

        self.append_log(f"🚀 Starting Pipeline...")
        self.append_log(f"   ► Input: {os.path.basename(self.selected_file)}")
        self.append_log(f"   ► Output: {target_dir}")
        self.append_log(f"   ► Models: Whisper({whisper_model}) + LLM({llm_model})")

        self.pipeline.start_thread(
            video_path=self.selected_file, 
            model_name=llm_model, 
            prompt=prompt,
            output_dir=target_dir,
            whisper_model=whisper_model
        )

    def stop_pipeline(self):
        self.pipeline.stop()
        self.append_log("🛑 Stopping pipeline... please wait.")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def append_log(self, message):
        self.log_output.append(message)
        # Auto-scroll
        cursor = self.log_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_output.setTextCursor(cursor)

        if "Pipeline Finished" in message or "Pipeline Failed" in message:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ViralClipperUI()
    window.show()
    sys.exit(app.exec())
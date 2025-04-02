#!/usr/bin/env python3
import sys, argparse
import os
import json
from datetime import datetime
# you a qtpy
try:
    import qtpy
    print(f"Using QtPy version: {qtpy.__version__}")
except (ImportError, AttributeError):
    print("Warning: QtPy version information not available")
from qtpy.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, 
                           QFileDialog, QLabel, QLineEdit, QWidget, QGroupBox, 
                           QGridLayout, QTextEdit, QSpinBox, QProgressBar, QMessageBox, QComboBox)
from qtpy.QtCore import QThread, Signal, Qt, QRect, QRectF
from qtpy.QtGui import QIcon, QPixmap
import sleap

try:
    from sleapgui.worker import Worker
    from sleapgui.dragdrop import DragDropTextEdit
    from sleapgui.utils import get_video_framerate, set_app_icon
except ModuleNotFoundError:
    from worker import Worker
    from dragdrop import DragDropTextEdit
    from utils import get_video_framerate, set_app_icon

class ModelGUI(QMainWindow):
    def __init__(self, mode='face'):
        super().__init__()
        self.mode = mode
        self.setWindowTitle(f"SLEAP: {mode[0].capitalize()}{mode[1:]} Analysis")
        self.setMinimumSize(800, 600)
        
        set_app_icon(self)

        self.init_ui()
        
    def init_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Input section
        input_group = QGroupBox("Input Configuration")
        input_layout = QGridLayout()
        
        # Model path with dropdown
        self.model_path_label = QLabel("Model Path:")
        self.model_path_combo = QComboBox()
        self.model_path_combo.setEditable(False)
        self.model_path_combo.setMinimumWidth(300)
        
        # Add default options
        self.model_path_combo.addItem("(No model selected)")
        self.model_path_combo.addItem("Browse for model...")
        
        # Add pretrained models if available
        pretrained_models_dir = os.path.join(os.path.dirname(sleap.__file__), "models", "pretrained")
        if os.path.exists(pretrained_models_dir):
            for file in os.listdir(pretrained_models_dir):
                # Accept any file that looks like a SLEAP model
                if file.endswith('.json') or file.endswith('.single_instance') or 'model' in file.lower():
                    self.model_path_combo.addItem(f"Pretrained: {file}", 
                                                os.path.join(pretrained_models_dir, file))
        
        # Load last used model from settings
        self.settings_file = os.path.join(os.path.expanduser("~"), ".sleapgui_settings.json")
        self.load_settings()
        if self.last_model_path:
            self.model_path_combo.addItem(f"Last used: {os.path.basename(self.last_model_path)}", 
                                        self.last_model_path)
        
        self.model_path_combo.activated.connect(self.handle_model_selection)
        
        # Output directory path
        self.output_dir_label = QLabel("Output Directory:")
        self.output_dir_text = QLineEdit()
        self.output_dir_button = QPushButton("Browse...")
        self.output_dir_button.clicked.connect(lambda: self.browse_directory(self.output_dir_text))
        
        # Video paths
        self.video_path_label = QLabel("Video Paths:")
        self.video_paths_list = DragDropTextEdit(self)
        self.video_paths_list.setMaximumHeight(80)

        video_buttons_layout = QVBoxLayout()
        self.video_path_button = QPushButton("Add Videos...")
        self.video_path_button.clicked.connect(self.add_video_paths)
        self.clear_videos_button = QPushButton("Clear")
        self.clear_videos_button.clicked.connect(lambda: self.video_paths_list.clear())
        video_buttons_layout.addWidget(self.video_path_button)
        video_buttons_layout.addWidget(self.clear_videos_button)

        # Frame rate for video creation
        self.frame_rate_label = QLabel("Frame Rate:")
        self.frame_rate_spin = QSpinBox()
        self.frame_rate_spin.setRange(1, 240)
        self.frame_rate_spin.setValue(120)
        
        # Output file naming
        self.output_basename_label = QLabel("Output Base Name:")
        self.output_basename_text = QLineEdit("labels.v001")
        
        ########### LAYOUTS ###########
        input_layout.addWidget(self.model_path_label, 0, 0)
        input_layout.addWidget(self.model_path_combo, 0, 1)
        
        input_layout.addWidget(self.output_dir_label, 1, 0)
        input_layout.addWidget(self.output_dir_text, 1, 1)
        input_layout.addWidget(self.output_dir_button, 1, 2)
        
        input_layout.addWidget(self.video_path_label, 2, 0)
        input_layout.addWidget(self.video_paths_list, 2, 1)
        input_layout.addLayout(video_buttons_layout, 2, 2)
        
        input_layout.addWidget(self.frame_rate_label, 3, 0)
        input_layout.addWidget(self.frame_rate_spin, 3, 1)
        
        input_layout.addWidget(self.output_basename_label, 4, 0)
        input_layout.addWidget(self.output_basename_text, 4, 1)
        
        input_group.setLayout(input_layout)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.analyze_button = QPushButton("Analyze SLEAP Data")
        self.analyze_button.clicked.connect(self.analyze_data)
        
        self.create_video_button = QPushButton("Create Video")
        self.create_video_button.clicked.connect(self.create_video)
        
        self.save_csv_button = QPushButton("Save as CSV")
        self.save_csv_button.clicked.connect(self.save_csv)
        
        self.all_in_one_button = QPushButton("Run Complete Workflow")
        self.all_in_one_button.clicked.connect(self.run_complete_workflow)
        self.all_in_one_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_operation)
        self.cancel_button.setStyleSheet("background-color: #f44336; color: white;")
        self.cancel_button.setEnabled(False)  # Disabled initially, enabled when a task starts
        
        self.clear_all_button = QPushButton("Clear All")
        self.clear_all_button.clicked.connect(self.clear_all_fields)

        action_layout.addWidget(self.analyze_button)
        action_layout.addWidget(self.create_video_button)
        action_layout.addWidget(self.save_csv_button)
        action_layout.addWidget(self.all_in_one_button)
        action_layout.addWidget(self.cancel_button)
        action_layout.addWidget(self.clear_all_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # Log display
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        
        # Add to main layout
        main_layout.addWidget(input_group)
        main_layout.addLayout(action_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(log_group)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
    def browse_file(self, text_field, file_filter, save_mode=False):
        if save_mode:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", file_filter)
        else:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", file_filter)
            
        if file_path:
            text_field.setText(file_path)
            
            # Update other fields based on selection
            if text_field == self.output_path_text:
                # Generate suggested paths for video and CSV based on the .slp path
                base_path = os.path.splitext(file_path)[0]
                self.output_video_text.setText(base_path + ".mp4")
                self.csv_path_text.setText(base_path + ".csv")
    
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.append(formatted_message)
        self.log_text.ensureCursorVisible()
    
    def browse_directory(self, text_field):
        """Browse for a directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", "")
        if directory:
            text_field.setText(directory)

    def analyze_data(self):
        model_path = self.get_model_path()
        output_dir = self.output_dir_text.text()
        video_paths = self.video_paths_list.toPlainText().splitlines()
        base_name = self.output_basename_text.text()
        
        # Validate inputs
        if not model_path or model_path == "Select a model...":
            QMessageBox.warning(self, "Missing Information", "Please select a model.")
            return
        
        # Check if model file exists, but don't validate extension
        model_valid, model_error = self.check_file_requirements(model_path, True)
        if not model_valid:
            QMessageBox.warning(self, "Invalid Model", model_error)
            return
        
        # Check output directory
        if not output_dir:
            QMessageBox.warning(self, "Missing Information", "Please specify an output directory.")
            return
        
        # Create output directory if it doesn't exist
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.warning(self, "Output Directory Error", f"Could not create output directory: {str(e)}")
            return
        
        # Check video paths
        if not video_paths:
            QMessageBox.warning(self, "Missing Information", "Please add at least one video file.")
            return
        
        for video_path in video_paths:
            video_valid, video_error = self.check_file_requirements(video_path, True)
            if not video_valid:
                QMessageBox.warning(self, "Invalid Video", f"Problem with video: {video_path}\n{video_error}")
                return
        
        self.save_settings()

        self.log(f"Starting analysis...")
        self.log(f"Model: {model_path}")
        self.log(f"Output directory: {output_dir}")
        self.log(f"Base name: {base_name}")
        self.log(f"Videos: {len(video_paths)} file(s)")
        for i, video in enumerate(video_paths, 1):
            self.log(f"  {i}. {video}")
        
        self.progress_bar.setValue(0)
        
        params = {
            "model_path": model_path,
            "output_dir": output_dir,
            "base_name": base_name,
            "video_paths": video_paths,
            "mode": self.mode
        }
        
        self.worker = Worker("analyze", params)
        self.worker.progress.connect(self.update_progress)
        self.worker.message.connect(self.log)
        self.worker.finished.connect(self.on_task_finished)
        self.worker.start()
        
        self.disable_buttons()

    def run_complete_workflow(self):
        """Run all three operations in sequence: analyze, save CSV, create video"""
        self.log("Starting complete workflow...")
        
        # Store workflow state
        self.workflow_state = {
            "current_step": "analyze",
            "steps_completed": 0,
            "total_steps": 3,
            "success": True
        }
        
        # Start the first step
        self.analyze_data()

    def on_task_finished(self, success, message):
        """Handle task completion and chain workflow operations"""
        self.enable_buttons()
        
        if success:
            self.progress_bar.setValue(100)
            self.log(f"Success: {message}")
            
            # Check if we're in a workflow
            if hasattr(self, 'workflow_state'):
                current_step = self.workflow_state["current_step"]
                self.workflow_state["steps_completed"] += 1
                
                if not success:
                    self.workflow_state["success"] = False
                    QMessageBox.warning(self, f"Workflow Error", f"Error during {current_step}: {message}")
                    delattr(self, 'workflow_state')
                    return
                
                # Move to next step
                if current_step == "analyze":
                    self.workflow_state["current_step"] = "save_csv"
                    self.log("Workflow: Continuing to CSV export...")
                    self.save_csv()
                elif current_step == "save_csv":
                    self.workflow_state["current_step"] = "create_video"
                    self.log("Workflow: Continuing to video creation...")
                    self.create_video()
                elif current_step == "create_video":
                    # Workflow complete
                    percent_complete = 100
                    self.progress_bar.setValue(percent_complete)
                    self.log("Complete workflow finished successfully!")
                    QMessageBox.information(self, "Workflow Complete", 
                                        "All operations completed successfully!")
                    delattr(self, 'workflow_state')
            else:
                # Single task complete
                QMessageBox.information(self, "Success", message)
        else:
            self.progress_bar.setValue(0)
            self.log(f"Error: {message}")
            
            # Clear workflow state if error
            if hasattr(self, 'workflow_state'):
                delattr(self, 'workflow_state')
                
            QMessageBox.critical(self, "Error", message)

    def clear_all_fields(self):
        """Clear all input fields and reset the interface"""
        # Reset dropdown to first item (no selection)
        self.model_path_combo.setCurrentIndex(0)
        
        # Clear all text fields
        self.output_dir_text.clear()
        self.video_paths_list.clear()
        self.output_basename_text.setText("labels.v001")
        
        # Reset frame rate to default
        self.frame_rate_spin.setValue(120)
        
        # Reset progress bar
        self.progress_bar.setValue(0)
        
        self.log("All fields cleared")

    def cancel_operation(self):
        """Cancel the current operation"""
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.log("Cancelling operation...")
            
            # Signal the worker to stop
            self.worker.cancel_requested = True
            
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText("Cancelling...")

            # Wait for the worker to finish safely
            self.worker.wait(500)  # Wait up to 500ms for clean termination
            
            # Force terminate if still running
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait()  # Wait for termination to complete
                self.log("Operation terminated")
            else:
                self.log("Operation cancelled")
            
            # Clear any workflow state
            if hasattr(self, 'workflow_state'):
                delattr(self, 'workflow_state')
            
            # Reset UI
            self.progress_bar.setValue(0)
            self.enable_buttons()
            self.log("Ready for new operation")
            
            # Disable the cancel button since we're not running anything
            self.cancel_button.setEnabled(False)

    def create_video(self):
        """Create video from .slp files"""
        output_dir = self.output_dir_text.text()
        frame_rate = self.frame_rate_spin.value()
        
        if not output_dir:
            QMessageBox.warning(self, "Missing Information", "Please specify an output directory.")
            return
        
        # Find all .slp files in the output directory
        slp_files = []
        try:
            for file in os.listdir(output_dir):
                if file.endswith(".slp"):
                    slp_files.append(os.path.join(output_dir, file))
        except Exception as e:
            QMessageBox.warning(self, "Directory Error", f"Could not read directory: {str(e)}")
            return
        
        if not slp_files:
            QMessageBox.warning(self, "No SLP Files", f"No .slp files found in {output_dir}")
            return
        
        self.log(f"Creating videos...")
        self.log(f"Output directory: {output_dir}")
        self.log(f"Frame rate: {frame_rate}")
        
        self.progress_bar.setValue(0)
        
        params = {
            "output_dir": output_dir,
            "slp_files": slp_files,
            "frame_rate": frame_rate
        }
        
        self.worker = Worker("create_video", params)
        self.worker.progress.connect(self.update_progress)
        self.worker.message.connect(self.log)
        self.worker.finished.connect(self.on_task_finished)
        self.worker.start()
        
        self.disable_buttons()

    def save_csv(self):
        """Save .slp files as CSV"""
        output_dir = self.output_dir_text.text()
        
        if not output_dir:
            QMessageBox.warning(self, "Missing Information", "Please specify an output directory.")
            return
        
        # Find all .slp files in the output directory
        slp_files = []
        try:
            for file in os.listdir(output_dir):
                if file.endswith(".slp"):
                    slp_files.append(os.path.join(output_dir, file))
        except Exception as e:
            QMessageBox.warning(self, "Directory Error", f"Could not read directory: {str(e)}")
            return
        
        if not slp_files:
            QMessageBox.warning(self, "No SLP Files", f"No .slp files found in {output_dir}")
            return
        
        self.log(f"Saving CSV files...")
        self.log(f"Output directory: {output_dir}")
        
        self.progress_bar.setValue(0)
        
        params = {
            "output_dir": output_dir,
            "slp_files": slp_files
        }
        
        self.worker = Worker("save_csv", params)
        self.worker.progress.connect(self.update_progress)
        self.worker.message.connect(self.log)
        self.worker.finished.connect(self.on_task_finished)
        self.worker.start()
        
        self.disable_buttons()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def on_task_finished(self, success, message):
        self.enable_buttons()
        self.progress_bar.setValue(100 if success else 0)
        
        if success:
            self.log(f"Success: {message}")
            QMessageBox.information(self, "Success", message)
        else:
            self.log(f"Error: {message}")
            QMessageBox.critical(self, "Error", message)
    
    def disable_buttons(self):
        self.analyze_button.setEnabled(False)
        self.create_video_button.setEnabled(False)
        self.save_csv_button.setEnabled(False)
        self.all_in_one_button.setEnabled(False)
        self.clear_all_button.setEnabled(False)
        # Enable the cancel button when operation is in progress
        self.cancel_button.setEnabled(True)

    def enable_buttons(self):
        self.analyze_button.setEnabled(True)
        self.create_video_button.setEnabled(True)
        self.save_csv_button.setEnabled(True)
        self.all_in_one_button.setEnabled(True)
        self.clear_all_button.setEnabled(True)
        # Disable the cancel button when no operation is in progress
        self.cancel_button.setEnabled(False)

    def load_settings(self):
        """Load settings from file"""
        self.last_model_path = ""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.last_model_path = settings.get('last_model_path', '')
            except:
                pass

    def save_settings(self):
        """Save settings to file"""
        settings = {
            'last_model_path': self.get_model_path()
        }
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
        except:
            pass

    def handle_model_selection(self, index):
        """Handle selection from the model dropdown"""
        if index == 1:  # Browse option
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Open Model File", "", "SLEAP Models (*.*)")
            if file_path:
                # Check if this path is already in the dropdown
                found = False
                for i in range(self.model_path_combo.count()):
                    if self.model_path_combo.itemData(i) == file_path:
                        self.model_path_combo.setCurrentIndex(i)
                        found = True
                        break
                
                if not found:
                    # Add the new path
                    self.model_path_combo.addItem(os.path.basename(file_path), file_path)
                    self.model_path_combo.setCurrentIndex(self.model_path_combo.count() - 1)
        
        # Update the line edit display if needed
        selected_data = self.model_path_combo.currentData()
        if selected_data:
            self.log(f"Selected model: {selected_data}")

    def get_model_path(self):
        """Get the current model path"""
        # First try to get the data (for dropdown items with data)
        model_path = self.model_path_combo.currentData()
        # If no data (custom entry), get the text
        if not model_path:
            model_path = self.model_path_combo.currentText()
        return model_path
    
    def check_file_requirements(self, file_path, is_input=True, check_extension=None):
        """Check if file path meets requirements"""
        if not file_path:
            return False, "Path cannot be empty"
        
        if is_input:
            if not os.path.exists(file_path):
                return False, f"File does not exist: {file_path}"
        else:
            # Check if directory is writable
            dir_path = os.path.dirname(file_path)
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path)
                except Exception as e:
                    return False, f"Cannot create directory: {dir_path}\nError: {str(e)}"
            
            if not os.access(dir_path, os.W_OK):
                return False, f"Directory is not writable: {dir_path}"
        
        # Only check file extension if explicitly required and it's not a model file
        if check_extension and not file_path.lower().endswith(check_extension.lower()):
            if "model" not in file_path.lower():  # Skip extension check for model files
                return False, f"File must have {check_extension} extension"
        
        return True, ""
    
    def add_video_paths(self, file_paths=[], dropped=False):
        if not dropped:
            file_paths, _ = QFileDialog.getOpenFileNames(
                self, "Select Video Files", "", "Video Files (*.avi *.mp4 *.mov)")
        
        if file_paths:
            current_text = self.video_paths_list.toPlainText()
            for path in file_paths:
                if current_text:
                    current_text += "\n"
                current_text += path
            self.video_paths_list.setText(current_text)
            
            # If output directory is not specified, suggest one based on first video
            if not self.output_dir_text.text():
                # Use the directory of the first video as output directory
                video_dir = os.path.dirname(file_paths[0])
                self.output_dir_text.setText(video_dir)
            
            # Set frame rate based on the first/most recent video
            most_recent_video = file_paths[0]
            try:
                fps = get_video_framerate(self.log, most_recent_video)
                self.frame_rate_spin.setValue(fps)
                self.log(f"Auto-detected frame rate: {fps} fps from {os.path.basename(most_recent_video)}")
            except Exception as e:
                self.log(f"Could not detect frame rate from {os.path.basename(most_recent_video)}: {str(e)}")
        
    def clear_all_fields(self):
        # Reset dropdown to first item (no selection)
        self.model_path_combo.setCurrentIndex(0)
        
        self.output_dir_text.clear()
        self.video_paths_list.clear()
        self.output_basename_text.setText("labels.v001")
        
        self.frame_rate_spin.setValue(120)
        
        self.progress_bar.setValue(0)
        
        self.log("All fields cleared")
    
    def clear_log(self):
        self.log_text.clear()

def main():
    """Main entry point for the sleapGUI application"""
    parser = argparse.ArgumentParser(description="GUI for SLEAP analysis")
    parser.add_argument('mode', nargs='?', default='face', choices=['face', 'pupil'],
                      help='Analysis mode: "face" for face analysis (default), "pupil" for pupil analysis')
    
    args, _ = parser.parse_known_args()

    app = QApplication(sys.argv)
    
    window = ModelGUI(mode=args.mode)
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
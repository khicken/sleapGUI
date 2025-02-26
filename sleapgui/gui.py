# gui.py
# Last Modified: 2025-02-07

import sys, os
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QFileDialog, QLabel, QProgressBar, QSpinBox, QComboBox)

if getattr(sys, 'frozen', False):  # Running as a bundled executable
    sys.path.insert(0, os.path.dirname(sys.executable))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("mediaGUI")
        self.setMinimumSize(480, 480)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        ## File Selection
        self.file_list = CustomListWidget(self)
        layout.addWidget(QLabel("Selected Videos:"))
        layout.addWidget(self.file_list)
        
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Videos")
        self.add_button.clicked.connect(self.add_videos)
        button_layout.addWidget(self.add_button)
        
        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_selected)
        button_layout.addWidget(self.remove_button)
        layout.addLayout(button_layout)
    
        ## Export Controls
        extract_layout = QHBoxLayout()
        output_fps_layout = QHBoxLayout()
        output_format_layout = QHBoxLayout()
        extract_layout.setContentsMargins(5, 0, 0, 0)
        output_fps_layout.setContentsMargins(5, 0, 0, 0)
        output_format_layout.setContentsMargins(5, 0, 0, 0)

        # First line: Extract frames
        self.frame_extract_spinbox = QSpinBox()
        self.frame_extract_spinbox.setRange(0, 10000)
        self.frame_extract_spinbox.setValue(100)
        self.frame_extract_spinbox.setMinimumWidth(50)
        extract_layout.addWidget(QLabel("Extract "))
        extract_layout.addWidget(self.frame_extract_spinbox)
        self.frame_extract_suffix_label = QLabel('frames per video')
        extract_layout.addWidget(self.frame_extract_suffix_label)
        extract_layout.addStretch()  # Push widgets to the left
        self.frame_extract_spinbox.valueChanged.connect(self.update_step_suffix)

        # Second line: Output FPS
        self.output_fps_spinbox = QSpinBox()
        self.output_fps_spinbox.setRange(1, 120)
        self.output_fps_spinbox.setValue(30)
        self.output_fps_spinbox.setMinimumWidth(40)
        output_fps_layout.addWidget(QLabel("Output FPS: "))
        output_fps_layout.addWidget(self.output_fps_spinbox)
        output_fps_layout.addStretch()  # Push widgets to the left

        # Third line: Output format
        self.output_format_box = QComboBox()
        self.output_formats = ['.mp4', '.avi']
        self.output_format_box.addItems(self.output_formats)
        output_format_layout.addWidget(QLabel("Output format: "))
        output_format_layout.addWidget(self.output_format_box)
        output_format_layout.addStretch()  # Push widgets to the left

        # Add all horizontal layouts to the main layout
        layout.addLayout(extract_layout)
        layout.addLayout(output_fps_layout)
        layout.addLayout(output_format_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Concatenate
        self.concat_button = QPushButton("Process videos")
        self.concat_button.clicked.connect(self.concat_videos)
        self.concat_button.setEnabled(False)
        layout.addWidget(self.concat_button)
        
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        self.video_files = []
        self.last_vid_dir = Path.home()
        self.last_save_dir = Path.home()

    def add_videos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Videos",
            str(self.last_vid_dir),
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*.*)"
        )
        
        if files:
            self.video_files.extend([Path(f) for f in files])
            self.last_vid_dir = Path(files[-1])
            self.file_list.clear()
            self.file_list.addItems([f.name for f in self.video_files])
            # concat button
            cbtxt = "Process video" if len(self.video_files) == 1 else "Process videos"
            self.concat_button.setText(cbtxt)
            self.concat_button.setEnabled(True)


    def remove_selected(self):
        selected_items = self.file_list.selectedItems()
        indices_to_remove = [self.file_list.row(item) for item in selected_items]
        
        # Remove items from video_files in reverse order to avoid index issues
        for idx in sorted(indices_to_remove, reverse=True):
            del self.video_files[idx]
        
        self.file_list.clear()
        self.file_list.addItems([f.name for f in self.video_files])
        if not self.video_files:
            self.concat_button.setEnabled(False)

    def concat_videos(self):
        if self.concat_button.text() == "Cancel":
            self.status_label.setText("Processing cancelled.")
            self.worker.cancel()
            self.reset_ui()
            return
        if not self.video_files:
            self.status_label.setText("Please select videos first!")
            self.concat_button.setEnabled(True)
            return

        default_name = f'concatenated_video{self.output_format_box.currentText()}'
        output_format_dict = {
            '.mp4': 'MP4 Video (*.mp4)',
            '.avi': 'AVI Video (*.avi)'
        }
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Concatenated Video",
            str(Path.home() / default_name),
            output_format_dict[self.output_format_box.currentText()]
        )
        
        if output_path:
            output_path = Path(output_path)
            self.last_save_dir = output_path
            if output_path.suffix.lower() not in output_format_dict:
                output_path = output_path.with_suffix(self.output_format_box.currentText())
                print("stinky! invalid suffix format but it's been patched")
                
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.add_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            self.frame_extract_spinbox.setEnabled(False)
            self.output_fps_spinbox.setEnabled(False)
            self.output_format_box.setEnabled(False)
            
            self.worker = VideoConcatenationWorker(
                self.video_files, 
                output_path,
                frames_per_video=self.frame_extract_spinbox.value(),
                output_fps=self.output_fps_spinbox.value(),
                output_format=self.output_format_box.currentText()
            )
            self.worker.progress.connect(self.update_progress)
            self.worker.finished.connect(self.concatenation_finished)
            self.worker.error.connect(self.concatenation_error)
            self.status_label.setText("Processing...")
            self.worker.start()
            
            # Toggle cancel
            self.concat_button.setText("Cancel")
            self.concat_button.setEnabled(True)
        else:
            self.concat_button.setEnabled(True)

    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def update_step_suffix(self, value):
        self.frame_extract_suffix_label.setText("frame per video" if value == 1 else "frames per video")
        
    def concatenation_finished(self):
        self.status_label.setText("Concatenation complete!")
        self.reset_ui()
        
    def concatenation_error(self, error_message):
        self.status_label.setText(f"Error: {error_message}")
        self.reset_ui()
        
    def reset_ui(self):
        self.progress_bar.setVisible(False)
        self.add_button.setEnabled(True)
        self.remove_button.setEnabled(True)
        self.frame_extract_spinbox.setEnabled(True)
        self.output_fps_spinbox.setEnabled(True)
        self.output_format_box.setEnabled(True)
        self.concat_button.setEnabled(True)
        cbtxt = "Process video" if len(self.video_files) == 1 else "Process videos"
        self.concat_button.setText(cbtxt)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
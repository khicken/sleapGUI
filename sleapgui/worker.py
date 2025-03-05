from PyQt5.QtCore import QThread, pyqtSignal
import sleap
from sleap.io.format.csv import CSVAdaptor
import subprocess

class Worker(QThread):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int)
    
    def __init__(self, task_type, params=None):
        super().__init__()
        self.task_type = task_type
        self.params = params
        
    def run(self):
        try:
            if self.task_type == "analyze":
                model_path = self.params.get("model_path", "")
                output_path = self.params.get("output_path", "")
                video_path = self.params.get("video_path", "")
                
                command = [
                    "sleap-track",
                    "-m", model_path,
                    "--tracking.tracker", "flow",
                    "--tracking.similarity", "centroid",
                    "--tracking.match", "greedy",
                    "--tracking.kf_node_indices", "0,1,2,3,4,5,6,7,8,9,10,11",
                    "-o", output_path,
                    video_path
                ]
                
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                while process.poll() is None:
                    self.progress.emit(50)  # Simulating progress
                
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    self.finished.emit(True, "Analysis completed successfully!")
                else:
                    self.finished.emit(False, f"Error during analysis: {stderr}")
                    
            elif self.task_type == "create_video":
                slp_path = self.params.get("slp_path", "")
                output_video = self.params.get("output_video", "")
                frame_rate = self.params.get("frame_rate", 30)
                
                command = [
                    "sleap-render",
                    "-o", output_video,
                    "-f", str(frame_rate),
                    slp_path
                ]
                
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                while process.poll() is None:
                    self.progress.emit(50)  # Simulating progress
                
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    self.finished.emit(True, "Video created successfully!")
                else:
                    self.finished.emit(False, f"Error creating video: {stderr}")
                    
            elif self.task_type == "save_csv":
                slp_path = self.params.get("slp_path", "")
                csv_path = self.params.get("csv_path", "")
                
                try:
                    # Load the SLEAP dataset
                    labels = sleap.load_file(slp_path)
                    # Export using the correct CSVAdaptor
                    CSVAdaptor.write(csv_path, labels)
                    self.finished.emit(True, "CSV file saved successfully!")
                except Exception as e:
                    self.finished.emit(False, f"Error saving CSV: {str(e)}")
                    
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")
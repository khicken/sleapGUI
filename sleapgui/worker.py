import os
import subprocess
import time
import threading
import queue
import traceback
from qtpy.QtCore import QThread, Signal
import sleap
from sleap.io.format.csv import CSVAdaptor

# Platform-specific imports
if os.name != 'nt':  # For UNIX systems
    import fcntl
    import select

class Worker(QThread):
    progress = Signal(int)
    message = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, task, params):
        super().__init__()
        self.task = task
        self.params = params
        
    def run(self):
        if self.task == "analyze":
            self.analyze_data()
        elif self.task == "create_video":
            self.create_video()
        elif self.task == "save_csv":
            self.save_csv()
    
    def analyze_data(self, mode):
        try:
            model_path = self.params["model_path"]
            output_path = self.params["output_path"]
            video_paths = self.params["video_paths"]
            mode = self.params["mode"]
            
            # Process each video
            for i, video_path in enumerate(video_paths):
                # Update progress for each video
                video_progress = int((i / len(video_paths)) * 100)
                self.progress.emit(video_progress)
                
                self.message.emit(f"Processing video {i+1}/{len(video_paths)}: {os.path.basename(video_path)}")
                
                # For a single video, output directly to the specified path
                # For multiple videos, append an index to the output filename
                current_output = output_path
                if len(video_paths) > 1:
                    base, ext = os.path.splitext(output_path)
                    current_output = f"{base}_{i+1}{ext}"
                
                kf_node_indices = "0,1,2,3,4,5,6,7,8,9,10,11" if mode=="face_analysis" else "0,1,2,3"
                cmd = [
                    "sleap-track",
                    "-m", model_path,
                    "--tracking.tracker", "flow",
                    "--tracking.similarity", "centroid",
                    "--tracking.match", "greedy",
                    "--tracking.kf_node_indices", kf_node_indices,
                    "-o", current_output,
                    video_path
                ]
                
                # Execute the command with pipes
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1  # Line buffered
                )
                
                # Monitor process with timeout and progress updates
                start_time = time.time()
                max_wait_time = 7200  # 2 hours max runtime
                update_interval = 5  # Update message every 5 seconds
                last_update = 0
                
                # Use platform-specific approach for reading output
                if os.name != 'nt':  # UNIX systems - use select
                    # Make the stdout and stderr pipes non-blocking
                    for pipe in [process.stdout, process.stderr]:
                        flags = fcntl.fcntl(pipe.fileno(), fcntl.F_GETFL)
                        fcntl.fcntl(pipe.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)
                    
                    # Collect output
                    stdout_data = []
                    stderr_data = []
                    
                    while True:
                        # Check if the process has terminated
                        return_code = process.poll()
                        
                        # Read any available output
                        readable, _, _ = select.select([process.stdout, process.stderr], [], [], 0.1)
                        
                        for pipe in readable:
                            if pipe == process.stdout:
                                line = process.stdout.readline()
                                if line:
                                    stdout_data.append(line.strip())
                                    self.message.emit(f"[OUTPUT] {line.strip()}")
                            elif pipe == process.stderr:
                                line = process.stderr.readline()
                                if line:
                                    stderr_data.append(line.strip())
                                    self.message.emit(f"[ERROR] {line.strip()}")
                        
                        # Process has terminated and no more output to read
                        if return_code is not None and not readable:
                            break
                        
                        current_time = time.time()
                        elapsed = int(current_time - start_time)
                        
                        # Check for timeout and update message
                        if self._check_timeout_and_update(process, elapsed, max_wait_time, 
                                                        current_time, last_update, update_interval):
                            return
                            
                        last_update = self._update_status_if_needed(current_time, last_update, 
                                                                  update_interval, elapsed)
                        
                        # Short sleep to avoid busy waiting
                        time.sleep(0.1)
                
                else:  # Windows - use threads
                    # Use threads to read output
                    stdout_queue = queue.Queue()
                    stderr_queue = queue.Queue()
                    
                    def read_output(pipe, queue):
                        for line in iter(pipe.readline, ''):
                            queue.put(line.strip())
                        pipe.close()
                    
                    # Start threads to read output
                    stdout_thread = threading.Thread(target=read_output, args=(process.stdout, stdout_queue))
                    stderr_thread = threading.Thread(target=read_output, args=(process.stderr, stderr_queue))
                    stdout_thread.daemon = True
                    stderr_thread.daemon = True
                    stdout_thread.start()
                    stderr_thread.start()
                    
                    stdout_data = []
                    stderr_data = []
                    
                    while process.poll() is None:
                        # Check for output without blocking
                        try:
                            while True:
                                line = stdout_queue.get_nowait()
                                stdout_data.append(line)
                                self.message.emit(f"[OUTPUT] {line}")
                        except queue.Empty:
                            pass
                        
                        try:
                            while True:
                                line = stderr_queue.get_nowait()
                                stderr_data.append(line)
                                self.message.emit(f"[ERROR] {line}")
                        except queue.Empty:
                            pass
                        
                        current_time = time.time()
                        elapsed = int(current_time - start_time)
                        
                        # Check for timeout and update message
                        if self._check_timeout_and_update(process, elapsed, max_wait_time, 
                                                        current_time, last_update, update_interval):
                            return
                            
                        last_update = self._update_status_if_needed(current_time, last_update, 
                                                                  update_interval, elapsed)
                        
                        time.sleep(0.1)
                    
                    # Get any remaining output
                    try:
                        while True:
                            line = stdout_queue.get_nowait()
                            stdout_data.append(line)
                            self.message.emit(f"[OUTPUT] {line}")
                    except queue.Empty:
                        pass
                    
                    try:
                        while True:
                            line = stderr_queue.get_nowait()
                            stderr_data.append(line)
                            self.message.emit(f"[ERROR] {line}")
                    except queue.Empty:
                        pass
                
                # Check for errors
                if process.returncode != 0:
                    error_message = "\n".join(stderr_data)
                    self.message.emit(f"Error processing video: {error_message}")
                    self.finished.emit(False, f"Error processing video {i+1}: {os.path.basename(video_path)}")
                    return
            
            self.progress.emit(100)
            
            if len(video_paths) == 1:
                self.finished.emit(True, "Analysis completed successfully!")
            else:
                self.finished.emit(True, f"Analysis completed successfully for {len(video_paths)} videos!")
    
        except Exception as e:
            import traceback
            self.message.emit(f"Error: {str(e)}")
            self.message.emit(traceback.format_exc())
            self.finished.emit(False, str(e))
    
    def create_video(self):
        try:
            slp_path = self.params["slp_path"]
            output_video = self.params["output_video"]
            frame_rate = self.params["frame_rate"]
            
            self.message.emit(f"Creating video from {slp_path}")
            self.progress.emit(10)
            
            cmd = [
                "sleap-render",
                "-o", output_video,
                "-f", str(frame_rate),
                slp_path
            ]
            
            # Execute command with output piping
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Monitor process with timeout and progress updates
            start_time = time.time()
            max_wait_time = 1800  # 30 minutes max runtime for video rendering
            update_interval = 5  # Update message every 5 seconds
            last_update = 0
            
            # Cross-platform output reading using threads
            stdout_queue = queue.Queue()
            stderr_queue = queue.Queue()
            
            def read_output(pipe, queue):
                for line in iter(pipe.readline, ''):
                    queue.put(line.strip())
                pipe.close()
            
            # Start threads to read output
            stdout_thread = threading.Thread(target=read_output, args=(process.stdout, stdout_queue))
            stderr_thread = threading.Thread(target=read_output, args=(process.stderr, stderr_queue))
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()
            
            self.progress.emit(20)
            
            while process.poll() is None:
                # Check for output without blocking
                try:
                    while True:
                        line = stdout_queue.get_nowait()
                        self.message.emit(f"[OUTPUT] {line}")
                except queue.Empty:
                    pass
                
                stderr_data = []
                try:
                    while True:
                        line = stderr_queue.get_nowait()
                        stderr_data.append(line)
                        self.message.emit(f"[ERROR] {line}")
                except queue.Empty:
                    pass
                
                current_time = time.time()
                elapsed = int(current_time - start_time)
                
                # Check for timeout
                if elapsed > max_wait_time:
                    process.terminate()
                    time.sleep(2)
                    if process.poll() is None:
                        try:
                            process.kill()
                        except:
                            pass
                    self.message.emit("Video creation timed out")
                    self.finished.emit(False, "Video creation process timed out")
                    return
                
                # Update message periodically
                if current_time - last_update >= update_interval:
                    minutes, seconds = divmod(elapsed, 60)
                    time_str = f"{minutes:02d}:{seconds:02d}"
                    self.message.emit(f"Rendering video... (Elapsed time: {time_str})")
                    self.progress.emit(min(80, 20 + int(elapsed / 60)))  # Progress increases with time
                    last_update = current_time
                
                time.sleep(0.1)
            
            # Get any remaining output
            try:
                while True:
                    line = stdout_queue.get_nowait()
                    self.message.emit(f"[OUTPUT] {line}")
            except queue.Empty:
                pass
            
            stderr_data = []
            try:
                while True:
                    line = stderr_queue.get_nowait()
                    stderr_data.append(line)
                    self.message.emit(f"[ERROR] {line}")
            except queue.Empty:
                pass
            
            # Check for errors
            if process.returncode != 0:
                error_message = "\n".join(stderr_data)
                self.message.emit(f"Error creating video: {error_message}")
                self.finished.emit(False, f"Error creating video: {error_message}")
                return
                
            self.progress.emit(100)
            self.finished.emit(True, "Video created successfully!")
            
        except Exception as e:
            self.message.emit(f"Error: {str(e)}")
            self.message.emit(traceback.format_exc())
            self.finished.emit(False, str(e))
    
    def save_csv(self):
        try:
            slp_path = self.params["slp_path"]
            csv_path = self.params["csv_path"]
            
            self.message.emit(f"Loading SLEAP data from {slp_path}")
            self.progress.emit(25)
            
            # Load the SLEAP dataset
            labels = sleap.load_file(slp_path)
            
            self.message.emit("Processing data...")
            self.progress.emit(50)
            
            # Export using the correct CSVAdaptor
            self.message.emit(f"Saving CSV to {csv_path}")
            CSVAdaptor.write(csv_path, labels)
            
            self.progress.emit(100)
            self.finished.emit(True, "CSV file saved successfully!")
            
        except Exception as e:
            import traceback
            self.message.emit(f"Error: {str(e)}")
            self.message.emit(traceback.format_exc())
            self.finished.emit(False, str(e))
    
    # Helper methods to reduce code duplication
    def _check_timeout_and_update(self, process, elapsed, max_wait_time, 
                                current_time, last_update, update_interval):
        """Check if process has timed out, terminate if needed"""
        if elapsed > max_wait_time:
            process.terminate()
            time.sleep(2)
            if process.poll() is None:
                try:
                    process.kill()
                except:
                    pass
            self.message.emit(f"Process timed out after {max_wait_time//3600} hours")
            self.finished.emit(False, "Process timed out")
            return True
        return False
    
    def _update_status_if_needed(self, current_time, last_update, update_interval, elapsed):
        """Update status message with elapsed time if needed"""
        if current_time - last_update >= update_interval:
            minutes, seconds = divmod(elapsed, 60)
            hours, minutes = divmod(minutes, 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.message.emit(f"Working... (Elapsed time: {time_str})")
            return current_time
        return last_update
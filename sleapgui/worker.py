import os
import subprocess
import time
import threading
import queue
import traceback
from qtpy.QtCore import QThread, Signal
import sleap
from sleap.io.format.csv import CSVAdaptor

# For UNIX systems
if os.name != 'nt':
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
        self.cancel_requested = False
        
    def run(self):
        try:
            if self.task == "analyze":
                self.analyze_data()
            elif self.task == "create_video":
                self.create_video()
            elif self.task == "save_csv":
                self.save_csv()
        except Exception as e:
            import traceback
            self.message.emit(f"Error: {str(e)}")
            self.message.emit(traceback.format_exc())
            self.finished.emit(False, str(e))
   
    def analyze_data(self):
        try:
            model_path = self.params["model_path"]
            output_dirs = self.params["output_dirs"]  # Now a list of directories
            base_name = self.params["base_name"]
            video_paths = self.params["video_paths"]
            mode = self.params["mode"]
            
            # Check if we have matching number of videos and output dirs
            if len(output_dirs) != len(video_paths):
                self.message.emit(f"Warning: Number of output directories ({len(output_dirs)}) doesn't match number of videos ({len(video_paths)})")
                # Either use the first directory for all videos or repeat the last directory
                if len(output_dirs) < len(video_paths):
                    output_dirs = output_dirs + [output_dirs[-1]] * (len(video_paths) - len(output_dirs))
                else:
                    output_dirs = output_dirs[:len(video_paths)]
            
            # Process each video with its corresponding output directory
            for i, (video_path, output_dir) in enumerate(zip(video_paths, output_dirs)):
                base_progress = int((i / len(video_paths)) * 100)
                video_weight = 100 / len(video_paths)
                self.progress.emit(int(base_progress + 0.05 * video_weight))

                # Check for cancellation request
                if self.cancel_requested:
                    self.message.emit("Analysis cancelled by user")
                    self.finished.emit(False, "Operation cancelled")
                    return
                
                self.message.emit(f"Processing video {i+1}/{len(video_paths)}: {os.path.basename(video_path)}")
                self.message.emit(f"Output directory: {output_dir}")
                
                # Make sure output directory exists
                os.makedirs(output_dir, exist_ok=True)
                
                # Extract video name without extension for output naming
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                
                slp_output = os.path.join(output_dir, f"{base_name}.slp")
                
                kf_node_indices = "0,1,2,3,4,5,6,7,8,9,10,11" if mode=="face" else "0,1,2,3"
                cmd = [
                    "sleap-track",
                    "-m", model_path,
                    "--tracking.tracker", "flow",
                    "--tracking.similarity", "centroid",
                    "--tracking.match", "greedy",
                    "--tracking.kf_node_indices", kf_node_indices,
                    "-o", slp_output,
                    video_path
                ]
                
                # Execute the command with pipes
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                def calc_progress(elapsed):
                    return min(95, elapsed / 60)

                success, error = self.__monitor_process(
                    process=process,
                    max_wait_time=86400,  # 2 hours
                    update_interval=5,
                    process_description=f"Analyzing video {i+1}/{len(video_paths)}",
                    base_progress=base_progress,
                    progress_weight=video_weight,
                    progress_calc_func=calc_progress
                )

                # Check for errors
                if not success:
                    self.finished.emit(False, f"Error processing video {i+1}: {os.path.basename(video_path)}\n{error}")
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
            output_dirs = self.params["output_dirs"]
            slp_files = self.params.get("slp_files", [])
            frame_rate = self.params["frame_rate"]
            video_format = self.params.get("video_format", "mp4")
            
            # If no specific slp files provided, scan all directories
            if not slp_files:
                for output_dir in output_dirs:
                    if os.path.exists(output_dir):
                        for file in os.listdir(output_dir):
                            if file.endswith(".slp"):
                                slp_files.append(os.path.join(output_dir, file))
            
            self.message.emit(f"Creating videos for {len(slp_files)} .slp files across {len(output_dirs)} directories")

            for i, slp_path in enumerate(slp_files):
                if self.cancel_requested:
                    self.message.emit("Analysis cancelled by user")
                    self.finished.emit(False, "Operation cancelled")
                    return
                
                # Update progress
                progress = int((i / len(slp_files)) * 100)
                self.progress.emit(progress)
                
                # Create video path by replacing .slp extension with chosen format
                video_path = os.path.splitext(slp_path)[0] + f".{video_format}"
                
                self.message.emit(f"Rendering video {i+1}/{len(slp_files)}: {os.path.basename(video_path)}")
                
                cmd = [
                    "sleap-render",
                    "-o", video_path,
                    "-f", str(frame_rate),
                    slp_path
                ]
                
                # Execute the command
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                # For monitoring
                base_progress = int((i / len(slp_files)) * 100)
                video_weight = 100 / len(slp_files)
                def calc_progress(elapsed):
                    return min(95, elapsed / 60)

                success, error = self.__monitor_process(
                    process=process,
                    max_wait_time=7200,  # 2 hours
                    update_interval=5,
                    process_description=f"Analyzing video {i+1}/{len(output_dirs)}",
                    base_progress=base_progress,
                    progress_weight=video_weight,
                    progress_calc_func=calc_progress
                )

                if not success:
                    self.finished.emit(False, f"Error processing video {i+1}: {os.path.basename(video_path)}\n{error}")
                    return
                
                self.message.emit(f"Successfully created video: {os.path.basename(video_path)}")
                
            self.progress.emit(100)
            
            if len(slp_files) == 1:
                self.finished.emit(True, "Video created successfully!")
            else:
                self.finished.emit(True, f"All {len(slp_files)} videos created successfully!")
                
        except Exception as e:
            self.message.emit(f"Error: {str(e)}")
            self.message.emit(traceback.format_exc())
            self.finished.emit(False, str(e))

    def save_csv(self):
        try:
            output_dirs = self.params["output_dirs"]
            slp_files = self.params.get("slp_files", [])
            video_paths = self.params["video_paths"]
            base_name = self.params["base_name"]
            
            # If no specific slp files provided, scan all directories
            if not slp_files:
                for output_dir in output_dirs:
                    if os.path.exists(output_dir):
                        for file in os.listdir(output_dir):
                            if file.endswith(".slp"):
                                slp_files.append(os.path.join(output_dir, file))
            
            self.message.emit(f"Converting {len(slp_files)} .slp files to CSV")
            
            for i, (video_path, slp_path) in enumerate(zip(video_paths, slp_files)):
                if self.cancel_requested:
                    self.message.emit("CSV saving cancelled by user")
                    self.finished.emit(False, "Operation cancelled")
                    return
                
                progress = int((i / len(slp_files)) * 100)
                self.progress.emit(progress)
                
                try:
                    slp_dir = os.path.dirname(slp_path)
                    slp_basename = os.path.basename(slp_path)
                    slp_base = os.path.splitext(slp_basename)[0]
                    
                    video_base =  os.path.splitext(os.path.basename(video_path))[0]
                    
                    csv_name = f"{base_name}.000_{video_base}.analysis.csv"
                    csv_name = csv_name.replace('__', '_').replace('_.', '.').replace('..', '.')
                    csv_path = os.path.join(slp_dir, csv_name)
                    
                    self.message.emit(f"Converting {slp_basename} to CSV...")
                    labels = sleap.load_file(slp_path)
                    CSVAdaptor.write(csv_path, labels)
                    self.message.emit(f"Saved CSV: {os.path.basename(csv_path)}")
                except Exception as e:
                    self.message.emit(f"Error converting {slp_path}: {str(e)}")
                    # Continue with other files
            
            self.progress.emit(100)
            self.finished.emit(True, f"Converted {len(slp_files)} files to CSV format")
            
        except Exception as e:
            import traceback
            self.message.emit(f"Error: {str(e)}")
            self.message.emit(traceback.format_exc())
            self.finished.emit(False, str(e))
    
    def __monitor_process(self, process, max_wait_time, update_interval, 
                   process_description, start_time=time.time(), base_progress=0, progress_weight=100,
                   progress_calc_func=None):
        """
        Monitor a subprocess with output capture, progress updates, and timeout handling.
        
        Args:
            process: subprocess.Popen object to monitor
            start_time: Time when process started
            max_wait_time: Maximum seconds to allow process to run before timeout
            update_interval: How often to update status (seconds)
            process_description: Description for status messages (e.g., "Analyzing video")
            base_progress: Starting progress percentage
            progress_weight: Weight of this process in overall progress calculation
            progress_calc_func: Function to calculate progress (takes elapsed time, returns percentage)
            
        Returns:
            tuple: (success (bool), error_message (str))
        """
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

        self.progress.emit(base_progress)

        stderr_data = []
        last_update = 0
        last_progress_message = None

        while process.poll() is None:
            if self.cancel_requested:
                process.terminate()
                time.sleep(0.5)
                if process.poll() is None:
                    process.kill()
                self.message.emit(f"{process_description} cancelled by user")
                return False, "Operation cancelled"
            
            # Process stdout
            try:
                while True:
                    line = stdout_queue.get_nowait()
                    self.message.emit(f"[OUTPUT] {line}")
            except queue.Empty:
                pass
            
            # Process stderr
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
                timeout_msg = f"{process_description} timed out"
                self.message.emit(timeout_msg)
                return False, timeout_msg
            
            # Update message and progress periodically
            if current_time - last_update >= update_interval:
                minutes, seconds = divmod(elapsed, 60)
                time_str = f"{minutes:02d}:{seconds:02d}"
                self.message.emit(f"{process_description}... (Elapsed time: {time_str})")
                progress_message = f"{process_description}... (Elapsed time: {time_str})"
                
                # If this is a new progress message, send it normally
                if last_progress_message is None:
                    self.message.emit(progress_message)
                else:
                    # For updates, send a special signal
                    self.message.emit(f"UPDATE_LAST_LINE:{progress_message}")
                
                last_progress_message = progress_message
                
                # Calculate progress
                if progress_calc_func:
                    progress_pct = progress_calc_func(elapsed)
                    scaled_progress = int(base_progress + (progress_pct / 100) * progress_weight)
                    self.progress.emit(scaled_progress)
                
                last_update = current_time
                
            time.sleep(0.1)

        # Get any remaining output
        try:
            while True:
                line = stdout_queue.get_nowait()
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
            self.message.emit(f"Error during {process_description.lower()}: {error_message}")
            return False, error_message
        
        return True, ""
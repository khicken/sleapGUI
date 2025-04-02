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
   
    def create_video(self):
        try:
            output_dir = self.params["output_dir"]
            slp_files = self.params.get("slp_files", [])
            frame_rate = self.params["frame_rate"]
            
            # If no specific slp files provided, scan the directory
            if not slp_files:
                for file in os.listdir(output_dir):
                    if file.endswith(".slp"):
                        slp_files.append(os.path.join(output_dir, file))
            
            self.message.emit(f"Creating videos for {len(slp_files)} .slp files")
            
            for i, slp_path in enumerate(slp_files):
                if self.cancel_requested:
                    self.message.emit("Analysis cancelled by user")
                    self.finished.emit(False, "Operation cancelled")
                    return
                
                # Update progress
                progress = int((i / len(slp_files)) * 100)
                self.progress.emit(progress)
                
                # Create video path by replacing .slp extension with .mp4
                video_path = os.path.splitext(slp_path)[0] + ".mp4"
                
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

                stderr_data = []

                while not process.poll():
                    if self.cancel_requested:
                        process.terminate()
                        time.sleep(0.5)
                        if process.poll() is None:
                            process.kill()
                        self.message.emit("Analysis cancelled by user")
                        self.finished.emit(False, "Operation cancelled")
                        return

                    # Check for output without blocking
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
                
                # Remaining output
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
                    self.message.emit(f"Error creating video: {error_message}")
                    self.finished.emit(False, f"Error creating video: {error_message}")
                    return
                
                self.message.emit(f"Successfully created video: {os.path.basename(video_path)}")
                
            # All videos completed successfully
            self.progress.emit(100)
            
            if len(slp_files) == 1:
                self.finished.emit(True, "Video created successfully!")
            else:
                self.finished.emit(True, f"All {len(slp_files)} videos created successfully!")
                
        except Exception as e:
            self.message.emit(f"Error: {str(e)}")
            self.message.emit(traceback.format_exc())
            self.finished.emit(False, str(e))

    def analyze_data(self):
        try:
            model_path = self.params["model_path"]
            output_dir = self.params["output_dir"]
            base_name = self.params["base_name"]
            video_paths = self.params["video_paths"]
            mode = self.params["mode"]
            
            # Process each video
            for i, video_path in enumerate(video_paths):
                base_progress = int((i / len(video_paths)) * 100)
                video_weight = 100 / len(video_paths)
                self.progress.emit(int(base_progress + 0.05 * video_weight))

                # Check for cancellation request
                if self.cancel_requested:
                    self.message.emit("Analysis cancelled by user")
                    self.finished.emit(False, "Operation cancelled")
                    return
                
                self.message.emit(f"Processing video {i+1}/{len(video_paths)}: {os.path.basename(video_path)}")
                
                # Extract video name without extension for output naming
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                
                # The output .slp path for this video in the main output directory (no subfolders)
                slp_output = os.path.join(output_dir, f"{video_name}_{base_name}.slp")
                
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
                    bufsize=1  # Line buffered
                )
                
                # The rest of your existing process monitoring code stays the same
                # Monitor process with timeout and progress updates
                start_time = time.time()
                max_wait_time = 7200  # 2 hours max runtime for analysis
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

                stderr_data = []
                while process.poll() is None:
                    if self.cancel_requested:
                        process.terminate()
                        time.sleep(0.5)
                        if process.poll() is None:
                            process.kill()
                        self.message.emit("Analysis cancelled by user")
                        self.finished.emit(False, "Operation cancelled")
                        return
                    
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
                        self.message.emit("Video analysis timed out")
                        self.finished.emit(False, f"Analysis of video {i+1} timed out: {os.path.basename(video_path)}")
                        return
                    
                    # Update message periodically
                    if current_time - last_update >= update_interval:
                        minutes, seconds = divmod(elapsed, 60)
                        time_str = f"{minutes:02d}:{seconds:02d}"
                        self.message.emit(f"Analyzing video... (Elapsed time: {time_str})")
                        
                        # Progress for this video scaled to its portion of the total
                        # Limit to 95% completion for this video until it's actually done
                        progress_pct = min(95, elapsed / 60)  # Estimate based on time
                        video_progress = int(base_progress + (progress_pct / 100) * video_weight)
                        self.progress.emit(video_progress)
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

    def save_csv(self):
        try:
            output_dir = self.params["output_dir"]
            slp_files = self.params.get("slp_files", [])
            
            # If no specific slp files provided, scan the directory recursively
            if not slp_files:
                # Walk through directory and subdirectories
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        if file.endswith(".slp"):
                            slp_files.append(os.path.join(root, file))
            
            self.message.emit(f"Found {len(slp_files)} .slp files to convert to CSV")
            
            video_files_by_dir = {}
            
            # Find video files in each directory that contains .slp files
            slp_dirs = set(os.path.dirname(slp) for slp in slp_files)
            for dir_path in slp_dirs:
                video_files = []
                for file in os.listdir(dir_path):
                    if file.lower().endswith((".avi", ".mp4", ".mov")):
                        video_files.append(os.path.join(dir_path, file))
                video_files_by_dir[dir_path] = video_files
            
            for i, slp_path in enumerate(slp_files):
                if self.cancel_requested:
                    self.message.emit("CSV saving cancelled by user")
                    self.finished.emit(False, "Operation cancelled")
                    return
                
                progress = int((i / len(slp_files)) * 100)
                self.progress.emit(progress)
                
                try:
                    # Get directory and file info
                    slp_dir = os.path.dirname(slp_path)
                    slp_basename = os.path.basename(slp_path)
                    slp_base = os.path.splitext(slp_basename)[0]
                    
                    # Look for matching videos in the same directory as the .slp file
                    matching_video = None
                    video_base = None
                    
                    if slp_dir in video_files_by_dir:
                        for video_path in video_files_by_dir[slp_dir]:
                            video_filename = os.path.basename(video_path)
                            video_name = os.path.splitext(video_filename)[0]
                            
                            # Check if this video name is part of the slp filename
                            if video_name in slp_base:
                                matching_video = video_path
                                video_base = video_name
                                break
                    
                    # If no direct match, try to extract from slp name using base_name pattern
                    if not matching_video:
                        # Try to extract video name by splitting on underscore and base_name
                        video_name = slp_base
                        basename_parts = self.params.get("base_name", "labels.v001").split('.')
                        
                        if len(basename_parts) > 0:
                            # Look for parts of the base name in the slp filename
                            for part in basename_parts:
                                if part in slp_base and len(part) > 2:  # Avoid splitting on small parts
                                    parts = slp_base.split(part, 1)
                                    if parts[0]:
                                        video_name = parts[0].rstrip('_')
                                        break
                        
                        # If we extracted a video name, try to find a matching file
                        if video_name != slp_base and slp_dir in video_files_by_dir:
                            for video_path in video_files_by_dir[slp_dir]:
                                if video_name in os.path.basename(video_path):
                                    matching_video = video_path
                                    video_base = video_name
                                    break
                    
                    # Create CSV name in the right format
                    if matching_video:
                        video_basename = os.path.basename(matching_video)
                        video_base = os.path.splitext(video_basename)[0]
                        self.message.emit(f"Matched SLP with video: {video_basename}")
                    else:
                        video_base = video_name
                        self.message.emit(f"No matching video found for {slp_basename}, using extracted name.")
                    
                    # Create CSV name that follows your desired format
                    csv_name = f"{slp_base}.000_{video_base}.analysis.csv"
                    # Make sure we don't have double underscores or strange characters
                    csv_name = csv_name.replace('__', '_').replace('_.', '.')
                    csv_path = os.path.join(slp_dir, csv_name)
                    
                    self.message.emit(f"Converting {os.path.basename(slp_path)} to CSV...")
                    labels = sleap.load_file(slp_path)
                    CSVAdaptor.write(csv_path, labels)
                    self.message.emit(f"Saved CSV: {csv_path}")
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
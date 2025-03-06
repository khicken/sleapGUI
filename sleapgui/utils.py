# look ik this file violates SDLC principles but it's just a bunch of utility functions
import cv2, os

def get_video_framerate(log, video_path):
    """Get the frame rate of a video file using OpenCV"""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return 30  # Default value if can't open
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        
        if fps <= 0 or fps > 1000:  # Sanity check
            return 30
        
        return int(round(fps))
    except Exception as e:
        log(f"Warning: Could not get frame rate from video, using default. Error: {str(e)}")
        return 30  # Default value if something goes wrong

def set_app_icon(window):
    try:
        from PyQt5.QtGui import QIcon
        icon_url = "https://raw.githubusercontent.com/khicken/sleapGUI/main/assets/sleapgui.ico"
        icon_path = os.path.join(os.path.expanduser("~"), ".sleapgui", "icon.ico")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(icon_path), exist_ok=True)
        
        # Download icon if needed
        if not os.path.exists(icon_path):
            try:
                # Try requests first
                import requests
                response = requests.get(icon_url)
                with open(icon_path, 'wb') as f:
                    f.write(response.content)
            except:
                # Fall back to urllib
                import urllib.request
                urllib.request.urlretrieve(icon_url, icon_path)
        
        # Set the icon
        if os.path.exists(icon_path):
            window.setWindowIcon(QIcon(icon_path))
    except Exception as e:
        window.log(f"Could not set application icon: {str(e)}")
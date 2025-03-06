import os
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import QTextEdit

class DragDropTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.parent = parent
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)
    
    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            urls = event.mimeData().urls()
            
            video_extensions = ['.mp4', '.avi', '.mov']
            file_paths = []
            for url in urls:
                path = url.toLocalFile()
                ext = os.path.splitext(path)[1].lower()
                if ext in video_extensions:
                    file_paths.append(path)

            if self.parent and hasattr(self.parent, 'add_video_paths'):
                self.parent.add_video_paths(file_paths=file_paths, dropped=True)
        else:
            super().dropEvent(event)
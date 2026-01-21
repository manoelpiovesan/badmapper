import cv2
import numpy as np

class Media:
    def __init__(self, path):
        self.path = path
        self.is_video = path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))

        if self.is_video:
            self.cap = cv2.VideoCapture(path)
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            ret, frame = self.cap.read()
            if ret:
                self.original_frame = frame
                self.height, self.width = frame.shape[:2]
            else:
                raise ValueError("Failed to read video")
        else:
            self.original_frame = cv2.imread(path)
            if self.original_frame is None:
                raise ValueError("Failed to load image")
            self.height, self.width = self.original_frame.shape[:2]
            self.cap = None

    def get_current_frame(self):
        if self.is_video and self.cap:
            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            return frame if ret else self.original_frame
        return self.original_frame

    def release(self):
        if self.cap:
            self.cap.release()

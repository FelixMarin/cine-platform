import json
import os
from modules.core import OptimizationState
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))

class StateManager:
    def __init__(self, state_file="state.json"):
        self.state_file = state_file
        self.state = OptimizationState()
        self.load()

    def save(self):
        try:
            data = {
                "current_video": self.state.current_video,
                "current_step": self.state.current_step,
                "history": self.state.history,
                "video_info": self.state.video_info
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def load(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.state.current_video = data.get("current_video")
                    self.state.current_step = data.get("current_step", 0)
                    self.state.history = data.get("history", [])
                    self.state.video_info = data.get("video_info", {})
            except Exception as e:
                logger.error(f"Error loading state: {e}")

    def update_log(self, line):
        self.state.log_line = line

    def set_current_video(self, name):
        self.state.current_video = name
        self.save()

    def set_step(self, step):
        self.state.current_step = step
        self.save()

    def set_video_info(self, info):
        self.state.video_info = info
        self.save()

    def add_history(self, entry):
        self.state.history.append(entry)
        self.save()

    def reset(self):
        self.state.current_video = None
        self.state.current_step = 0
        self.state.video_info = {}
        self.save()
import os
import subprocess
import json
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ["LOG_FOLDER"])

class FFmpegHandler:
    def __init__(self, state_manager):
        self.state_manager = state_manager

    def get_gpu_decoder(self):
        if os.path.exists("/usr/lib/aarch64-linux-gnu/tegra"):
            return "h264_nvv4l2dec"
        return None

    def get_gpu_encoder(self):
        if os.path.exists("/usr/lib/aarch64-linux-gnu/tegra"):
            return "libx264" 
        return "libx264"

    def execute(self, cmd_args):
        logger.debug(f"CMD: {' '.join(cmd_args)}")
        with subprocess.Popen(
            cmd_args, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            universal_newlines=True, 
            bufsize=1
        ) as process:
            for line in process.stdout:
                line = line.strip()
                if "frame=" in line or "time=" in line:
                    stats = [x for x in line.split() if "=" in x]
                    log_line = " | ".join(stats).replace("frame=", "frames=")
                    self.state_manager.update_log(log_line)
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd_args)
        self.state_manager.update_log("")

    def get_video_info(self, video_path):
        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", video_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            format_info = data.get("format", {})
            streams = data.get("streams", [])
            v_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
            a_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
            size_mb = round(int(format_info.get("size", 0)) / (1024 * 1024), 2)
            
            return {
                "name": os.path.basename(video_path),
                "duration": format_info.get("duration", "0"),
                "resolution": f"{v_stream.get('width', '??')}x{v_stream.get('height', '??')}",
                "format": format_info.get("format_name", "desconocido"),
                "vcodec": v_stream.get("codec_name", "desconocido"),
                "acodec": a_stream.get("codec_name", "desconocido"),
                "size": f"{size_mb} MB"
            }
        except Exception as e:
            logger.error(f"Error info video: {e}")
            return {}

    def get_duration(self, video_path):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True,
            )
            return float(result.stdout.strip())
        except subprocess.CalledProcessError:
            return 0.0
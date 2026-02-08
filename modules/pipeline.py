class PipelineSteps:
    def __init__(self, ffmpeg_handler):
        self.ffmpeg = ffmpeg_handler

    def repair(self, input_path, output_path):
        cmd = ["ffmpeg", "-y", "-i", input_path, "-c", "copy", output_path]
        self.ffmpeg.execute(cmd)

    def reduce(self, input_path, output_path):
        decoder = self.ffmpeg.get_gpu_decoder()
        cmd = ["ffmpeg", "-y"]
        if decoder: cmd.extend(["-c:v", decoder])
        
        cmd.extend([
            "-i", input_path, 
            "-c:v", "libx264", "-preset", "veryfast", "-b:v", "2M", 
            "-vf", "scale=1280:720", "-c:a", "aac", 
            output_path
        ])
        self.ffmpeg.execute(cmd)

    def optimize(self, input_path, output_path):
        decoder = self.ffmpeg.get_gpu_decoder()
        encoder = self.ffmpeg.get_gpu_encoder()
        
        cmd = ["ffmpeg", "-y"]
        if decoder: cmd.extend(["-c:v", decoder])
        cmd.extend(["-i", input_path, "-c:v", encoder])
        
        if encoder == "libx264":
            cmd.extend(["-preset", "slow", "-crf", "23", "-b:v", "1000k"])
        else:
            cmd.extend(["-b:v", "1000k"])
            
        cmd.extend([
            "-r", "30", "-vf", "scale=1280:720", 
            "-c:a", "aac", "-movflags", "faststart", 
            output_path
        ])
        self.ffmpeg.execute(cmd)
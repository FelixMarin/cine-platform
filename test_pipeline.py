import os
from modules.pipeline import PipelineSteps
from modules.ffmpeg import FFmpegHandler
from modules.state import StateManager

input_path = "./temp/28 anos despues.mkv"
output_path = "./temp/28 anos despues-optimized.mkv"

state = StateManager()
ff = FFmpegHandler(state)
pipeline = PipelineSteps(ff)

print("Iniciando pipeline directo...")
pipeline.process(input_path, output_path)
print("Pipeline finalizado.")

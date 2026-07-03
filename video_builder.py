import os
import re
import subprocess
from config import Config


class VideoBuilder:
    def create_list_file(self):
        files = [f for f in os.listdir(Config.OUTPUT_DIR) if f.endswith(".ts")]

        def segment_number(name):
            match = re.search(r'-(\d+)\.ts$', name)
            return int(match.group(1)) if match else -1

        files.sort(key=segment_number)

        with open("list.txt", "w", encoding="utf-8") as f:
            for file in files:
                path = os.path.join(Config.OUTPUT_DIR, file).replace("\\", "/")
                f.write(f"file '{path}'\n")

        print("list.txt создан")

    def merge_video(self, output_file):
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", "list.txt",
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            output_file
        ]
        subprocess.run(cmd)
        print("Готово:", output_file)
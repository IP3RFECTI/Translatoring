import os
import re
import subprocess
import time
import requests
from yandex_disk_client import YandexDiskClient


class VideoTranslator:
    def __init__(self):
        self.disk_client = YandexDiskClient()
        self.audio_file = "translation.mp3"

    def translate(self, video_file):
        disk_file = f"app:/{video_file}"
        translated_file = video_file.replace(".mp4", "_translated.mp4")

        try:
            self.disk_client.upload_file(video_file, disk_file)
            self.disk_client.publish_file(disk_file)
            time.sleep(5)
            public_url = self.disk_client.get_public_url(disk_file)
            audio_url = self._run_vot(public_url)
            self._download_audio(audio_url)
            self._replace_audio(video_file, translated_file)
            print("\nDONE")
        finally:
            try:
                self.disk_client.delete_file(disk_file)
            except:
                pass
            self._cleanup()

        return translated_file

    def _run_vot(self, url):
        print("Running vot-cli...")
        cmd = f'vot-cli {url}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        output = result.stdout + result.stderr
        print(output)

        match = re.search(r'https://[^\s"]+\.mp3[^\s"]*', output)
        if not match:
            raise Exception("Audio link not found")

        audio_url = match.group(0)
        print("Audio URL:", audio_url)
        return audio_url

    def _download_audio(self, audio_url):
        print("Downloading translated audio...")
        r = requests.get(audio_url, stream=True)
        with open(self.audio_file, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        print("Audio downloaded")

    def _replace_audio(self, input_video, output_video):
        print("Replacing audio track...")
        subprocess.run([
            "ffmpeg",
            "-y",
            "-i", input_video,
            "-i", self.audio_file,
            "-c:v", "copy",
            "-map", "0:v:0",
            "-map", "1:a:0",
            output_video
        ], check=True)
        print("New video created:", output_video)

    def _cleanup(self):
        if os.path.exists(self.audio_file):
            os.remove(self.audio_file)
            print(f"Удален файл: {self.audio_file}")
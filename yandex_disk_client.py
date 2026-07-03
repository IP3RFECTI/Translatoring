import requests
from config import Config


class YandexDiskClient:
    def __init__(self):
        self.headers = {"Authorization": f"OAuth {Config.TOKEN}"}

    def upload_file(self, local_path, disk_path):
        print("Getting upload URL...")
        r = requests.get(
            f"{Config.BASE_URL}/resources/upload",
            headers=self.headers,
            params={"path": disk_path, "overwrite": "true"}
        )
        r.raise_for_status()
        upload_url = r.json()["href"]

        print("Uploading video...")
        with open(local_path, "rb") as f:
            requests.put(upload_url, data=f).raise_for_status()
        print("Upload complete")

    def publish_file(self, disk_path):
        requests.put(
            f"{Config.BASE_URL}/resources/publish",
            headers=self.headers,
            params={"path": disk_path}
        ).raise_for_status()
        print("File published")

    def get_public_url(self, disk_path):
        r = requests.get(
            f"{Config.BASE_URL}/resources",
            headers=self.headers,
            params={"path": disk_path}
        )
        r.raise_for_status()
        url = r.json()["public_url"]
        print("Public URL:", url)
        return url

    def delete_file(self, disk_path):
        print("Deleting file from Yandex Disk...")
        r = requests.delete(
            f"{Config.BASE_URL}/resources",
            headers=self.headers,
            params={"path": disk_path, "permanently": "true"}
        )
        r.raise_for_status()
        print("File deleted from Yandex Disk")
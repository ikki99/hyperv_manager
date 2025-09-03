import requests
import threading
import os
import time

class DownloadManager:
    def __init__(self, download_folder="./downloads", on_progress=None, on_complete=None, on_error=None):
        self.download_folder = download_folder
        os.makedirs(self.download_folder, exist_ok=True)
        self.downloads = {}
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error

    def _download_task(self, url, filename, download_id):
        try:
            filepath = os.path.join(self.download_folder, filename)
            response = requests.get(url, stream=True)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.downloads[download_id]['status'] == 'cancelled':
                        os.remove(filepath)
                        return
                    if self.downloads[download_id]['status'] == 'paused':
                        while self.downloads[download_id]['status'] == 'paused':
                            time.sleep(1) # Wait while paused
                        if self.downloads[download_id]['status'] == 'cancelled':
                            os.remove(filepath)
                            return

                    f.write(chunk)
                    downloaded_size += len(chunk)
                    progress = (downloaded_size / total_size) * 100 if total_size > 0 else 0
                    self.downloads[download_id]['progress'] = progress
                    self.downloads[download_id]['downloaded_size'] = downloaded_size
                    if self.on_progress:
                        self.on_progress(download_id, progress, downloaded_size, total_size)

            self.downloads[download_id]['status'] = 'completed'
            if self.on_complete:
                self.on_complete(download_id, filepath)

        except requests.exceptions.RequestException as e:
            self.downloads[download_id]['status'] = 'failed'
            self.downloads[download_id]['error'] = str(e)
            if self.on_error:
                self.on_error(download_id, str(e))
        except Exception as e:
            self.downloads[download_id]['status'] = 'failed'
            self.downloads[download_id]['error'] = str(e)
            if self.on_error:
                self.on_error(download_id, str(e))

    def start_download(self, url, filename):
        download_id = str(time.time()) # Simple unique ID
        self.downloads[download_id] = {
            'url': url,
            'filename': filename,
            'filepath': os.path.join(self.download_folder, filename),
            'status': 'downloading',
            'progress': 0,
            'downloaded_size': 0,
            'total_size': 0,
            'thread': None
        }
        thread = threading.Thread(target=self._download_task, args=(url, filename, download_id))
        self.downloads[download_id]['thread'] = thread
        thread.start()
        return download_id

    def pause_download(self, download_id):
        if download_id in self.downloads and self.downloads[download_id]['status'] == 'downloading':
            self.downloads[download_id]['status'] = 'paused'

    def resume_download(self, download_id):
        if download_id in self.downloads and self.downloads[download_id]['status'] == 'paused':
            self.downloads[download_id]['status'] = 'downloading'

    def cancel_download(self, download_id):
        if download_id in self.downloads and self.downloads[download_id]['status'] in ['downloading', 'paused']:
            self.downloads[download_id]['status'] = 'cancelled'

    def get_download_status(self, download_id):
        return self.downloads.get(download_id)

    def get_all_downloads(self):
        return self.downloads

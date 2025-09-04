import os
import json
import threading
import time
import requests

class DownloadManager:
    def __init__(self, config_dir=".", downloads_dir="downloads"):
        self.config_dir = config_dir
        self.downloads_dir = downloads_dir
        os.makedirs(self.downloads_dir, exist_ok=True)
        self.downloads_file = os.path.join(self.config_dir, "downloads.json")
        self.lock = threading.Lock()
        self.downloads = self._load_downloads()
        self.threads = {}
        self.pause_events = {}

    def _load_downloads(self):
        if os.path.exists(self.downloads_file):
            try:
                with open(self.downloads_file, "r", encoding="utf-8") as f:
                    # Don't load 'downloading' or 'paused' as active, reset them
                    data = json.load(f)
                    for url, d in data.items():
                        if d.get('status') in ['downloading', 'paused']:
                            d['status'] = 'stopped'
                    return data
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_downloads(self):
        with self.lock:
            with open(self.downloads_file, "w", encoding="utf-8") as f:
                json.dump(self.downloads, f, indent=4)

    def get_all_downloads(self):
        with self.lock:
            return self.downloads.copy()

    def get_download_status(self, url):
        with self.lock:
            return self.downloads.get(url)

    def start_download(self, url, filename):
        with self.lock:
            if url in self.threads and self.threads[url].is_alive():
                return False, "Download already in progress."

            self.downloads[url] = {
                "filename": filename,
                "status": "downloading",
                "progress": 0,
                "total_size": 0,
                "downloaded_size": 0,
                "error_message": None,
                "cancel_flag": False
            }
            self.pause_events[url] = threading.Event()

        thread = threading.Thread(target=self._downloader, args=(url,))
        thread.daemon = True
        self.threads[url] = thread
        thread.start()
        self._save_downloads()
        return True, "Download started."

    def pause_download(self, url):
        with self.lock:
            if url in self.pause_events:
                self.pause_events[url].set() # Set event to cause wait()
                if self.downloads[url]['status'] == 'downloading':
                    self.downloads[url]['status'] = 'paused'
                    self._save_downloads()

    def resume_download(self, url):
        with self.lock:
            if url in self.pause_events:
                self.pause_events[url].clear() # Clear event to allow loop to continue
                if self.downloads[url]['status'] == 'paused':
                    self.downloads[url]['status'] = 'downloading'
                    self._save_downloads()

    def cancel_download(self, url):
        with self.lock:
            if url in self.downloads:
                self.downloads[url]['cancel_flag'] = True
                # If paused, unpause it so it can check the cancel flag and exit
                if url in self.pause_events:
                    self.pause_events[url].clear()

    def delete_download(self, url):
        with self.lock:
            self.cancel_download(url) # Ensure it's stopped first
            if url in self.downloads:
                filepath = os.path.join(self.downloads_dir, self.downloads[url]['filename'])
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except OSError as e:
                        print(f"Error deleting file {filepath}: {e}")
                del self.downloads[url]
                if url in self.threads:
                    del self.threads[url]
                if url in self.pause_events:
                    del self.pause_events[url]
                self._save_downloads()

    def _downloader(self, url):
        try:
            filepath = os.path.join(self.downloads_dir, self.downloads[url]['filename'])
            downloaded_size = 0
            headers = {}
            if os.path.exists(filepath):
                downloaded_size = os.path.getsize(filepath)
                headers['Range'] = f'bytes={downloaded_size}-'

            response = requests.get(url, headers=headers, stream=True, timeout=30)
            resuming = response.status_code == 206
            if not resuming:
                downloaded_size = 0

            total_size = int(response.headers.get('content-length', 0)) + downloaded_size
            
            with self.lock:
                self.downloads[url]['total_size'] = total_size
                self.downloads[url]['downloaded_size'] = downloaded_size

            mode = 'ab' if resuming else 'wb'
            with open(filepath, mode) as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.downloads[url].get('cancel_flag'):
                        break
                    
                    if url in self.pause_events and self.pause_events[url].is_set():
                        self.pause_events[url].wait()

                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        with self.lock:
                            self.downloads[url]['downloaded_size'] = downloaded_size
                            if total_size > 0:
                                self.downloads[url]['progress'] = (downloaded_size / total_size) * 100
            
            with self.lock:
                if self.downloads[url].get('cancel_flag'):
                    self.downloads[url]['status'] = 'stopped'
                    # Clean up the partial file
                    f.close()
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    # We don't save here, delete_download will handle it
                else:
                    self.downloads[url]['status'] = 'completed'
                    self.downloads[url]['progress'] = 100
                self._save_downloads()

        except Exception as e:
            with self.lock:
                self.downloads[url]['status'] = 'error'
                self.downloads[url]['error_message'] = str(e)
                self._save_downloads()
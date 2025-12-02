"""
多线程视频下载器
支持分段下载、断点续传、自动重试
"""
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Optional, Callable, List

import requests
import urllib3

from models.entities import DownloadTask
from utils.logger import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class VideoDownloader:
    """多线程视频下载器"""
    
    def __init__(
        self,
        url: str,
        save_path: str,
        headers: Optional[dict] = None,
        thread_count: int = 4,
        chunk_size: int = 1024 * 1024,
        progress_callback: Optional[Callable] = None
    ):
        self.url = url
        self.save_path = save_path
        self.headers = headers or {}
        self.thread_count = thread_count
        self.chunk_size = chunk_size
        self.progress_callback = progress_callback
        
        self.total_size = 0
        self.downloaded_size = 0
        self.lock = Lock()
        self.tasks: List[DownloadTask] = []
        
        if 'User-Agent' not in self.headers:
            self.headers['User-Agent'] = (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )
    
    def start(self) -> bool:
        try:
            if not self._get_file_info():
                return False
            
            support_range = self._check_range_support()
            
            if support_range and self.total_size > self.chunk_size:
                self._create_multipart_tasks()
            else:
                self._create_single_task()
            
            return self._execute_download()
            
        except Exception as e:
            logger.error(f"[错误] 下载失败: {e}")
            return False
    
    def _get_file_info(self) -> bool:
        try:
            response = requests.head(
                self.url, 
                headers=self.headers, 
                timeout=10,
                verify=False
            )
            self.total_size = int(response.headers.get('Content-Length', 0))
            
            if self.total_size <= 0:
                logger.warning("[警告] 无法获取文件大小，将使用单线程下载")
            
            return True
        except Exception as e:
            logger.error(f"[错误] 获取文件信息失败: {e}")
            return False
    
    def _check_range_support(self) -> bool:
        try:
            headers = self.headers.copy()
            headers['Range'] = 'bytes=0-0'
            response = requests.get(
                self.url, 
                headers=headers, 
                timeout=10, 
                stream=True,
                verify=False
            )
            response.close()
            return response.status_code == 206
        except:
            return False
    
    def _create_multipart_tasks(self) -> None:
        chunk_count = min(self.thread_count, self.total_size // self.chunk_size + 1)
        chunk_size = self.total_size // chunk_count
        
        for i in range(chunk_count):
            start = i * chunk_size
            end = start + chunk_size - 1 if i < chunk_count - 1 else self.total_size - 1
            self.tasks.append(DownloadTask(
                task_id=i,
                start=start,
                end=end
            ))
    
    def _create_single_task(self) -> None:
        self.tasks.append(DownloadTask(
            task_id=0,
            start=0,
            end=self.total_size - 1 if self.total_size > 0 else -1
        ))
    
    def _execute_download(self) -> bool:
        temp_file = self.save_path + '.tmp'
        
        try:
            if self.total_size > 0:
                with open(temp_file, 'wb') as f:
                    f.seek(self.total_size - 1)
                    f.write(b'\0')
            
            with ThreadPoolExecutor(max_workers=len(self.tasks)) as executor:
                futures = {
                    executor.submit(self._download_part, task, temp_file): task
                    for task in self.tasks
                }
                
                for future in as_completed(futures):
                    task = futures[future]
                    try:
                        success = future.result()
                        if not success:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                            return False
                    except Exception as e:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                        return False
            
            if os.path.exists(temp_file):
                os.rename(temp_file, self.save_path)
            return True
            
        except Exception as e:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False
    
    def _download_part(self, task: DownloadTask, temp_file: str) -> bool:
        task_id = task.task_id
        start = task.start
        end = task.end
        
        for retry in range(3):
            try:
                headers = self.headers.copy()
                if end > 0:
                    current_start = start + task.downloaded
                    if current_start > end:
                        return True
                    headers['Range'] = f'bytes={current_start}-{end}'
                
                response = requests.get(
                    self.url,
                    headers=headers,
                    stream=True,
                    timeout=60,
                    verify=False
                )
                
                if response.status_code not in [200, 206]:
                    if retry < 2:
                        continue
                    return False
                
                with open(temp_file, 'r+b') as f:
                    f.seek(start + task.downloaded)
                    
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            chunk_len = len(chunk)
                            
                            with self.lock:
                                self.downloaded_size += chunk_len
                                task.downloaded += chunk_len
                                
                                if self.progress_callback:
                                    self.progress_callback(
                                        self.downloaded_size,
                                        self.total_size
                                    )
                
                return True
                
            except Exception as e:
                if retry < 2:
                    import time
                    time.sleep(2)
                    continue
                return False
        
        return False


def format_size(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def generate_filename(description: str, url: str, suffix: str) -> str:
    if description:
        import re
        clean_desc = re.sub(r'[^\w\u4e00-\u9fff]', '', description)
        if len(clean_desc) > 30:
            clean_desc = clean_desc[:30]
        if clean_desc:
            return clean_desc + suffix
    
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return f"wechat_video_{url_hash}{suffix}"


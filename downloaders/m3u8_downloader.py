"""
m3u8 视频流下载器
支持下载和合并多段 TS 文件
"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

import requests
import urllib3

from utils.logger import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class M3U8Downloader:
    """m3u8 下载器"""
    
    def __init__(self, m3u8_url: str, save_path: str, headers: dict = None):
        self.m3u8_url = m3u8_url
        self.save_path = save_path
        self.headers = headers or {}
        self.ts_urls = []
        
        if 'User-Agent' not in self.headers:
            self.headers['User-Agent'] = (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )
    
    def download(self) -> bool:
        try:
            if not self._parse_m3u8():
                return False
            
            ts_dir = self.save_path + '_ts_temp'
            os.makedirs(ts_dir, exist_ok=True)
            
            if not self._download_ts_files(ts_dir):
                return False
            
            if not self._merge_ts_files(ts_dir):
                return False
            
            self._cleanup(ts_dir)
            
            logger.success(f"[完成] m3u8 视频已保存: {self.save_path}")
            return True
            
        except Exception as e:
            logger.error(f"[错误] m3u8 下载失败: {e}")
            return False
    
    def _parse_m3u8(self) -> bool:
        try:
            response = requests.get(
                self.m3u8_url,
                headers=self.headers,
                verify=False,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"[错误] 获取 m3u8 失败: {response.status_code}")
                return False
            
            content = response.text
            
            if '#EXT-X-STREAM-INF' in content:
                for line in content.split('\n'):
                    if line and not line.startswith('#'):
                        sub_m3u8_url = urljoin(self.m3u8_url, line.strip())
                        self.m3u8_url = sub_m3u8_url
                        return self._parse_m3u8()
            
            base_url = self.m3u8_url.rsplit('/', 1)[0] + '/'
            
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith('http'):
                        self.ts_urls.append(line)
                    else:
                        self.ts_urls.append(urljoin(base_url, line))
            
            logger.info(f"[信息] 找到 {len(self.ts_urls)} 个视频片段")
            return len(self.ts_urls) > 0
            
        except Exception as e:
            logger.error(f"[错误] 解析 m3u8 失败: {e}")
            return False
    
    def _download_ts_files(self, ts_dir: str) -> bool:
        logger.info(f"[下载] 开始下载 {len(self.ts_urls)} 个片段...")
        
        def download_one_ts(index: int, url: str) -> bool:
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    verify=False,
                    timeout=30
                )
                
                if response.status_code == 200:
                    ts_path = os.path.join(ts_dir, f'{index:05d}.ts')
                    with open(ts_path, 'wb') as f:
                        f.write(response.content)
                    return True
                else:
                    logger.error(f"[错误] 片段 {index} 下载失败: {response.status_code}")
                    return False
                    
            except Exception as e:
                logger.error(f"[错误] 片段 {index} 下载异常: {e}")
                return False
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(download_one_ts, i, url): i
                for i, url in enumerate(self.ts_urls)
            }
            
            success_count = 0
            for future in as_completed(futures):
                if future.result():
                    success_count += 1
                    if success_count % 10 == 0:
                        logger.info(f"[进度] {success_count}/{len(self.ts_urls)}")
        
        logger.info(f"[完成] 已下载 {success_count}/{len(self.ts_urls)} 个片段")
        return success_count == len(self.ts_urls)
    
    def _merge_ts_files(self, ts_dir: str) -> bool:
        try:
            logger.info("[合并] 正在合并视频片段...")
            
            with open(self.save_path, 'wb') as outfile:
                for i in range(len(self.ts_urls)):
                    ts_path = os.path.join(ts_dir, f'{i:05d}.ts')
                    if os.path.exists(ts_path):
                        with open(ts_path, 'rb') as infile:
                            outfile.write(infile.read())
            
            return True
            
        except Exception as e:
            logger.error(f"[错误] 合并失败: {e}")
            return False

    @staticmethod
    def _cleanup(ts_dir: str):
        try:
            import shutil
            if os.path.exists(ts_dir):
                shutil.rmtree(ts_dir)
                logger.info("[清理] 临时文件已清理")
        except Exception as e:
            logger.warning(f"[警告] 清理临时文件失败: {e}")


def is_m3u8_url(url: str) -> bool:
    return '.m3u8' in url.lower()


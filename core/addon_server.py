"""
mitmproxy 插件服务器
这个文件会被 mitmdump 加载
"""
import os
from pathlib import Path
from queue import Queue
from threading import Thread

from core.proxy_addon import WechatVideoAddon, extract_video_url
from crypto.decryptor import decrypt_wechat_video
from downloaders.m3u8_downloader import M3U8Downloader, is_m3u8_url
from downloaders.video_downloader import VideoDownloader, format_size, generate_filename
from models.entities import VideoData
from models.exceptions import DecryptError, DownloadError
from utils.config import config
from utils.logger import logger

download_queue = Queue()
downloaded_urls = set()


def create_progress_callback():
    """进度回调"""
    import time
    
    state = {
        'last_progress': 0,
        'last_time': time.time(),
        'last_percent': -1
    }
    
    def progress_callback(downloaded, total):
        if total > 0:
            percent = int(downloaded * 100 / total)
            percent_tier = percent // 10
            
            if percent_tier > state['last_percent']:
                current_time = time.time()
                elapsed = current_time - state['last_time']
                if elapsed > 0:
                    speed = (downloaded - state['last_progress']) / elapsed
                    speed_str = format_size(int(speed)) + "/s"
                    logger.info(f"{percent}% ({format_size(int(downloaded))}/{format_size(int(total))}) {speed_str}")
                else:
                    logger.info(f"{percent}% ({format_size(int(downloaded))}/{format_size(int(total))})")
                
                state['last_progress'] = downloaded
                state['last_time'] = current_time
                state['last_percent'] = percent_tier
    
    return progress_callback


def download_worker():
    """下载工作线程"""
    while True:
        item = download_queue.get()
        if item is None:
            break
        
        video_data: VideoData = item
        url = video_data.url
        
        filename = generate_filename(
            video_data.description,
            video_data.url,
            video_data.suffix
        )
        filepath = Path(os.path.join(config.download_dir, filename))
        
        counter = 1
        while filepath.exists():
            filepath = Path(os.path.join(config.download_dir, f"{filepath.stem}_{counter}{video_data.suffix}"))
            counter += 1
        
        logger.info(f"⬇️{filepath.name} 下载中...")
        
        progress_callback = create_progress_callback()

        if is_m3u8_url(url):
            downloader = M3U8Downloader(
                m3u8_url=url,
                save_path=str(filepath),
                headers={}
            )
            success = downloader.download()
        else:
            downloader = VideoDownloader(
                url=url,
                save_path=str(filepath),
                thread_count=4,
                progress_callback=progress_callback
            )
            success = downloader.start()
        
        try:
            if success:
                actual_file = filepath
                if hasattr(downloader, 'save_path'):
                    actual_file = Path(downloader.save_path)

                if video_data.is_encrypted:
                    logger.info(f"🔓{actual_file.name} 解密中...")
                    if decrypt_wechat_video(str(actual_file), video_data.decode_key):
                        logger.success(f"✅{actual_file.name} 下载完成")
                    else:
                        raise DecryptError(f"[Crawler-Retry] 解密失败: {actual_file.name}")
                else:
                    logger.success(f"✅{actual_file.name} 下载完成")
            else:
                if url in downloaded_urls:
                    downloaded_urls.discard(url)

                temp_file = str(filepath) + '.tmp'
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                raise DownloadError(f"[Crawler-Retry] {url}视频下载失败")
        except DecryptError or DownloadError as e:
            logger.error(e)
        except Exception as e:
            logger.error(str(e), exc_info=True)
        finally:
            download_queue.task_done()


def on_video_found(video_info: dict) -> None:
    """视频发现回调"""
    video_data = extract_video_url(video_info)
    if not video_data:
        return
    
    url = video_data.url
    if url in downloaded_urls:
        return

    desc = video_data.display_name
    size_info = f" ({format_size(video_data.size)})" if video_data.size else ""
    encrypt_info = " 🔐" if video_data.is_encrypted else ""

    logger.info(f"📥 {desc}{size_info}{encrypt_info}")
    downloaded_urls.add(url)
    download_queue.put(video_data)


addon_instance = WechatVideoAddon(
    video_callback=on_video_found,
    version="1.0.0"
)

download_thread = Thread(target=download_worker, daemon=True)
download_thread.start()


addons = [
    addon_instance
]

"""
数据实体类定义
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class VideoData:
    """视频数据实体"""
    url: str = field(default_factory=str)
    description: str = field(default="")
    size: int = field(default=0)
    suffix: str = field(default=".mp4")
    decode_key: str = field(default="")
    cover_url: str = field(default="")
    media_type: str = field(default="video")
    formats: List[str] = field(default_factory=list)
    
    @property
    def is_encrypted(self) -> bool:
        """是否加密"""
        return bool(self.decode_key)
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        return self.description[:40] if self.description else '无标题'


@dataclass
class DownloadTask:
    """下载任务实体"""
    task_id: int = field(default_factory=int)
    start: int = field(default_factory=int)
    end: int = field(default_factory=int)
    downloaded: int = field(default=0)
    
    @property
    def is_completed(self) -> bool:
        if self.end <= 0:
            return False
        return self.downloaded >= (self.end - self.start + 1)
    
    @property
    def progress(self) -> float:
        if self.end <= 0:
            return 0.0
        total = self.end - self.start + 1
        return self.downloaded / total if total > 0 else 0.0

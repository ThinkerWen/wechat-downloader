"""
统一配置管理模块
"""
import os


class Config:
    """配置管理器"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._init_config()
            self._initialized = True

    def _init_config(self):
        """初始化配置"""
        self.is_test = bool(os.getenv("DEBUG"))

    @property
    def env_suffix(self) -> str:
        """环境后缀"""
        return "dev" if self.is_test else "prod"

    @property
    def log_dir(self) -> str:
        """日志目录"""
        config_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(os.path.dirname(config_dir), "logs")

    @property
    def download_dir(self) -> str:
        """下载目录（微信视频默认保存位置）"""
        download_dir = os.path.join(self.log_dir, "downloads")
        os.makedirs(download_dir, exist_ok=True)
        return download_dir
    
    @property
    def proxy_port(self) -> int:
        """默认代理端口"""
        return 8899


config = Config()

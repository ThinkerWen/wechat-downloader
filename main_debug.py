"""
直接在主进程中运行 mitmproxy，支持 PyCharm 断点调试
"""
import atexit
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from models.exceptions import NetworkError

sys.path.insert(0, str(Path(__file__).parent))

from utils.config import config
from utils.logger import logger
from core.proxy_manager import ProxyManager, check_certificate

proxy_manager: Optional[ProxyManager] = None


def cleanup_proxy():
    """清理代理"""
    if proxy_manager:
        proxy_manager.cleanup()


async def start_proxy(save_dir: Path, port: int):
    """启动代理服务器（异步）"""
    from mitmproxy.options import Options
    from mitmproxy.tools.dump import DumpMaster
    
    os.environ['SAVE_DIR'] = str(save_dir)
    os.environ['PORT'] = str(port)
    
    opts = Options(
        listen_host='127.0.0.1',
        listen_port=port,
    )
    
    opts.add_option("block_global", bool, False, "")
    opts.add_option("stream_large_bodies", str, "5m", "")
    opts.add_option("ssl_insecure", bool, True, "")
    
    master = DumpMaster(opts)
    addon_script = Path(__file__).parent / 'core' / 'addon_server.py'
    
    import importlib.util
    spec = importlib.util.spec_from_file_location("addon_server", addon_script)
    addon_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(addon_module)
    
    if hasattr(addon_module, 'addons'):
        for addon in addon_module.addons:
            master.addons.add(addon)
    
    try:
        await master.run()
    except KeyboardInterrupt:
        master.shutdown()


def main():
    """主函数"""
    global proxy_manager

    save_dir = Path(config.download_dir).absolute()
    save_dir.mkdir(exist_ok=True)
    port = config.proxy_port
    
    logger.info(f"[DEBUG] 启动 | 端口:{port} | 保存:{save_dir}")

    env = os.environ.copy()
    env['SAVE_DIR'] = str(save_dir)
    env['PORT'] = str(port)

    process = None
    addon_script = Path(__file__).parent / 'core' / 'addon_server.py'

    cmd = [
        'mitmdump',
        '-s', str(addon_script),
        '-p', str(port),
        '--set', 'block_global=false',
        '--set', 'stream_large_bodies=5m',
        '--ssl-insecure',
        '--quiet'
    ]

    try:
        logger.info("🚀启动代理服务器...")
        process = subprocess.Popen(cmd, env=env)
        time.sleep(1)

        proxy_manager = ProxyManager("127.0.0.1", port)
        if proxy_manager.setup():
            atexit.register(cleanup_proxy)
        else:
            logger.warning("⚠️自动设置代理失败，请手动设置")
            logger.warning(f"代理地址: 127.0.0.1:{port}")
            proxy_manager = None

        if not check_certificate():
            raise NetworkError("⚠️无法连接到代理，可能需要安装证书")

        process.wait()

    except KeyboardInterrupt:
        logger.info("⏸️️正在停止...")
        if process:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        logger.success("✅已停止")

    except FileNotFoundError:
        logger.error("❌找不到 mitmdump 命令")
        sys.exit(1)

    except Exception as e:
        logger.error(f"❌错误: {e}")
        sys.exit(1)

    finally:
        cleanup_proxy()


if __name__ == '__main__':
    main()

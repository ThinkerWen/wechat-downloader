"""
微信视频解密模块
对加密的视频号视频进行解密
Reference from: https://github.com/Hanson/WechatSphDecrypt/blob/main/decrypt.go
"""
import struct
from pathlib import Path
from typing import Optional

from utils.logger import logger

MASK64 = 0xFFFFFFFFFFFFFFFF


def mix(a, b, c, d, e, f, g, h):
    a = (a - e) & MASK64
    f ^= (h >> 9) & MASK64
    h = (h + a) & MASK64

    b = (b - f) & MASK64
    g ^= (a << 9) & MASK64
    a = (a + b) & MASK64

    c = (c - g) & MASK64
    h ^= (b >> 23) & MASK64
    b = (b + c) & MASK64

    d = (d - h) & MASK64
    a ^= (c << 15) & MASK64
    c = (c + d) & MASK64

    e = (e - a) & MASK64
    b ^= (d >> 14) & MASK64
    d = (d + e) & MASK64

    f = (f - b) & MASK64
    c ^= (e << 20) & MASK64
    e = (e + f) & MASK64

    g = (g - c) & MASK64
    d ^= (f >> 17) & MASK64
    f = (f + g) & MASK64

    h = (h - d) & MASK64
    e ^= (g << 14) & MASK64
    g = (g + h) & MASK64

    return a, b, c, d, e, f, g, h


class RandCtx64:
    def __init__(self, enc_key):
        self.RandCnt = 255
        self.Seed = [0] * 256
        self.MM = [0] * 256
        self.AA = 0
        self.BB = 0
        self.CC = 0

        self.rand64_init(enc_key)

    def is_aac_random(self):
        r = self.Seed[self.RandCnt]
        if self.RandCnt == 0:
            self.is_aac64()
            self.RandCnt = 255
        else:
            self.RandCnt -= 1
        return r

    def _process_pass(self, a, b, c, d, e, f, g, h, source_array):
        """处理单个pass的通用方法"""
        for i in range(0, 256, 8):
            values = [a, b, c, d, e, f, g, h]
            values = [(v + source_array[i+j]) & MASK64 for j, v in enumerate(values)]
            a, b, c, d, e, f, g, h = mix(*values)
            
            for j, val in enumerate([a, b, c, d, e, f, g, h]):
                self.MM[i+j] = val
        
        return a, b, c, d, e, f, g, h

    def rand64_init(self, enc_key):
        golden = 0x9e3779b97f4a7c13
        a = b = c = d = e = f = g = h = golden

        self.Seed[0] = enc_key & MASK64
        self.Seed[1:] = [0] * 255

        for _ in range(4):
            a, b, c, d, e, f, g, h = mix(a, b, c, d, e, f, g, h)

        a, b, c, d, e, f, g, h = self._process_pass(a, b, c, d, e, f, g, h, self.Seed)
        a, b, c, d, e, f, g, h = self._process_pass(a, b, c, d, e, f, g, h, self.MM)
        
        self.is_aac64()

    def is_aac64(self):
        self.CC = (self.CC + 1) & MASK64
        self.BB = (self.BB + self.CC) & MASK64

        for i in range(256):
            if i % 4 == 0:
                self.AA = (~(self.AA ^ (self.AA << 21))) & MASK64
            elif i % 4 == 1:
                self.AA ^= (self.AA >> 5) & MASK64
            elif i % 4 == 2:
                self.AA ^= (self.AA << 12) & MASK64
            else:
                self.AA ^= (self.AA >> 33) & MASK64

            self.AA = (self.AA + self.MM[(i + 128) % 256]) & MASK64

            x = self.MM[i]
            y = (self.MM[(x >> 3) % 256] + self.AA + self.BB) & MASK64
            self.MM[i] = y
            self.BB = (self.MM[(y >> 11) % 256] + x) & MASK64
            self.Seed[i] = self.BB


def decrypt(data: bytearray, enc_len: int, key: int) -> bool:
    if len(data) == 0 or len(data) < enc_len:
        return False

    try:
        ctx = RandCtx64(key)
        for i in range(0, enc_len, 8):
            rand_number = ctx.is_aac_random()
            temp = struct.pack(">Q", rand_number)

            for j in range(8):
                idx = i + j
                if idx >= enc_len:
                    return True
                data[idx] ^= temp[j]
        return True
    except Exception as e:
        logger.error(f"解密失败: {e}")
        return False


def _read_and_decrypt(file_path: str, decode_key: str) -> Optional[bytearray]:
    """读取文件并解密"""
    try:
        if not decode_key:
            return None
        
        with open(file_path, "rb") as f:
            data = bytearray(f.read())
        
        if decrypt(data, 131072, int(decode_key)):
            return data
        return None
    except Exception as e:
        logger.error(f"解密异常: {e}")
        return None


def decrypt_wechat_video(video_path: str, decode_key: str) -> bool:
    decrypted_data = _read_and_decrypt(video_path, decode_key)
    if decrypted_data:
        with open(video_path, "wb") as f:
            f.write(decrypted_data)
        return True
    return False


def create_decrypted_copy(video_path: str, decode_key: str, output_path: str = None) -> Optional[str]:
    """
    创建解密后的视频副本

    Args:
        video_path: 原视频文件路径
        decode_key: 解密密钥
        output_path: 输出路径（可选，默认在原文件名后加 _decrypted）

    Returns:
        解密后的文件路径，失败返回 None
    """
    try:
        if not output_path:
            path = Path(video_path)
            output_path = str(path.parent / f"{path.stem}_decrypted{path.suffix}")
        
        decrypted_data = _read_and_decrypt(video_path, decode_key)
        if decrypted_data:
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            return output_path
        
        return None
            
    except Exception as e:
        logger.error(f"创建解密副本失败: {e}")
        return None

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 2:
        decrypt_wechat_video(sys.argv[1], sys.argv[2])

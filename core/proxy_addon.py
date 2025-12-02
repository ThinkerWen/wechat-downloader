"""
微信视频号代理拦截插件
基于 mitmproxy 实现流量拦截和 JS 注入
"""
import json
import re
from typing import Optional

from mitmproxy import http

from models.entities import VideoData
from utils.logger import logger


class WechatVideoAddon:
    """微信视频号拦截插件"""
    
    def __init__(self, video_callback=None, version="1.0.0"):
        """
        初始化插件
        
        Args:
            video_callback: 视频信息回调函数
            version: 版本号，防止缓存
        """
        self.video_callback = video_callback
        self.version = version
        self.source_url = ""
        
        self.media_regex = re.compile(r'get\s+media\(\)\{', re.MULTILINE)
        
        self.comment_regex = re.compile(
            r'async\s+finderGetCommentDetail\((\w+)\)\s*\{return(.*?)\s*}\s*async',
            re.MULTILINE | re.DOTALL
        )

        logger.success("✅微信视频号插件初始化完成")
    
    def request(self, flow: http.HTTPFlow) -> None:
        request = flow.request

        if (request.host.endswith('qq.com') and 
            '/res-downloader/wechat' in request.path):
            
            try:
                body = request.content.decode('utf-8')
                video_info = json.loads(body)
                
                if self.video_callback:
                    self.video_callback(video_info, self.source_url)
                    if self.source_url:
                        self.source_url = ""
                
                flow.response = http.Response.make(
                    200,
                    b"OK",
                    {"Content-Type": "text/plain"}
                )
            except Exception as e:
                logger.error(f"[视频号错误] 解析视频信息失败: {e}")
                flow.response = http.Response.make(500, b"Error")
    
    def response(self, flow: http.HTTPFlow) -> None:
        response = flow.response
        request = flow.request
        
        if not response or response.status_code not in [200, 206]:
            return

        if (request.host.endswith('qq.com') and
            '/res-downloader/wechat' in request.path):
            logger.debug("检测到视频号上报请求")
        
        host = request.host
        path = request.path
        
        is_wechat_channels = host.endswith('channels.weixin.qq.com')
        is_wechat_res = host.endswith('res.wx.qq.com')
        
        if not (is_wechat_channels or is_wechat_res):
            return
        
        if is_wechat_channels and ('/web/pages/feed' in path or '/web/pages/home' in path):
            self._add_version_to_js(flow)
        
        if is_wechat_res:
            if path.endswith(f'.js?v={self.version}'):
                self._add_version_to_js(flow)
            
            if 'web-finder/res/js/virtual_svg-icons-register.publish' in path:
                self._inject_video_sniffer(flow)
    
    def _add_version_to_js(self, flow: http.HTTPFlow) -> None:
        try:
            content = flow.response.content.decode('utf-8', errors='ignore')
            new_content = content.replace('.js"', f'.js?v={self.version}"')
            
            if new_content != content:
                flow.response.content = new_content.encode('utf-8')
                flow.response.headers['Content-Length'] = str(len(flow.response.content))
        except Exception as e:
            logger.warning(e)
    
    def _inject_video_sniffer(self, flow: http.HTTPFlow) -> None:
        try:
            content = flow.response.content.decode('utf-8', errors='ignore')
            
            inject_media_code = '''
get media(){
    if(this.objectDesc){
        fetch("https://wxapp.tc.qq.com/res-downloader/wechat?type=1", {
          method: "POST",
          mode: "no-cors",
          body: JSON.stringify(this.objectDesc),
        });
    };
'''
            content = self.media_regex.sub(inject_media_code, content)
            
            inject_comment_code = r'''
async finderGetCommentDetail(\1) {
    var res = await\2;
    if (res?.data?.object?.objectDesc) {
        fetch("https://wxapp.tc.qq.com/res-downloader/wechat?type=2", {
          method: "POST",
          mode: "no-cors",
          body: JSON.stringify(res.data.object.objectDesc),
        });
    }
    return res;
}async
'''
            content = self.comment_regex.sub(inject_comment_code, content)
            
            flow.response.content = content.encode('utf-8')
            flow.response.headers['Content-Length'] = str(len(flow.response.content))
            
            logger.success("✅[视频号] JS 注入成功，嗅探已激活")
            
        except Exception as e:
            logger.error(f"❌[视频号] JS 注入失败: {e}")


def extract_video_url(video_info: dict) -> Optional[VideoData]:
    try:
        media_list = video_info.get('media', [])
        if not media_list:
            return None
        
        first_media = media_list[0]
        url = first_media.get('url', '')
        if not url:
            return None
        
        url_token = first_media.get('urlToken', '')
        if url_token:
            url += url_token
        
        media_type = first_media.get('mediaType', 0)
        is_image = media_type == 9
        
        decode_key = first_media.get('decodeKey', '')
        if decode_key and not isinstance(decode_key, str):
            decode_key = str(decode_key)
        
        spec = first_media.get('spec', [])
        formats = [s.get('fileFormat', '') for s in spec if 'fileFormat' in s] if spec else []
        
        return VideoData(
            url=url,
            description=video_info.get('description', ''),
            size=first_media.get('fileSize', 0),
            suffix='.png' if is_image else '.mp4',
            decode_key=decode_key,
            cover_url=first_media.get('coverUrl', ''),
            media_type='image' if is_image else 'video',
            formats=formats,
        )
        
    except Exception as e:
        logger.error(f"提取视频信息失败: {e}")
        return None


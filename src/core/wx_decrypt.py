import os
from pymem import Pymem, pattern, process
from win32api import HIWORD, LOWORD, GetFileVersionInfo
import binascii
import struct

class WeChatDecrypt:
    """微信数据库解密工具"""
    
    def __init__(self):
        try:
            self.pm = Pymem("WeChat.exe")
        except Exception as e:
            raise RuntimeError("请确认微信程序已经打开并登录！")
    
    def _get_dll_arch(self, dll_file):
        """获取DLL架构类型"""
        with open(dll_file, "rb") as f:
            doshdr = f.read(64)
            magic, padding, offset = struct.unpack("2s58si", doshdr)
            
            if magic != b"MZ":
                return None
            f.seek(offset, os.SEEK_SET)
            pehdr = f.read(6)
            
            magic, padding, machine = struct.unpack("2s2sH", pehdr)
            
            if magic != b"PE":
                return None
            if machine == 0x014c:
                return "i386"
            if machine == 0x0200:
                return "IA64"
            if machine == 0x8664:
                return "x64"
            
            return "unknown"
    
    def _is_64bit(self):
        """判断是否是64位程序"""
        exe_arch = self._get_dll_arch(list(self.pm.list_modules())[0].filename)
        return exe_arch == "x64"
    
    def _get_version_base(self):
        """获取微信版本和基址"""
        WeChatWindll_base = 0
        WeChatWindll_path = ""
        for m in list(self.pm.list_modules()):
            path = m.filename
            if path.endswith("WeChatWin.dll"):
                WeChatWindll_base = m.lpBaseOfDll
                WeChatWindll_path = path
                break
        
        if not WeChatWindll_path:
            raise RuntimeError("获取版本失败，请确认本系统是否成功安装了微信！")
        
        version = GetFileVersionInfo(WeChatWindll_path, "\\")
        msv = version['FileVersionMS']
        lsv = version['FileVersionLS']
        version = f"{str(HIWORD(msv))}.{str(LOWORD(msv))}.{str(HIWORD(lsv))}.{str(LOWORD(lsv))}"
        
        return version, WeChatWindll_base
    
    def _get_offset_by_wxid(self, wxid):
        """通过微信号获取密钥偏移"""
        bytes_pattern = bytearray()
        bytes_pattern.extend(map(ord, wxid))
        id_pattern = bytes(bytes_pattern)
        wechatwindll_module = process.module_from_name(self.pm.process_handle, "WeChatWin.dll")
        wechat_id_addrs = pattern.pattern_scan_module(
            self.pm.process_handle, wechatwindll_module, id_pattern, return_multiple=True)
        
        if wechat_id_addrs == None or len(wechat_id_addrs) != 2:
            raise RuntimeError(f"未能找到微信账号: {wxid}")
        
        return wechat_id_addrs[1] - (64 if self._is_64bit() else 36)
    
    def _get_aes_key(self, base, offset):
        """获取AES密钥"""
        try:
            if self._is_64bit():
                result = self.pm.read_bytes(base + offset, 8)
                addr = struct.unpack("<Q", result)[0]
            else:
                result = self.pm.read_bytes(base + offset, 4)
                addr = struct.unpack("<I", result)[0]
            
            aes_key = self.pm.read_bytes(addr, 0x20)
            result = binascii.b2a_hex(aes_key)
            return result.decode()
            
        except Exception as e:
            raise RuntimeError("获取密钥失败，请确认微信已经登录！")
    
    def get_key(self, wxid: str) -> tuple:
        """获取指定微信号的密钥"""
        version, base = self._get_version_base()
        offset = self._get_offset_by_wxid(wxid) - base
        key = self._get_aes_key(base, offset)
        
        version_str = f"{version} " + ("(64bit)" if self._is_64bit() else "(32bit)")
        return version_str, key 
import requests
import time
import json
import os
from typing import List, Dict, Optional


class RadioAPI:
    def __init__(self):
        self.base_url = "https://de1.api.radio-browser.info/json/stations"
        # 添加用户代理，避免被API拒绝
        self.headers = {
            "User-Agent": "GlobalRadioPlayer/1.0"
        }
        # 添加请求间隔，避免触发API限制
        self.last_request_time = 0
        self.request_interval = 1  # 1秒间隔
        self.cache_file = "radio_cache.json"
        self.cache_duration = 3600  # 1小时缓存

    def _wait_for_rate_limit(self):
        """确保请求间隔，避免触发API限制"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self.last_request_time = time.time()

    def _load_cache(self) -> Optional[List[Dict]]:
        """从缓存加载数据"""
        try:
            if os.path.exists(self.cache_file):
                # 检查缓存是否过期
                file_time = os.path.getmtime(self.cache_file)
                if time.time() - file_time < self.cache_duration:
                    with open(self.cache_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
        except Exception:
            pass
        return None

    def _save_cache(self, data: List[Dict]):
        """保存数据到缓存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _fetch(self, params: Dict) -> List[Dict]:
        """内部方法：发送请求并返回数据，增加错误处理"""
        # 首先尝试从缓存加载
        cached_data = self._load_cache()
        if cached_data is not None:
            return cached_data

        try:
            # 遵守请求间隔
            self._wait_for_rate_limit()

            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=15
            )

            # 检查HTTP状态码
            response.raise_for_status()

            # 解析JSON
            data = response.json()

            # 检查返回数据是否有效
            if not isinstance(data, list):
                raise ValueError("API返回的数据格式不正确")

            # 缓存数据
            self._save_cache(data)
            return data

        except requests.exceptions.RequestException as e:
            print(f"API请求错误: {str(e)}")
            return []
        except ValueError as e:
            print(f"数据解析错误: {str(e)}")
            return []
        except Exception as e:
            print(f"未知错误: {str(e)}")
            return []

    def get_popular_radios(self, limit: int = 200) -> List[Dict]:
        """获取热门电台"""
        params = {
            "limit": limit,
            "order": "clickcount",
            "reverse": "true"  # 降序排列（最热门的在前）
        }
        return self._fetch(params)

    def search_radios(self, query: str, limit: int = 100) -> List[Dict]:
        """搜索电台"""
        params = {
            "limit": limit,
            "name": query
        }
        return self._fetch(params)

    def get_radios_by_country(self, country: str, limit: int = 100) -> List[Dict]:
        """按国家获取电台"""
        params = {
            "limit": limit,
            "country": country
        }
        return self._fetch(params)

    def get_radios_by_language(self, language: str, limit: int = 100) -> List[Dict]:
        """按语言获取电台"""
        params = {
            "limit": limit,
            "language": language
        }
        return self._fetch(params)

    def get_radios_by_tag(self, tag: str, limit: int = 100) -> List[Dict]:
        """按标签获取电台"""
        params = {
            "limit": limit,
            "tag": tag
        }
        return self._fetch(params)

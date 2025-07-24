try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    VLC_AVAILABLE = False
    print("警告: 未安装 VLC 模块，播放功能将不可用")
    print("请运行 'pip install python-vlc' 安装")

import json
import os
from typing import Callable, Optional


class RadioPlayer:
    def __init__(self):
        if not VLC_AVAILABLE:
            self.instance = None
            self.player = None
            self.volume = 70
            self.current_url = None
            self.state_callbacks = []
            self.load_config()
            return

        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.volume = 70  # 默认音量
        self.current_url = None
        self.state_callbacks = []
        self.load_config()  # 加载保存的音量设置
        # 应用保存的音量
        self.player.audio_set_volume(self.volume)

        # 设置事件管理器
        self.event_manager = self.player.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_playing)
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPaused, self._on_paused)
        self.event_manager.event_attach(vlc.EventType.MediaPlayerStopped, self._on_stopped)

    def add_state_callback(self, callback: Callable[[str], None]):
        """添加状态变化回调"""
        if not VLC_AVAILABLE:
            return
        self.state_callbacks.append(callback)

    def remove_state_callback(self, callback: Callable[[str], None]):
        """移除状态变化回调"""
        if not VLC_AVAILABLE:
            return
        if callback in self.state_callbacks:
            self.state_callbacks.remove(callback)

    def _notify_state_change(self, state: str):
        """通知状态变化"""
        for callback in self.state_callbacks:
            try:
                callback(state)
            except Exception:
                pass

    def _on_playing(self, event):
        """播放事件处理"""
        self._notify_state_change("playing")

    def _on_paused(self, event):
        """暂停事件处理"""
        self._notify_state_change("paused")

    def _on_stopped(self, event):
        """停止事件处理"""
        self._notify_state_change("stopped")

    def _on_end_reached(self, event):
        """播放结束事件处理"""
        self._notify_state_change("ended")

    def set_volume(self, value):
        """设置音量（0 - 100）"""
        if not VLC_AVAILABLE:
            self.volume = int(float(value))
            self.volume = max(0, min(100, self.volume))
            self.save_config()
            return

        try:
            # 处理可能的字符串输入和浮点值
            self.volume = int(float(value))
            # 确保音量在有效范围内
            self.volume = max(0, min(100, self.volume))
            self.player.audio_set_volume(self.volume)
            self.save_config()  # 保存音量到本地
        except Exception as e:
            print(f"设置音量失败: {e}")

    def load_config(self):
        """从本地加载配置（音量）"""
        try:
            if os.path.exists("player_config.json"):
                with open("player_config.json", "r") as f:
                    config = json.load(f)
                    self.volume = config.get("volume", 70)
        except Exception as e:
            print(f"加载配置失败: {e}")
            self.volume = 70

    def save_config(self):
        """保存配置到本地"""
        try:
            with open("player_config.json", "w") as f:
                json.dump({"volume": self.volume}, f)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def play_stream(self, stream_url: str) -> int:
        """播放流媒体url"""
        if not VLC_AVAILABLE:
            print("VLC 不可用，无法播放")
            return -1

        try:
            if self.current_url == stream_url and self.player.get_state() in [vlc.State.Playing, vlc.State.Paused]:
                # 如果是同一个URL且正在播放或暂停，则恢复播放
                if self.player.get_state() == vlc.State.Paused:
                    self.player.play()
                return 0

            self.current_url = stream_url
            media = self.instance.media_new(stream_url)
            self.player.set_media(media)
            result = self.player.play()
            self._notify_state_change("playing")
            return result
        except Exception as e:
            print(f"播放失败: {e}")
            self._notify_state_change("error")
            return -1

    def is_playing(self) -> bool:
        """判断是否正在播放"""
        if not VLC_AVAILABLE or not self.player:
            return False
        return self.player.get_state() == vlc.State.Playing

    def is_paused(self) -> bool:
        """判断是否已暂停"""
        if not VLC_AVAILABLE or not self.player:
            return False
        return self.player.get_state() == vlc.State.Paused

    def is_stopped(self) -> bool:
        """判断是否已停止"""
        if not VLC_AVAILABLE or not self.player:
            return True
        return self.player.get_state() == vlc.State.Stopped

    def get_state(self) -> str:
        """获取播放器状态"""
        if not VLC_AVAILABLE or not self.player:
            return "unknown"

        state = self.player.get_state()
        if state == vlc.State.Playing:
            return "playing"
        elif state == vlc.State.Paused:
            return "paused"
        elif state == vlc.State.Stopped:
            return "stopped"
        elif state == vlc.State.Ended:
            return "ended"
        else:
            return "unknown"

    def pause(self):
        """暂停播放"""
        if not VLC_AVAILABLE or not self.player:
            return
        if self.player.get_state() == vlc.State.Playing:
            self.player.pause()
            self._notify_state_change("paused")

    def resume(self):
        """继续播放"""
        if not VLC_AVAILABLE or not self.player:
            return
        if self.player.get_state() == vlc.State.Paused:
            self.player.play()
            self._notify_state_change("playing")

    def stop(self):
        """停止播放"""
        if not VLC_AVAILABLE or not self.player:
            return
        self.player.stop()
        self._notify_state_change("stopped")
        self.current_url = None

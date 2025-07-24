import tkinter as tk
from tkinter import ttk, messagebox
import os
import threading
import json
import sys
from typing import List, Dict
from player import RadioPlayer
import logging


class GlobalRadioApp:
    # 常量定义
    DEFAULT_GEOMETRY = "1100x700"
    MIN_GEOMETRY = "900x600"
    COLUMN_CONFIG = {
        "favorite": {"width": 60, "anchor": "center"},
        "name": {"width": 250, "anchor": "w"},
        "country": {"width": 120, "anchor": "center"},
        "genre": {"width": 180, "anchor": "w"},
        "language": {"width": 120, "anchor": "center"},
        "bitrate": {"width": 80, "anchor": "center"}
    }

    def __init__(self, root):
        # 设置日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # 首先强制设置Tcl/Tk路径（关键修复）
        self.setup_tcl_paths()

        self.root = root
        self.root.title("全球广播播放器")
        self.root.geometry(self.DEFAULT_GEOMETRY)
        self.root.minsize(900, 600)

        # 状态变量
        self.status_var = tk.StringVar(value="就绪 - 正在加载电台列表...")
        self.current_playing_index = -1  # 当前播放的电台索引
        self.current_view = "all"  # 当前视图："all"或"favorites"
        self.search_var = tk.StringVar()

        # 存储数据
        self.all_radios: List[Dict] = []  # 所有电台
        self.filtered_radios: List[Dict] = []  # 当前显示的电台
        self.favorite_radios: List[Dict] = []  # 收藏的电台
        self.favorite_ids = set()  # 收藏的电台ID集合，用于快速判断

        # 初始化播放器
        self.player = RadioPlayer()
        self.player.add_state_callback(self.on_player_state_change)

        # 加载收藏的电台
        self.load_favorites()

        # 检查VLC是否可用
        if not self.check_vlc_available():
            messagebox.showerror("错误", "未检测到VLC播放器，请先安装VLC\n下载地址：https://www.videolan.org/vlc/")
            self.root.destroy()
            return

        # 创建UI
        self.create_widgets()

        # 启动时加载电台
        self.refresh_radios()

    def setup_tcl_paths(self):
        """强制设置Tcl/Tk库路径，解决初始化错误"""
        # 使用更灵活的路径查找方式
        python_paths = [
            os.path.dirname(os.path.dirname(sys.executable)),  # 当前Python路径
            sys.prefix,  # Python安装目录
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 脚本所在目录
        ]

        # 添加环境变量中的路径
        if 'PYTHONHOME' in os.environ:
            python_paths.append(os.environ['PYTHONHOME'])

        tcl_lib_path = None
        tk_lib_path = None

        for python_path in python_paths:
            # 尝试不同版本的Tcl/Tk
            for version in ['8.6', '8.5']:
                tcl_candidate = os.path.join(python_path, "tcl", f"tcl{version}")
                tk_candidate = os.path.join(python_path, "tcl", f"tk{version}")

                if os.path.exists(os.path.join(tcl_candidate, "init.tcl")):
                    tcl_lib_path = tcl_candidate

                if os.path.exists(os.path.join(tk_candidate, "tk.tcl")):
                    tk_lib_path = tk_candidate

                if tcl_lib_path and tk_lib_path:
                    break

            if tcl_lib_path and tk_lib_path:
                break

        # 如果找到有效路径，设置环境变量
        if tcl_lib_path and tk_lib_path:
            os.environ["TCL_LIBRARY"] = tcl_lib_path
            os.environ["TK_LIBRARY"] = tk_lib_path
            os.environ["TCLHOME"] = os.path.dirname(tcl_lib_path)
            return True
        else:
            return False

    def check_vlc_available(self):
        """检查VLC是否正确安装"""
        try:
            import vlc
            vlc.Instance()
            return True
        except Exception as e:
            self.logger.error(f"VLC检查失败: {e}")
            return False

    def create_widgets(self):
        # 主容器
        main_container = tk.Frame(self.root, padx=10, pady=10)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 顶部控制区
        top_frame = ttk.Frame(main_container)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # 控制按钮框架
        controls_frame = ttk.Frame(top_frame)
        controls_frame.pack(side=tk.LEFT)

        # 刷新按钮
        self.refresh_btn = ttk.Button(
            controls_frame,
            text="刷新电台列表",
            command=self.refresh_radios
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 视图切换按钮
        self.view_all_btn = ttk.Button(
            controls_frame,
            text="查看所有电台",
            command=lambda: self.switch_view("all")
        )
        self.view_all_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.view_all_btn.config(state=tk.DISABLED)  # 默认显示所有电台

        self.view_fav_btn = ttk.Button(
            controls_frame,
            text="查看收藏电台",
            command=lambda: self.switch_view("favorites")
        )
        self.view_fav_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 收藏/取消收藏按钮
        self.favorite_btn = ttk.Button(
            controls_frame,
            text="收藏选中电台",
            command=self.toggle_favorite
        )
        self.favorite_btn.pack(side=tk.LEFT)

        # 搜索框架
        search_frame = ttk.Frame(top_frame)
        search_frame.pack(side=tk.RIGHT)

        # 搜索框
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(10, 5))
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT)
        self.search_var.trace('w', self.on_search_change)

        # 电台数量统计
        self.count_label = ttk.Label(top_frame, text="电台数量：0")
        self.count_label.pack(side=tk.RIGHT, padx=(10, 0))

        # 中间：电台列表区域
        list_frame = ttk.LabelFrame(main_container, text="电台列表（双击播放）")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 创建水平滚动条
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # 创建垂直滚动条
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 电台表格
        columns = ("favorite", "name", "country", "genre", "language", "bitrate")
        self.radio_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            height=18,
            xscrollcommand=h_scrollbar.set,
            yscrollcommand=v_scrollbar.set
        )

        # 设置列标题和宽度
        self.radio_tree.heading("favorite", text="收藏")
        self.radio_tree.heading("name", text="电台名称")
        self.radio_tree.heading("country", text="国家/地区")
        self.radio_tree.heading("genre", text="节目类型")
        self.radio_tree.heading("language", text="语言")
        self.radio_tree.heading("bitrate", text="比特率(kbps)")

        # 应用列配置
        for col, config in self.COLUMN_CONFIG.items():
            self.radio_tree.column(col, width=config["width"], anchor=config["anchor"])

        # 关联滚动条
        h_scrollbar.config(command=self.radio_tree.xview)
        v_scrollbar.config(command=self.radio_tree.yview)

        # 放置表格
        self.radio_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 绑定双击事件
        self.radio_tree.bind("<Double-1>", self.play_on_double_click)
        # 绑定选择事件
        self.radio_tree.bind("<<TreeviewSelect>>", self.on_selection_change)

        # 底部播放控制区
        control_frame = ttk.LabelFrame(main_container, text="播放控制")
        control_frame.pack(fill=tk.X, pady=(0, 5))

        # 按钮框架
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.pack(side=tk.LEFT, padx=10, pady=10)

        # 播放按钮
        self.play_btn = ttk.Button(
            buttons_frame,
            text="播放选中电台",
            command=self.play_selected,
            width=15
        )
        self.play_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 暂停/继续按钮
        self.pause_btn = ttk.Button(
            buttons_frame,
            text="暂停",
            command=self.toggle_play_pause,
            width=10
        )
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 停止按钮
        self.stop_btn = ttk.Button(
            buttons_frame,
            text="停止",
            command=self.stop_playback,
            width=10
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 20))

        # 音量控制
        volume_frame = ttk.Frame(control_frame)
        volume_frame.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(volume_frame, text="音量：").pack(side=tk.LEFT, padx=(0, 5))
        self.volume_scale = ttk.Scale(
            volume_frame,
            from_=0, to=100,
            command=self.on_volume_change,
            length=200
        )
        self.volume_scale.set(self.player.volume)
        self.volume_scale.pack(side=tk.LEFT, padx=(0, 20))

        # 状态显示
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(status_frame, text="状态：").pack(side=tk.LEFT, padx=(0, 5))
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT, padx=5)

    def on_volume_change(self, value):
        """音量变化回调"""
        self.player.set_volume(value)

    def on_selection_change(self, event):
        """选择变化回调"""
        selected = self.radio_tree.selection()
        if selected:
            index = self.radio_tree.index(selected[0])
            if 0 <= index < len(self.filtered_radios):
                radio = self.filtered_radios[index]
                station_id = radio.get('stationuuid')
                if station_id in self.favorite_ids:
                    self.favorite_btn.config(text="取消收藏")
                else:
                    self.favorite_btn.config(text="收藏选中电台")

    def on_player_state_change(self, state):
        """播放器状态变化回调"""
        if state == "playing":
            self.pause_btn.config(text="暂停")
        elif state == "paused":
            self.pause_btn.config(text="继续")
        elif state == "stopped":
            self.pause_btn.config(text="暂停")
        elif state == "ended":
            self.status_var.set("播放结束")
            self.current_playing_index = -1
        elif state == "error":
            self.status_var.set("播放出错")

    def on_search_change(self, *args):
        """搜索框内容变化时的回调"""
        search_term = self.search_var.get().lower()
        if search_term:
            # 进行搜索过滤
            if self.current_view == "favorites":
                base_list = [r for r in self.all_radios if r.get('stationuuid') in self.favorite_ids]
            else:
                base_list = self.all_radios

            self.filtered_radios = [
                r for r in base_list
                if search_term in r.get("name", "").lower() or
                   search_term in r.get("country", "").lower() or
                   search_term in r.get("tags", "").lower() or
                   search_term in r.get("language", "").lower()
            ]
        else:
            # 恢复原始过滤
            self._update_radio_list()

        self._refresh_radio_display()

    def refresh_radios(self):
        """刷新电台列表（在后台线程执行）"""
        # 禁用刷新按钮防止重复点击
        self.refresh_btn.config(state=tk.DISABLED)
        self.status_var.set("正在刷新电台列表...")

        # 在后台线程执行
        threading.Thread(target=self._fetch_radios, daemon=True).start()

    def _fetch_radios(self):
        """实际获取电台数据的函数（在后台执行）"""
        try:
            from radio_api import RadioAPI  # 延迟导入，加快启动速度
            api = RadioAPI()

            # 获取热门电台
            self.all_radios = api.get_popular_radios(limit=200)

            # 过滤掉无效电台
            self.all_radios = [
                r for r in self.all_radios
                if r.get('url_resolved') and r.get('name')
            ]

            # 切换到主线程更新UI
            self.root.after(0, self._update_radio_list)

        except Exception as e:
            self.logger.error(f"获取电台列表时出错: {e}", exc_info=True)
            self.root.after(0, lambda: self.status_var.set(f"刷新失败：{str(e)}"))
        finally:
            # 恢复按钮状态
            self.root.after(0, lambda: self.refresh_btn.config(state=tk.NORMAL))

    def _update_radio_list(self):
        """更新电台列表显示"""
        # 根据当前视图筛选电台
        if self.current_view == "favorites":
            self.filtered_radios = [r for r in self.all_radios if r.get('stationuuid') in self.favorite_ids]
        else:
            self.filtered_radios = self.all_radios.copy()

        self._refresh_radio_display()

    def _refresh_radio_display(self):
        """刷新电台列表显示（不重新获取数据）"""
        # 清空现有列表
        for item in self.radio_tree.get_children():
            self.radio_tree.delete(item)

        # 添加新数据
        for radio in self.filtered_radios:
            station_id = radio.get('stationuuid')
            # 标记收藏状态
            favorite_mark = "★" if station_id in self.favorite_ids else ""

            self.radio_tree.insert(
                "",
                tk.END,
                values=(
                    favorite_mark,
                    radio.get("name", "未知名称"),
                    radio.get("country", "未知地区"),
                    radio.get("tags", "未知类型").replace(",", " | ")[:30],
                    radio.get("language", "未知语言"),
                    radio.get("bitrate", "0")
                )
            )

        # 更新数量统计
        count = len(self.filtered_radios)
        self.count_label.config(text=f"电台数量：{count}")

        # 更新状态
        if count == 0:
            self.status_var.set("当前没有可显示的电台")
        else:
            self.status_var.set(f"就绪 - 显示 {count} 个电台")

    def switch_view(self, view_type):
        """切换电台视图（所有/收藏）"""
        self.current_view = view_type
        # 更新按钮状态
        self.view_all_btn.config(state=tk.DISABLED if view_type == "all" else tk.NORMAL)
        self.view_fav_btn.config(state=tk.DISABLED if view_type == "favorites" else tk.NORMAL)
        # 更新列表
        self._update_radio_list()
        # 更新状态
        view_name = "所有电台" if view_type == "all" else "收藏电台"
        self.status_var.set(f"已切换到{view_name}视图")

    def toggle_favorite(self):
        """收藏/取消收藏选中的电台"""
        selected = self.radio_tree.selection()
        if not selected:
            self.status_var.set("请先选中一个电台")
            return

        # 获取选中电台的索引
        index = self.radio_tree.index(selected[0])
        if 0 <= index < len(self.filtered_radios):
            radio = self.filtered_radios[index]
            station_id = radio.get('stationuuid')

            if station_id in self.favorite_ids:
                # 取消收藏
                self.favorite_ids.remove(station_id)
                self.favorite_radios = [r for r in self.favorite_radios if r.get('stationuuid') != station_id]
                self.status_var.set(f"已取消收藏：{radio.get('name', '未知电台')}")
                self.favorite_btn.config(text="收藏选中电台")
            else:
                # 添加收藏
                self.favorite_ids.add(station_id)
                self.favorite_radios.append(radio)
                self.status_var.set(f"已收藏：{radio.get('name', '未知电台')}")
                self.favorite_btn.config(text="取消收藏")

            # 保存收藏
            self.save_favorites()
            # 更新列表
            self._update_radio_list()
        else:
            self.status_var.set("选中的电台不存在")

    def load_favorites(self):
        """加载收藏的电台"""
        try:
            if os.path.exists("favorites.json"):
                with open("favorites.json", "r", encoding="utf-8") as f:
                    self.favorite_radios = json.load(f)
                    # 更新ID集合
                    self.favorite_ids = {r.get('stationuuid') for r in self.favorite_radios if r.get('stationuuid')}
        except Exception as e:
            self.logger.error(f"加载收藏失败：{e}")
            self.favorite_radios = []
            self.favorite_ids = set()

    def save_favorites(self):
        """保存收藏的电台到本地"""
        try:
            with open("favorites.json", "w", encoding="utf-8") as f:
                json.dump(self.favorite_radios, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存收藏失败：{e}")
            self.status_var.set(f"保存收藏失败：{str(e)}")

    def play_on_double_click(self, event):
        """双击播放选中的电台"""
        selected = self.radio_tree.selection()
        if selected:
            self.current_playing_index = self.radio_tree.index(selected[0])
            self.play_selected()

    def play_selected(self):
        """播放选中的电台"""
        selected = self.radio_tree.selection()
        if not selected:
            self.status_var.set("请先选中一个电台")
            return

        self.current_playing_index = self.radio_tree.index(selected[0])

        if 0 <= self.current_playing_index < len(self.filtered_radios):
            radio = self.filtered_radios[self.current_playing_index]
            stream_url = radio.get("url_resolved") or radio.get("url")

            if stream_url:
                try:
                    # 播放电台
                    self.player.play_stream(stream_url)
                    self.status_var.set(f"正在播放：{radio.get('name', '未知电台')}")
                    # 更新收藏按钮状态
                    station_id = radio.get('stationuuid')
                    if station_id in self.favorite_ids:
                        self.favorite_btn.config(text="取消收藏")
                    else:
                        self.favorite_btn.config(text="收藏选中电台")
                except Exception as e:
                    self.logger.error(f"播放电台时出错: {e}")
                    self.status_var.set(f"播放失败：{str(e)}")
                    self.current_playing_index = -1
            else:
                self.status_var.set("该电台无可用播放地址")
                self.current_playing_index = -1

    def toggle_play_pause(self):
        """切换播放/暂停状态"""
        if self.current_playing_index == -1 or not self.filtered_radios:
            self.status_var.set("请先选择电台播放")
            return

        if self.player.is_playing():
            self.player.pause()
            self.status_var.set("已暂停播放")
        else:
            self.player.resume()
            if 0 <= self.current_playing_index < len(self.filtered_radios):
                radio_name = self.filtered_radios[self.current_playing_index].get('name', '未知电台')
                self.status_var.set(f"继续播放：{radio_name}")

    def stop_playback(self):
        """停止播放"""
        self.player.stop()
        self.status_var.set("已停止播放")
        self.current_playing_index = -1


if __name__ == "__main__":
    # 在创建Tk实例前最后一次设置Tcl路径
    # 获取Python安装路径（尝试多种方式）
    python_paths = [
        # 从解释器路径获取
        os.path.dirname(os.path.dirname(sys.executable)),
        # 手动路径（请修改为你的实际路径）
        r"C:\Users\wangy\AppData\Local\Programs\Python\Python313"
    ]

    # 尝试设置路径
    for python_path in python_paths:
        tcl_path = os.path.join(python_path, "tcl", "tcl8.6")
        tk_path = os.path.join(python_path, "tcl", "tk8.6")
        if os.path.exists(os.path.join(tcl_path, "init.tcl")):
            os.environ["TCL_LIBRARY"] = tcl_path
            os.environ["TK_LIBRARY"] = tk_path
            break

    # 启动应用
    root = tk.Tk()
    app = GlobalRadioApp(root)
    root.mainloop()

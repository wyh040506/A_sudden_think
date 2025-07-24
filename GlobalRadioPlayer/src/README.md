# 全球广播播放器

一款用于Windows系统的全球广播电台收听工具，支持在线播放全球数万电台，按地区、类型筛选，操作简单。

## 功能特点

- 收录全球数万在线广播电台（依赖radio-browser公开API）
- 支持按地区（国家）、关键词搜索筛选电台
- 双击电台列表直接播放
- 完整的播放控制：播放/暂停、停止、音量调节
- 轻量界面，无需注册，免费使用

## 安装与使用

### 前提条件

- Windows 10/11系统
- Python 3.8及以上版本
- VLC播放器（用于解码流媒体，[下载地址](https://www.videolan.org/vlc/download-windows.html)）

### 安装步骤

1. 克隆本仓库：
   ```bash
   git clone https://github.com/你的用户名/GlobalRadioPlayer.git
   cd GlobalRadioPlayer
   ```

2. 创建并激活虚拟环境：
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. 安装依赖库：
   ```bash
   pip install -r requirements.txt
   ```

4. 运行程序：
   ```bash
   python src/main.py
   ```

### 打包为EXE（可选）

如需生成可直接运行的`.exe`文件（无需Python环境）：

1. 安装打包工具：
   ```bash
   pip install pyinstaller
   ```

2. 执行打包命令：
   ```bash
   pyinstaller --onefile --windowed --name "GlobalRadioPlayer" src/main.py
   ```
   生成的`exe`文件位于`dist`文件夹中。

## 注意事项

- 部分电台可能因版权或地域限制无法播放，属于正常现象
- 网络不稳定可能导致播放卡顿，建议使用稳定网络
- 首次使用前请确保VLC播放器已正确安装
- 如果Tcl/Tk相关错误，请检查`main.py`中`setup_tcl_paths`函数的路径设置是否正确

## 使用说明

1. 程序启动后会自动加载全球热门电台
2. 可通过顶部的搜索框搜索感兴趣的电台
3. 可通过地区下拉框筛选特定国家的电台
4. 双击电台列表中的电台即可开始播放
5. 使用底部的"暂停/继续"按钮控制播放状态
6. 使用"停止"按钮停止当前播放
7. 通过音量滑块调节播放音量

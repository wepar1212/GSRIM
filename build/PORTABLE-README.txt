GSRIM — Windows x64 / NVIDIA portable research build

使用方法
1. 完整解压 ZIP 到可写目录，不要直接在压缩软件内运行。
2. 双击 GSRIM.exe。无需安装 Python 或完整 CUDA Toolkit。
3. 保留 _internal 文件夹，不要单独复制 EXE。
4. 首次启动/计算可能需要编译 CUDA 内核和生成散射表，请稍候。

硬件和系统要求
- Windows 10/11 64 位、CUDA 12 兼容 NVIDIA GPU 和驱动。
- 建议使用支持 CUDA 12.9 的最新驱动；未逐一验证所有显卡型号。
- 使用 Qt 原生桌面窗口，不需要浏览器、WebView2 或本地 HTTP 服务。
- 右上角可切换中文 / English；切换保留输入、结果和正在运行的任务。
- AMD/Intel 显卡不支持当前 GPU 核心。没有 CPU 输运回退。

便携性
程序包含独立 Python 运行时，不使用开发电脑的虚拟环境或绝对路径。
默认结果保存在 EXE 旁边的 results；目录不可写时使用当前用户的
LocalAppData/GSRIM/results。不要在运行中移动目录。
自检：运行 GPU-Self-Test.cmd，查看 gpu-self-test.json。
启动失败日志：results/startup-error.txt（或上述用户目录）。

数据与精度
此包不附带尚未核验再分发条件的 IAEA/NIST 下载数据。
缺少适用数据时，默认表格模式使用 BV 解析回退，不能保证与安装了
外部数据的研究电脑产生相同结果。可选数据放到 _internal/data/stopping，
具体结构见 DATA-README.md。检查结果中的 se_sources 和警告。
这是研究模型，不是官方 SRIM，也不是已完成全面实验验证的替代品。

许可
自有代码使用 MIT（LICENSE）。第三方依赖保留各自许可证，见 licenses。
NVIDIA 组件不是 MIT 开源软件，其使用遵循所附 NVIDIA 许可。
Python、CuPy、NumPy 等第三方的许可证也随包提供。
本包未签名，Windows 可能提示未知发布者；只从可信来源获取。

原生操作
- 控制面板按离子、靶材分层、元素、特殊参数和输出文件分区。
- 结果页支持图表、数据表和运行记录，图表可保存 PNG / BMP。
- 可载入 SRIM 的 RANGE.txt / IONIZ.txt 等参考表，始终与本程序结果分开。
- 导出新建独立子文件夹，包含 TDATA / RANGE / IONIZ / PHONON 等文本表。
- 稳定空位和替位尚未模拟，VACANCY / NOVAC 仅输出不可用说明。
- 每次新运行单独保存 project.json 和 autosave.npz，不覆盖之前的运行目录。
- 从“载入结果 / 断点”读取 NPZ 可恢复兼容历史；JSON 是只读结果快照。

Qt 许可与来源
Qt for Python / PySide6 / Shiboken6 保留所附 LGPLv3/GPL/商业许可条款。
本程序动态加载未修改的 Qt 库，不限制调试库修改或替换兼容库。
上游源码：https://code.qt.io/cgit/pyside/pyside-setup.git/
以及 https://code.qt.io/cgit/qt/ 。具体版本见 licenses/COMPONENTS.txt。

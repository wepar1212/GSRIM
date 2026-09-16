# GSRIM — GPU ion transport research simulator

独立实现的 GPU 离子输运研究程序：Python + CuPy/CUDA 计算核心、浏览器 GUI 和可选桌面窗口。自有源码采用 MIT。

**不是官方 SRIM，不调用 TRIM，不包含 SRIM 数据库，也不是经过全面验证的 SRIM 替代品。** 工程测试不等于物理精度验证，不可直接作为工艺处方。

## 功能

- ZBL 屏蔽势二体碰撞；数值积分及通用散射表。
- 静态非晶多层靶；GPU 并行入射离子历史和反冲级联。
- LS/BV 电子阻止，以及可选 IAEA/NIST 数据与解析回退。
- 射程、横向分布、背散射、透射、溅射、位移事件及能量收支。
- GUI 参数输入、进度、按批次暂停/恢复、断点、剂量换算和 CSV/JSON 导出。

## 环境与安装

主要验证环境：Windows 10/11 x64、Python 3.12、支持 CUDA 12 的 NVIDIA GPU 与兼容驱动。
CPU 可运行参考散射及非 GPU 测试，但没有完整 CPU 输运后端。AMD/Intel GPU 暂不支持。
桌面窗口额外需要 Microsoft WebView2。

PowerShell：

```powershell
git clone https://github.com/wepar1212/GSRIM.git
cd GSRIM
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-gpu.txt
.\.venv\Scripts\python.exe -m gsrim.server
```

浏览器会打开本地 GUI（默认 http://127.0.0.1:8765）。不要通过端口转发或反向代理公开服务。

可选桌面窗口：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
.\.venv\Scripts\python.exe -m gsrim.desktop
```

之后可使用 Start-GSRIM.cmd 或 GSRIM-Desktop.cmd。首次运行需要编译内核和生成表格，可能较慢。

**第三方阻止数据不随源码分发。** 见 [数据说明](data/README.md)。缺少适用表格时默认模式回退到 BV；
结果不一定与安装了数据的本地版本一致。检查 stopping_sources 与警告。

## 测试

```powershell
# 非 GPU 测试只需 requirements.txt
.\.venv\Scripts\python.exe -B run_tests.py
# NVIDIA GPU 上的小规模回归测试
.\.venv\Scripts\python.exe -B run_tests.py --gpu
```

测试输出隔离在临时目录，不覆盖应用断点。缺少 GPU 或外部数据时相应测试跳过。
测试通过不表示已完成跨离子、材料和能量范围的物理标定。

## 项目结构

```text
gsrim/                参数、材料、物理模型、统计、服务端与桌面入口
  kernels/            CUDA 散射和输运内核
web/                  HTML/CSS/JavaScript 界面
tests/                单元测试与 GPU/接口回归测试
docs/                 模型边界、修复及发布检查说明
data/README.md        可选外部数据说明
build/                本地打包脚本（不是已审计的二进制发布）
requirements*.txt     分层依赖
```

环境、下载数据、研究草稿、私人配置、计算结果和打包产物不纳入仓库。

## 科学边界

- 静态非晶靶；不模拟沟道、退火、成分演化、化学溅射或完整替位过程。
- 位移产生事件不等于稳定空位；KP/NRT 和损伤能估计已停用。
- 粒子数、截止能量、碰撞范围和插值表需要收敛检查。
- 有失败历史的结果仅供诊断，不能换算剂量或导出 CSV。
- 修复前的历史射程比和速度不是当前精度或加速比的依据。
- GPU 加速不自动提高模型精度；定量使用必须与独立参考及实验对照。

详见 [物理说明](docs/PHYSICS.md)、[SRIM 差异](docs/SRIM_EQUIVALENCE.md)、
[修复记录](docs/REVIEW_FIXES.md)。

## 许可证

自有源码采用 [MIT](LICENSE)。第三方依赖、数据不受其覆盖，见
[第三方说明](THIRD_PARTY_NOTICES.md)。本次仅发布源码，不发布现有 Portable 包。

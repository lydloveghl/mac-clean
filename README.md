# Mac Cleaner

一款 macOS 应用管理与文件清理工具，提供友好的图形界面，帮助你快速卸载应用、清理垃圾文件、释放磁盘空间。

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)
![License](https://img.shields.io/badge/license-MIT-yellow)

## 功能特性

### 应用管理
- 快速扫描 `/Applications`、`~/Applications`、`/System/Applications` 下所有已安装应用
- 显示应用名称、版本、大小、Bundle ID、安装路径及图标
- 单个/批量卸载应用，删除时弹出系统密码框确认权限
- 卸载时可选择是否同步清理关联的缓存文件

### 文件清理
| 清理类型 | 说明 |
|----------|------|
| 缓存清理 | 扫描并清理 `~/Library/Caches`、`/Library/Caches` 等目录 |
| 日志清理 | 清理系统和应用日志文件 |
| 大文件扫描 | 按自定义阈值（默认 100MB）全盘查找大文件 |
| 应用文件分析 | 按应用查看所有关联文件，支持分类和精确选择 |

### 文件从属关系与风险评估
- 自动识别文件所属应用及 Bundle ID
- 五级影响评估：
  - ✅ 安全 — 可安全删除（缓存、日志）
  - ⚠️ 低风险 — 删除后应用需重新配置
  - 🟠 中风险 — 可能丢失用户数据
  - 🔴 高风险 — 应用可能无法运行
  - ⛔ 危险 — 不应删除（钥匙串等）

### 操作体验
- 扫描时逐条显示结果，无需等待全部完成
- 支持按目录 / 按应用两种分类视图
- 点击表头可按大小、时间、影响级别等排序
- 双击文件预览内容（plist、json、文本等）
- 右键菜单：预览 / 打开 / 打开所在文件夹 / 复制路径
- 勾选复选框批量选择，或 Ctrl/Shift 多选精确选择
- 删除时弹出 macOS 系统密码框获取管理员权限
- 删除后实时更新列表和统计

## 安装与运行

### 环境要求
- macOS 10.15+
- Python 3.8+

### 安装

```bash
# 克隆项目
git clone https://github.com/lydloveghl/mac-clean.git
cd mac-clean

# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 运行

```bash
# 方式一：启动脚本
./start.sh

# 方式二：手动运行
source venv/bin/activate
python3 src/main.py

# 方式三
python3 run.py
```

### 打包 DMG

```bash
# 安装打包工具
pip install pyinstaller dmgbuild

# 使用项目自带脚本打包
python3 build_dmg.py
```

生成的 `MacCleaner.dmg` 位于项目根目录。

## 项目结构

```
mac-clean/
├── src/
│   ├── main.py                 # 主窗口
│   ├── app_scanner.py          # 应用扫描器
│   ├── uninstaller.py          # 卸载管理器
│   ├── cache_selector.py       # 缓存选择对话框
│   ├── progress_dialog.py      # 进度对话框
│   ├── file_analyzer.py        # 文件分析器
│   ├── file_cleanup_dialog.py  # 文件清理对话框
│   ├── file_preview_dialog.py  # 文件预览对话框
│   └── app_icon_manager.py     # 应用图标管理器
├── resources/                  # 资源文件
├── requirements.txt            # Python 依赖
├── build_dmg.py                # DMG 打包脚本
├── run.py                      # 启动入口
├── start.sh                    # Shell 启动脚本
└── README.md
```

## 文件目录说明

| 目录 | 说明 | 删除风险 |
|------|------|----------|
| `~/Library/Caches` | 应用缓存 | ✅ 安全 |
| `~/Library/Logs` | 日志文件 | ✅ 安全 |
| `~/Library/Saved Application State` | 窗口恢复状态 | ✅ 安全 |
| `~/Library/Preferences` | 偏好设置 | ⚠️ 低风险 |
| `~/Library/Application Support` | 应用数据 | ⚠️~🟠 |
| `~/Library/Containers` | 沙盒容器数据 | 🟠 中风险 |

## 技术栈

- **Python 3** — 主语言
- **PyQt6** — 图形界面
- **PyInstaller** — 应用打包
- **dmgbuild** — DMG 制作

## 许可证

[MIT License](LICENSE)

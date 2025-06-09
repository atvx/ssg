# 浏览器环境配置指南

## 概述

本项目现已支持跨平台浏览器自动化，包括：
- **Windows** (32位/64位)
- **macOS** (Intel/Apple Silicon)
- **Linux** (64位)

系统会自动检测操作系统并配置相应的Chrome Driver和临时目录。

## 自动功能

### Chrome Driver 自动管理
1. **自动查找**：系统会在常见路径中查找已安装的Chrome Driver
2. **自动下载**：如果未找到，会自动下载对应版本的Chrome Driver
3. **跨平台路径**：支持不同操作系统的默认安装路径

### 临时目录管理
- **Windows**: 使用系统临时目录 + chrome_tmp
- **macOS/Linux**: 使用 /tmp/chrome_tmp
- **权限处理**: 自动设置合适的文件权限

## 手动安装指南

如果自动安装失败，可按以下方式手动安装：

### Windows

#### 方法1: 手动下载
1. 访问 [ChromeDriver官网](https://chromedriver.chromium.org/downloads)
2. 下载与Chrome版本匹配的 `chromedriver.exe`
3. 将文件放在以下位置之一：
   - `C:\Program Files\Google\Chrome\Application\`
   - 系统PATH环境变量中的任意目录
   - 设置环境变量 `CHROMEDRIVER_PATH` 指向文件路径

#### 方法2: 使用包管理器
```bash
# 使用 chocolatey
choco install chromedriver

# 使用 scoop
scoop install chromedriver
```

### macOS

#### 方法1: Homebrew (推荐)
```bash
brew install chromedriver
```

#### 方法2: 手动下载
1. 访问 [ChromeDriver官网](https://chromedriver.chromium.org/downloads)
2. 下载对应架构的版本：
   - Intel Mac: `chromedriver_mac-x64.zip`
   - Apple Silicon: `chromedriver_mac-arm64.zip`
3. 解压并移动到 `/usr/local/bin/` 或 `~/bin/`
4. 设置执行权限：`chmod +x /path/to/chromedriver`

### Linux

#### 方法1: 包管理器 (推荐)
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install chromium-chromedriver

# CentOS/RHEL/Fedora
sudo yum install chromium-chromedriver
# 或
sudo dnf install chromium-chromedriver
```

#### 方法2: 手动下载
1. 访问 [ChromeDriver官网](https://chromedriver.chromium.org/downloads)
2. 下载 `chromedriver_linux64.zip`
3. 解压并移动到 `/usr/local/bin/` 或 `~/bin/`
4. 设置执行权限：`chmod +x /path/to/chromedriver`

## 环境变量配置

如果需要指定特定的Chrome Driver路径，可以设置环境变量：

### Windows
```cmd
set CHROMEDRIVER_PATH=C:\path\to\chromedriver.exe
```

### macOS/Linux
```bash
export CHROMEDRIVER_PATH=/path/to/chromedriver
```

## 常见问题

### 1. Chrome版本不匹配
**错误信息**: "This version of ChromeDriver only supports Chrome version X"

**解决方法**: 
- 更新Chrome浏览器到最新版本
- 或下载匹配当前Chrome版本的ChromeDriver

### 2. 权限问题
**错误信息**: "Permission denied" 或 "chromedriver: permission denied"

**解决方法**:
```bash
# macOS/Linux
chmod +x /path/to/chromedriver

# 如果是安全策略问题 (macOS)
xattr -d com.apple.quarantine /path/to/chromedriver
```

### 3. 路径问题
**错误信息**: "chromedriver not found" 或 "No such file or directory"

**解决方法**:
1. 确认ChromeDriver已正确安装
2. 检查PATH环境变量
3. 使用绝对路径设置 `CHROMEDRIVER_PATH`

### 4. 网络问题
如果自动下载失败，可能是网络问题：
1. 检查网络连接
2. 如果在代理环境，配置相应的代理设置
3. 手动下载并安装

## 测试配置

创建一个简单的测试脚本验证配置：

```python
from core.meituan.browser import init_chrome_driver

# 测试配置
config = {
    "HEADLESS": True,  # 无头模式测试
    "MONITOR_API_RESPONSE": False
}

try:
    driver = init_chrome_driver(config)
    print("✅ 浏览器启动成功")
    driver.get("https://www.google.com")
    print(f"✅ 页面加载成功: {driver.title}")
    driver.quit()
    print("✅ 浏览器关闭成功")
except Exception as e:
    print(f"❌ 浏览器配置失败: {e}")
```

## 性能优化建议

1. **无头模式**: 生产环境建议使用无头模式以提高性能
2. **用户数据目录**: 本地开发可保留用户数据目录以保持登录状态
3. **资源限制**: 在资源受限环境中适当调整Chrome启动参数

## 更新说明

- **v2.0**: 添加跨平台支持
- 自动Chrome Driver下载和管理
- 改进的错误处理和用户友好的安装指南
- 支持Windows、macOS、Linux三大平台 
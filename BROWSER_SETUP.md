# 浏览器设置指南

本文档提供了在不同操作系统上设置Edge浏览器和EdgeDriver的详细步骤。

## 安装Microsoft Edge

### Windows
1. 从[Microsoft官网](https://www.microsoft.com/zh-cn/edge)下载并安装最新版Edge浏览器
2. 安装完成后，Edge会自动添加到系统路径中

### macOS
1. 从[Microsoft官网](https://www.microsoft.com/zh-cn/edge)下载并安装最新版Edge浏览器
2. 将应用拖到Applications文件夹中完成安装

### Linux (Ubuntu/Debian)
```bash
# 添加Microsoft Edge存储库
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/
sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge.list'
sudo rm microsoft.gpg

# 安装Edge浏览器
sudo apt update
sudo apt install microsoft-edge-stable
```

## 安装EdgeDriver

EdgeDriver是Microsoft Edge浏览器的WebDriver实现，用于自动化测试。

### 方法1: 使用webdriver-manager (推荐)
在Python中，可以使用webdriver-manager自动下载和管理EdgeDriver:

```python
from selenium import webdriver
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.edge.service import Service

service = Service(EdgeChromiumDriverManager().install())
driver = webdriver.Edge(service=service)
```

### 方法2: 手动下载
1. 访问[Microsoft Edge WebDriver下载页面](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/)
2. 下载与你的Edge浏览器版本匹配的EdgeDriver
3. 解压并移动到系统路径中:
   - Windows: 放在PATH环境变量包含的目录中
   - macOS/Linux: 移动到 `/usr/local/bin/` 或 `~/bin/`
4. 设置执行权限（仅Linux/macOS）：`chmod +x /path/to/msedgedriver`

## 环境变量配置

如果需要指定特定的Edge Driver路径，可以设置环境变量：

### Windows
```cmd
set MSEDGEDRIVER_PATH=C:\path\to\msedgedriver.exe
```

### macOS/Linux
```bash
export MSEDGEDRIVER_PATH=/path/to/msedgedriver
```

## 常见问题

### 1. Edge版本不匹配
**错误信息**: "This version of MSEdgeDriver only supports Microsoft Edge version X"

**解决方法**: 
- 更新Edge浏览器到最新版本
- 或下载匹配当前Edge版本的EdgeDriver

### 2. 权限问题
**错误信息**: "Permission denied" 或 "msedgedriver: permission denied"

**解决方法**:
```bash
# macOS/Linux
chmod +x /path/to/msedgedriver

# 如果是安全策略问题 (macOS)
xattr -d com.apple.quarantine /path/to/msedgedriver
```

### 3. 路径问题
**错误信息**: "msedgedriver not found" 或 "No such file or directory"

**解决方法**:
1. 确认EdgeDriver已正确安装
2. 检查PATH环境变量
3. 使用绝对路径设置 `MSEDGEDRIVER_PATH`

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

1. 使用无头模式减少资源消耗
2. 禁用不必要的浏览器功能（如图片加载、扩展等）
3. 使用页面加载策略（如 `eager` 模式）
4. 优化内存使用（设置较小的JavaScript堆大小）
5. 关闭不必要的浏览器进程
6. 定期清理浏览器缓存和临时文件 
# 无 WSL 环境下的 Android APK 打包指南

如果您在 Windows 环境下尚未配置 Ubuntu/WSL，**强烈不建议**直接尝试在 Windows PowerShell 强行运行 Buildozer（Buildozer 严重依赖 Linux 专属编译工具链和路径系统，在原生 Windows 会疯狂报错）。

为此，我们提供两种不需要配置本地系统、直接利用**云端免费算力**的极简替代方案。

---

## 方案一：使用 GitHub Actions 自动云端打包（🌟 极度推荐，最省心）

我已经在此项目中为您配置好了自动化工作流 `.github/workflows/buildozer.yml`。这意味着只要您将代码推送到 GitHub，微软的云端 Ubuntu 服务器就会自动帮您把代码打包成 APK。

### 详细操作流程：
1. **上传代码到 GitHub**：
   - 确保您的当前代码已全部 Commit。
   - 在您的 GitHub 账号中新建一个空的仓库（Repository），例如命名为 `VolumeDemo`。
   - 将本地代码推送到该仓库：
     ```powershell
     git remote add origin https://github.com/<您的用户名>/VolumeDemo.git
     git branch -M master
     git push -u origin master
     ```
2. **等待云端打包**：
   - 用浏览器打开您刚创建的 GitHub 仓库页面。
   - 点击上方的 **`Actions`** 选项卡。
   - 您会看到一个名为 `Android Build with Buildozer` 的任务正在运行（标志为黄色的等待圈）。由于首次打包需要下载 NDK/SDK，**预计将耗时约 10-15 分钟**。
3. **下载 APK 产物**：
   - 等待圆圈变成绿色的 `✓`，点击进入该任务的详情页。
   - 在页面最下方的 **`Artifacts`** 区域，会看到一个名为 **`VolumeDemo-Android-APK`** 的压缩包。
   - 下载并解压该 zip 文件，里面就是可以安装在手机上的 `xxxxx-debug.apk`。

---

## 方案二：使用 Google Colab 白嫖云算力打包（备选方案）

如果您不想把代码传给 GitHub，或者想快速在一次性的云容器中实验，可以使用 Google Colab。

### 详细操作流程：
1. **压缩本地工程**：在本地路径（`D:\code\volume_demo`）下，将所有代码和配置打包成 `volume_demo.zip`（不要打包 `.git` 等隐藏大体积文件）。
2. **打开 Colab**：使用浏览器访问 [Google Colab](https://colab.research.google.com/)，随便新建一个 Notebook。
3. **上传代码**：点击左侧边栏的“文件夹”图标，将 `volume_demo.zip` 拖拽上传到这里。
4. **执行以下打包命令（分步运行框里的代码）**：
   ```python
   # 框 1: 解压代码
   !unzip volume_demo.zip -d volume_demo
   ```
   ```python
   # 框 2: 安装 Ubuntu 打包依赖环境
   !sudo apt update
   !sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
   !pip install --user --upgrade buildozer cython virtualenv
   ```
   ```python
   # 框 3: 进入目录并打包（约需15分钟，耐心等待）
   %cd volume_demo
   !buildozer android debug
   ```
5. **下载 APK**：执行完后，代码包里面的 `bin` 文件夹内就会生成 `xxxxx-debug.apk` 文件，右键它点击下载即可。

---

## 第三步：安卓真机测试指引（完成打包后必做）

获得 APK 并在安卓手机上安装后，我们需要验证最重要的一环：真机硬件录音拟真情况。

1. **权限验证**：启动 App，点击大红圆圈录音，系统是否正确弹出了`允许录音`的权限框？如果不给权限，App 是否会闪退还是平稳忽略？
2. **硬件底噪验证**：授权后，请保持几秒钟安静，此时红线处刷出的波形应是一条几乎没有起伏的直线。如果没有说话时波形依然乱跳，说明后续需要引入去底噪算法。
3. **分贝收音反馈**：靠近手机底部麦克风正常说话，波形是否能上拉涨满中心区域？如果幅度很小（像蚂蚁一样），或者幅度极其巨大（直接平顶），请详细反馈给我，我将针对由于真实硬件 16-bit PCM 输入导致的比例失调编写专用的动态增益（AGC）算法。
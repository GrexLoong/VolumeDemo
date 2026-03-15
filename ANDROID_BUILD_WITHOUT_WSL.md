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

### 🔴 如果遇到红色叉叉（打包失败）该怎么办？

红色的叉叉表示云端的打包任务遇到了错误并停止了运行。因为 Android 打包涉及数千个文件的编译，任何一点环境不匹配都可能导致失败。请按以下详尽步骤排查：

1. **进入错误日志详情**：
   - 在 `Actions` 页面，点击那个红色的 `Android Build with Buildozer` 任务名称。
   - 左侧边栏会有一个列出步骤的列表，点击红色的 `build-android`。
   - 此时右侧会展开一个命令行黑色窗口。向下滚动，找到带红叉的那一步（通常是 `Build with Buildozer` 这一步）。

2. **展开报错详情并截图/复制**：
   - 点击这一步右侧的小箭头（`>`）展开详细的运行日志。
   - 滚动到日志的 **最底部**（通常最后 20-50 行包含了最关键的报错原因，例如：`Command failed: ...`，或者 `ModuleNotFoundError` 等）。
   - 将最底部带有 `Error` 关键词的那段报错截图，或者直接将这段文本原封不动地复制发给我。

3. **最常见的几种报错及一键排查思路**（供参考，最好还是发日志给我）：
   - **Cython 版本不匹配**：如果看到 `ValueError: numpy.ndarray size changed` 或 `cython` 相关的编译错误，我们在 `buildozer.spec` 中限制一下 Cython 的版本即可。
   - **缺少第三方 Python 库**：如果你在代码中 `import` 了额外的库，但没有在 `buildozer.spec` 的 `requirements = xxx` 中声明，就会报错。
   - **平台架构错误 / NDK 下载失败**：有时候是由于微软服务器网络波动导致 Android NDK 没下载全，这种情况下可以在 GitHub Actions 页面右上角点击 **`Re-run all jobs`**（重新运行一次试试运气）。

**下一步操作**：请您直接把那段报错信息发给我，我将马上为您修改相关配置，您只需在我修改后重新 `git push` 一次即可。

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

## 第三步：安装与真机环境测试（核心环节）

您现在已经成功下载了 `VolumeDemo-Android-APK.zip`。请按照以下详尽步骤将其安装到您的安卓手机上并进行测试：

### 1. 解压与传输 APK
- **解压缩**：在电脑上解压 `VolumeDemo-Android-APK.zip`，您会得到一个以 `.apk` 结尾的应用安装包（例如 `waveformdemo-0.1.0-arm64-v8a_armeabi-v7a-debug.apk`）。
- **发送至手机**：最简单的方法是使用**微信/QQ的“文件传输助手”**将此 `.apk` 文件发送到您的手机，或者通过 USB 数据线直接拷贝到手机存储中。

### 2. 在手机上授权安装
- **点击安装**：在手机上（微信或文件管理器中）点击该 APK 文件。
- **⚠️ 忽略安全警告**：由于这是您个人刚刚编译出的开发者调试版（Debug）应用，未向任何应用商店缴纳保护费和配置签名，因此大多数国产手机系统（小米、华为、vivo、OPPO 等）会弹窗严重警告“未知来源”、“有风险”、“包含病毒”或“未检测到安全签名”。
- **强制放行**：请不要担心，代码完全是您亲手把控的。请在手机的安全拦截提示中，选择“**了解风险并继续安装**”、“**无视风险安装**”或在系统设置里勾选“**允许安装未知应用**”。

### 3. 上机实测反馈（最新修复版）
安装成功后，请打开 App，完成以下 3 个核心环节的测试，然后将结果告诉我：

1. **麦克风收音恢复测试（最关键）**：
   - 之前由于 Python 和 Java 数组的底层转换切断了数据导致“平直线”。现在已经改用 Java JNI 的原生底层内存反射重新穿透连接。
   - 请在安静时观察红线中心（现在红线应该已经在**屏幕正中**了）。正常说话时，**波形是否开始剧烈跳动？不再是一条直线了？**
2. **中心原点与对称滚动测试**：
   - 之前波形是在最右侧，而且由于声音的响度导致波形宽度会变化（就像一排宽窄不一的积木），引发数学坐标积攒误差，造成波形产生偏移导致红线“看起来在移动”。
   - 目前已经将：1.红线固定在**屏幕正中**，2.波形的横向宽度**锁定为均宽**，3.只要每次按录制，强制**清空之前的波形重新回到中心点**。
   - 请问开始、继续录音多次时，波形是否表现为**坚定地从中心红线吐出，并以恒定速度均匀平滑地向左侧滚动流出**？
3. **分贝收音反馈（如恢复正常的话需评估）**：
   - 如果波形正常了，请测试普通说话时的幅度：是涨得刚刚好，还是“像蚂蚁一样太小”，或者是“太容易顶到天花板”？

**后续操作**：请执行云端打包并安装验证。如果您确认**波形恢复了起伏（解决了直线问题）**且**生成位置位于正中间并且不再乱跑（解决了起底偏移问题）**，请把最新情况回复给我。
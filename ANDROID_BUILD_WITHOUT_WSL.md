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

### 验证修复后的核心功能（最新版比对检查清单）：

经历了几波底层重构，目前最新代码已经全面向 iOS 的“Voice Memos（语音备忘录）”1:1 像素级对齐。请覆盖安装新包后，着重验证以下三点以确认是否收口：

1. **核心阻塞 1：波形是否具备了真实生命力？**
   - **行为预期**：不再是“无论怎么说话都是水线上一排毫无反应的点”。由于我们启用了全新的 `java.nio.ByteBuffer` 内存直读技术跨过了以前获取不到 16bit 音频阵列的暗坑，现在当您说话时，系统会自动捕捉人声的短时 RMS 能量。
   - **检查动作**：把手机放桌上保持安静，此时应画出极小幅度的平稳波段；拿到嘴边发“啊——”的长音，波形应瞬间饱满弹起，并随您声音的顿挫而上下拉伸缩放，全程高度在 12dp～58dp 之间律动！
2. **核心阻塞 2：波形滚动速度是否与录音时长严密对应？**
   - **行为预期**：绝对不再是“2-3秒钟就滑出屏幕找不到了”。我们重新设计了录音帧的采样密度（`5.0 FPS`），将其牢牢锁死在绝对的 `10dp` 推进步长上！现在的整体滚动速度为 `50像素/秒`。
   - **检查动作**：录制一段超过 10 秒的说话声。您会发现从中间红线“吐”出来的音频，会像缓慢流动的河流一样非常沉稳地向左移动，半个屏幕完全可以兜得住近 10 秒的超长录音轨迹，能够让您从容地回看上一句说的话。
3. **视觉阻塞：形态与尺寸是否已经落地为标准胶囊体？**
   - **行为预期**：再也没有贴在中间线上的“像素像素点”了！哪怕在深夜最寂静的深室里录音，最细微的环境音也会强制渲染为至少具备 `12dp` 高度的**粗壮胶囊（Capsule）**。我们应用了标准的 4dp 宽搭配 6dp 间距。
   - **检查动作**：无论声音大小，注意看屏幕新画出来的音频柱的上下两头——它们现在应该都是完美对称的半圆形收口，不会有扁平的直角，完全还原苹果设计的优雅丰满形态。

如果顺利符合上述这 3 条现象，则代表核心技术栈彻底打通！请给我肯定反馈。如果出现任何其他异常效果（例如麦克风仍无权限或底噪过大直接通顶），请用详尽的话语告知我，我们将马上修正。
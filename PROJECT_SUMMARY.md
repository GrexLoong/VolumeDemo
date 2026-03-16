# Volume Demo 项目开发总结与技术文档

**记录日期**: 2026年3月16日
**项目状态**: 核心功能与视觉打通，第一阶段开发暂停/封版。

---

## 1. 项目简介与核心目标

本项目旨在使用纯 Python 技术栈（借助 Kivy 框架和 Buildozer）在 Android 平台上实现一个高质量的语音录制与波形可视化组件。
其**终极产品目标**是达成与 **iOS iOS Voice Memos (苹果原生语音备忘录)** 像素级对齐的视觉效果与交互体验。

### 核心实现的功能：
- **真机实时环境音捕获**：支持调用 Android 原生 `AudioRecord` 接口进行 16-bit PCM 录音。
- **高动态保真波形**：能够敏锐捕获人声的 RMS 能量，生成高度从 `12dp` 到高达 `180dp` 的动态柱状图。
- **类 iOS 视觉交互**：使用胶囊体（Capsule）形状的完整半圆收口波形，配合极度稳定的 `50px/s` 历史轨迹向左滚屏系统。
- **云端原生编译流水线**：脱离繁杂的本地 Linux/WSL 配置，实现了依托 GitHub Actions 的 CI/CD 云端构建 Android APK。

---

## 2. 关键历程与技术攻坚点 (Technical Hurdles Solved)

在目前的开发周期内，我们解决了以下三个维度的极其棘手的核心技术障碍，为项目奠定了坚实的基础：

### 阶段一：打破 Buildozer 打包环境壁垒 (CI/CD 自动化)
- **挑战**：Buildozer 对 Linux 宿主系统的依赖（如特定版本的 Python、Cython、NDK 路径）繁重且脆弱，导致早期在 Windows/WSL 中极其容易构建崩溃。
- **方案**：我们在 `.github/workflows/buildozer.yml` 中编写了极度强健的云打包脚本。锁定了 `ubuntu-22.04` 环境，显式安装了失去维护的 `libtinfo5` 依赖，将 JDK 版本控制在 17，并通过 `yes |` 解决了 Android SDK 协议强制拦截问题。同时限制 `"Cython<3"` 以配合当前的 Kivy 编译链。

### 阶段二：打通 Android Java 底层音频硬件与 Python 的内存黑洞
- **挑战**：初期应用在真机上运行时存在录音“毫无起伏”的假死问题（呈现为直线点阵）。其根本原因在于 Pyjnius（JNI 通信桥梁）无法直接将 Python 的原生 `array('h')` 作为 Out-Parameter 传给 Java 的 `AudioRecord.read()` 获取内存修改。
- **方案**：摒弃传统数组传递，在 `waveform/audio_source.py` 中引入了 `java.nio.ByteBuffer`。通过 `ByteBuffer.allocateDirect()` 在底层直接开辟内存映射，配合 `ByteOrder.nativeOrder()`，成功以无损且不阻断的方式将 Android 底层的 PCM 字节流提取回 Python 层，唤醒了项目的原始数据采集能力。

### 阶段三：iOS 原生级渲染管线重构 (UI 与视觉精算)
- **挑战**：波形在长时间录制下发生坐标系“漂移”（越来越快或错乱），同时原本的红线位于屏幕中央，严重浪费左侧展示区域，且最高波形（58dp）视觉感极其扁平。
- **方案**：
  1. **坐标系绝对化**：在 `waveform/widget.py` 中引入 `_viewport_x` 机制，彻底摒弃本地相对坐标系增量，将所有波形的渲染点锚定在绝对时间流逝上，彻底解决漂移。
  2. **视口利用率极值化优化**：创建 `_get_playhead_x()` 将红线居右（距离屏幕边缘 `72dp`），将超过 70% 的手机屏幕留作回放视野。
  3. **视觉张力强化**：在 `waveform/constants.py` 中，严格定义柱体渲染规格——标准的宽度 `4dp`、间距 `6dp`，并将容器扩展至 `240dp`，允许波柱依据分贝呈现最高达 `180dp` 的夸张起伏，真正还原了 iOS 语音录制时的动态冲击力。

---

## 3. 项目架构说明

在恢复开发时，请参考以下核心文件职能：

```text
volume_demo/
├── main.py                          # Kivy App 入口，组装 UI 容器面板与生命周期管理
├── buildozer.spec                   # Android 交叉编译配置（包名、SDK版本、所需权限RECORD_AUDIO等）
├── .github/workflows/buildozer.yml  # GitHub Actions 自动化编译脚本
├── ANDROID_BUILD_WITHOUT_WSL.md     # 给开发者的免配置云打包装机说明书
├── waveform/                        # ⭐ 核心波形与音频处理业务包
│   ├── constants.py                 # UI 尺寸、刷新率 (5.0 FPS)、步长 (10dp)、高度极限配置字典
│   ├── widget.py                    # 承载一切 Canvas 绘制的核心画布渲染器（包含红线及胶囊绘制）
│   └── audio_source.py              # Android Java 麦克风硬件通信、权限申请、PCM/RMS 声强算法解码
```

---

## 4. 未来展望与后续 Todo 建议

在您未来重新开启该项目时，可以直接在现有的极其稳定的基础上继续拓展高级功能：

1. **暂停与恢复机制**：目前波形为持续写入，后续可加入录音暂停、继续拼接的逻辑。
2. **手势滑动回放**：使得用户能在录音结束后（或暂停时）通过左滑右滑手势，查看并重播历史波形。
3. **音频文件落盘存储**：在 RMS 解析波形的同时，将原始 PCM 流编码并写入 `wav` 或 `m4a` 文件保存到手机存储器中。

**总结**：目前底层设施的基建“硬骨头”已被彻底啃下，从录音硬件打通到页面流畅绘制的双链路均已实现，期待您休整归来后继续大展身手！
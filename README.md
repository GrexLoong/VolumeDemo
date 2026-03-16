# Volume Demo - 语音备忘录（高保真波形复刻）

本项目是一个基于 Python 和 Kivy 框架开发的 Android 录音与实时波形展示应用。其核心视觉目标是**1:1 像素级复刻 iOS 系统原生“语音备忘录 (Voice Memos)”的界面的波形动态效果**。

通过调用 Android 底层原生音频接口 (JNI/Pyjnius) 和优化 Kivy 图形渲染管线，实现了高性能的真机实时音频能量捕获与顺滑的波形滚动展示。

## 📖 文档导航

为了方便了解与继续开发，项目包含了以下详细文档：

1. **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)**
   - **（⭐核心关注）项目开发总结与详细技术白皮书**。详细记录了项目从零到一的开发历程、核心技术难点（如 JNI 内存跨界通信、波形漂移修复、UI iOS化）、代码结构以及当前工作状态。如果您在未来恢复本项目开发，请首要阅读此文档以快速恢复技术上下文。

2. **[ANDROID_BUILD_WITHOUT_WSL.md](ANDROID_BUILD_WITHOUT_WSL.md)**
   - **零本地环境 APK 打包指南**。记录了如何利用 GitHub Actions 自动化流水线（或 Google Colab）在纯云端算力下将本项目编译为 Android APK。包含了常见打包报错分析及真机验证测试核对清单。

## 🚀 快速接手与持续开发

1. 核心应用入口位于 `main.py`。
2. Android 原生麦克风调用与数据桥接位于 `waveform/audio_source.py`。
3. 波形渲染与精调布局逻辑位于 `waveform/widget.py` 和 `waveform/constants.py`。

目前开发已处于**视觉与功能双重验证完毕的稳定阶段**，代码库已全部就绪，可以直接使用 `git push` 触发 `.github/workflows/buildozer.yml` 进行打包装机。
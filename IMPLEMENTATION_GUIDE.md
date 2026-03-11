# Android 录音波形组件实现说明

本文档解释当前代码实现、运行方式、验证步骤和后续扩展点。

## 1. 已实现内容

1. Kivy 工程骨架与依赖声明
2. 波形组件 `WaveformWidget`（右向左匀速滚动、圆角胶囊条、固定间距）
3. 数据源抽象与双实现：`MockSource` + `MicrophoneSource`
4. 应用入口 `main.py`，支持 `--mock` 模式
5. Android 打包起始配置 `buildozer.spec`（含 `RECORD_AUDIO` 权限）

## 2. 代码结构说明

- `main.py`
  - 负责应用启动、参数解析、Android 权限请求、数据源选择和兜底切换
- `waveform/constants.py`
  - 负责尺寸、颜色、帧率、音频参数等统一常量
- `waveform/audio_source.py`
  - `AudioSource` 协议定义
  - `MockSource`：说话段/静默段包络 + attack/release 平滑
  - `MicrophoneSource`：pyjnius 调用 Android `AudioRecord` 并计算 RMS
- `waveform/widget.py`
  - 新音柱从最右侧生成，所有音柱匀速整体左移
  - 音柱间距固定 6dp，不随音量变化
  - 音柱高度在 12dp~58dp 映射，宽度在 3dp~4dp 随高度联动
  - 音柱生成后高度冻结，仅位置随时间移动

## 3. 关键实现决策

1. 使用 `deque(maxlen)` 保存波形窗口，实现 O(1) 右入左出
2. 采用 `Clock.schedule_interval(..., 1/60)` 驱动渲染循环
3. 音频采样与渲染解耦：麦克风采样维持实时，渲染统一 60fps
4. 波形滚动采用“固定速度 + 固定间距 + 右侧生成”时序模型
4. Android 麦克风失败时自动回退到 Mock 模式，确保始终可演示

## 4. 本地运行步骤（Conda）

> Windows 下可以直接验证 Mock 动画；Android 打包推荐 Linux/WSL 环境。

1. 创建并激活 conda 环境（示例）
  - `conda create -n voldemo python=3.11 -y`
  - `conda activate voldemo`
2. 安装依赖
   - `pip install -r requirements.txt`
3. 运行 Mock 模式
   - `python main.py --mock`

## 5. Android 真机接入说明

1. 设备首次运行时需授权麦克风
2. 若在 Android 且未加 `--mock`，应用优先尝试 `MicrophoneSource`
3. 若 pyjnius 或权限失败，应用自动降级为 Mock 数据源

## 6. 验证清单

1. 视觉验证：波形为垂直圆角矩形，间距固定，右侧实时生成
2. 动效验证：整体从右向左平滑滚动，无明显阶梯感
3. 稳定性验证：反复启动/关闭应用无线程残留异常
4. 降级验证：故意触发麦克风失败时，动画仍可继续（Mock）

## 7. 下一步建议

1. 增加“开始/停止录音”按钮和状态指示
2. 增加 FPS 监控 HUD（显示实时帧率）
3. 增加音量门限和自动增益，优化不同环境噪声下的视觉观感

## 8. Mock 速度调节说明

当前默认已降低 Mock 的推进速度，避免测试时看起来过快。

可在以下常量直接调节观感：

1. `waveform/constants.py` 中 `MOCK_SAMPLE_FPS`：控制每秒新增波形条数量（越小越慢）
2. `waveform/constants.py` 中 `SCROLL_SPEED_DP_PER_SEC`：控制整体左移速度
3. `waveform/constants.py` 中 `MOCK_SPEAK_*` 和 `MOCK_SILENCE_*`：控制说话/停顿起伏幅度
4. `waveform/constants.py` 中 `MOCK_ATTACK_ALPHA`、`MOCK_RELEASE_ALPHA`：控制抗闪烁与响应速度

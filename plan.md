# Plan: Android 录音波形组件 (Kivy)

## TL;DR
使用 **Kivy + Buildozer** 构建仿 iPhone 语音备忘录的实时录音波形组件。Kivy 的 OpenGL Canvas 指令系统提供原生 `RoundedRectangle` 和 60fps `Clock` 调度，是 Python 生态中唯一能满足此场景实时自定义渲染需求的框架。采用 `deque` 固定窗口 + Canvas 指令属性更新（非 clear+redraw）的架构实现丝滑左滚动画。

---

## 一、技术选型：Kivy + Buildozer

### 选择理由
| 维度 | Kivy | Flet | BeeWare |
|---|---|---|---|
| 圆角矩形 | ★★★★★ 原生 `RoundedRectangle` GPU 指令 | ★★★ 需 Path 组合 | ★★☆ 需手动 arc+line |
| 60fps 动画 | ★★★★★ `Clock.schedule_interval` + VSync | ★★☆ gRPC IPC 瓶颈 | ★★☆ 无帧调度器 |
| Android 麦克风 | ★★★★ pyjnius 直调 AudioRecord | ★☆ 无原生 API 访问 | ★★☆ 理论可行 |
| APK 打包 | ★★★★ Buildozer 成熟 | ★★★ 较新 | ★★★ Beta |
| 实时渲染性能 | ★★★★★ OpenGL ES + Cython | ★★☆ IPC 开销 | ★★☆ 无 GPU 管道 |

**结论**：Flet 的 Python→Flutter gRPC 通信在每帧更新数十个图形属性时会成为不可逾越的瓶颈；BeeWare 的 Canvas 缺少 GPU 加速和帧调度能力。Kivy 是唯一满足实时自定义渲染需求的选项。

### 依赖清单
- `kivy>=2.3.0`（SmoothRoundedRectangle 抗锯齿支持）
- `buildozer`（Android 打包）
- `pyjnius`（Android API 调用，Buildozer 自动包含）
- Python 3.10+

---

## 二、架构设计

### 2.1 线程模型

```
┌─ 主线程 (Kivy Event Loop) ──────────────────┐
│  Clock.schedule_interval(render, 1/60)       │
│  render():                                    │
│    1. 从 deque 快照读取振幅数据               │
│    2. 映射振幅 → bar 高度 (12dp~58dp)        │
│    3. 更新每根 bar 的 pos/size 属性           │
└──────────────────────────────────────────────┘
                ↑ collections.deque (线程安全 append/iter)
┌─ 音频采集线程 (threading.Thread, daemon) ────┐
│  loop:                                        │
│    AudioRecord.read(buf) → 计算 RMS 振幅      │
│    → 归一化 [0.0, 1.0]                        │
│    → deque.append(amplitude)                  │
└──────────────────────────────────────────────┘
```

主线程与音频线程通过 `deque` 松耦合，无需 Lock：
- CPython GIL 保证 `deque.append()` 和迭代操作的原子性
- `deque(maxlen=N)` 自动维护窗口大小

### 2.2 数据结构

```
WaveformBuffer:
  - amplitudes: deque(maxlen=MAX_BARS), float [0.0, 1.0]
  - MAX_BARS: 计算方式 = ceil(screen_width / (BAR_WIDTH + BAR_GAP)) + 2 (溢出缓冲)
  
  常量:
  - BAR_WIDTH = 4dp
  - BAR_GAP = 6dp  
  - BAR_MIN_HEIGHT = 12dp
  - BAR_MAX_HEIGHT = 58dp
  - BAR_RADIUS = 2dp (圆角半径 = 宽度/2，形成两端半圆)
```

### 2.3 渲染逻辑（核心）

**策略：指令属性更新，而非 clear+redraw**

初始化阶段（一次性）：
1. 计算屏幕可容纳的最大 bar 数量 `NUM_BARS`
2. 在 Canvas 上预创建 `NUM_BARS` 组 `(Color, RoundedRectangle)` 指令对
3. 存储所有 `RoundedRectangle` 引用到列表 `self.bar_instructions[]`

每帧更新（60fps）：
1. 将 `deque` 快照转为 list（`list(self.amplitudes)`）
2. 对每根 bar `i`（从右向左排列）:
   - `height = BAR_MIN_HEIGHT + amplitude * (BAR_MAX_HEIGHT - BAR_MIN_HEIGHT)`
   - `x = widget_right - (i+1) * (BAR_WIDTH + BAR_GAP)`
   - `y = widget_center_y - height / 2`（垂直居中）
   - 更新: `self.bar_instructions[i].pos = (x, y)`
   - 更新: `self.bar_instructions[i].size = (BAR_WIDTH, height)`
3. 超出 deque 数据的 bar 设置 `size=(0, 0)` 隐藏

**滚动效果实现**：
- 不需要真正"移动"任何对象
- 每次音频线程 `append()` 新振幅，deque 自动左移窗口
- 渲染帧读取 deque 最新状态，bars 的位置自然从右向左"推进"
- 新 bar 从右侧边缘出现，最老的 bar 从左侧消失

**平滑插值（关键丝滑感）：**
- 音频采样率（~20-30Hz）低于渲染帧率（60Hz）
- 在渲染帧之间对相邻振幅值做线性插值或指数平滑
- 使用 `current = current * 0.7 + target * 0.3` 的 EMA（指数移动平均）平滑高度变化
- 这消除了阶梯感，产生类似 iPhone 的"弹性"视觉效果

### 2.4 颜色方案

参考 iPhone 语音备忘录风格：
- 波形条颜色：白色 `(1, 1, 1, 1)` 或浅蓝色
- 背景色：深色 `(0.1, 0.1, 0.12, 1)` 或根据参考图调整
- 可在初始化时配置

---

## 三、Android 音频接入方案

### 3.1 权限配置

`buildozer.spec` 中添加：
```
android.permissions = RECORD_AUDIO
```

运行时动态权限请求（Android 6.0+）：
- 使用 `android.permissions` 模块（Kivy/p4a 内置）
- `request_permissions([Permission.RECORD_AUDIO])` + 回调

### 3.2 AudioRecord 接入（pyjnius）

音频采集线程核心流程：
1. `autoclass('android.media.AudioRecord')` 获取 Java 类
2. 配置参数：44100Hz, MONO, PCM_16BIT
3. `getMinBufferSize()` 计算最小缓冲区
4. `recorder.startRecording()` 开始采集
5. 循环 `recorder.read(short_array, 0, chunk_size)` 读取 PCM 数据
6. 计算 RMS：`sqrt(mean(samples^2))` → 归一化到 [0.0, 1.0]
7. `deque.append(normalized_rms)`

### 3.3 RMS 计算

```
chunk_size = SAMPLE_RATE / TARGET_WAVEFORM_FPS  
(44100 / 25 ≈ 1764 samples per chunk → 一次 read 产生一个振幅值)

rms = sqrt(sum(sample^2 for sample in chunk) / len(chunk))
normalized = min(rms / MAX_EXPECTED_RMS, 1.0)
```

TARGET_WAVEFORM_FPS = 25（每秒生成 25 个新 bar，视觉上接近 iPhone 的速度）

---

## 四、Mock 数据驱动模式

### 4.1 设计

定义 `AudioSource` 抽象接口（Protocol）：
- `start()` — 开始产生数据
- `stop()` — 停止
- `get_buffer() -> deque` — 返回振幅 deque 引用

两个实现：
1. **`MicrophoneSource`** — 真实 AudioRecord 采集（Android 专用）
2. **`MockSource`** — 模拟数据（全平台可用）

### 4.2 Mock 数据生成策略

```
MockSource (在独立线程中运行):
  t = 0
  loop (每 1/25 秒):
    base = 0.3 + 0.25 * sin(2π * 0.5 * t)       # 0.5Hz 慢呼吸波
    detail = 0.15 * sin(2π * 3.0 * t)             # 3Hz 细节波动  
    noise = uniform(-0.1, 0.1)                      # 随机噪声
    amplitude = clamp(base + detail + noise, 0.0, 1.0)
    deque.append(amplitude)
    t += 1/25
```

这产生的波形视觉上接近真实语音：有缓慢的"说话/停顿"节奏，也有快速的细节变化。

### 4.3 模式切换

通过启动参数或配置切换：
- 检测平台：`kivy.utils.platform == 'android'` → MicrophoneSource
- 非 Android 或指定 `--mock` → MockSource
- 所有渲染逻辑完全共享，只替换数据源

---

## 五、项目结构

```
volume_demo/
├── main.py                  # App 入口，初始化 Kivy App
├── waveform/
│   ├── __init__.py
│   ├── widget.py            # WaveformWidget — 核心渲染组件 (Kivy Widget)
│   ├── audio_source.py      # AudioSource Protocol + MicrophoneSource + MockSource
│   └── constants.py         # BAR_WIDTH, BAR_GAP, MIN/MAX_HEIGHT 等常量
├── buildozer.spec           # Android 打包配置
├── volume.webp              # 参考图（已有）
└── requirements.txt         # kivy>=2.3.0
```

---

## 六、分步实施计划 (Milestones)

### Phase 1: 基础骨架 + Mock 静态验证（桌面端）
**目标：在 PC 桌面上看到静态的波形条**

1. **Step 1.1** — 初始化项目结构，创建 `constants.py` 定义所有设计常量
2. **Step 1.2** — 实现 `WaveformWidget(Widget)` 基类：预创建 Canvas 指令，硬编码一组测试数据，渲染出静态波形条
3. **Step 1.3** — 验证：桌面运行 `python main.py`，确认看到居中的圆角矩形条阵列，高度各异

### Phase 2: Mock 数据 + 滚动动画（桌面端）
**目标：在 PC 桌面上看到丝滑的左滚波形动画**

4. **Step 2.1** — 实现 `MockSource`：正弦波 + 噪声数据生成，独立线程，输出到 deque
5. **Step 2.2** — 实现 `WaveformWidget.update()` 方法：`Clock.schedule_interval(self.update, 1/60)` 驱动，从 deque 读取数据更新 bar 指令属性
6. **Step 2.3** — 实现指数平滑插值（EMA），消除阶梯感
7. **Step 2.4** — 验证：桌面运行，确认波形从右向左平滑滚动，无卡顿，新 bar 从右侧实时生成

### Phase 3: Android 音频接入
**目标：真机上用麦克风驱动波形**

8. **Step 3.1** — 实现 `MicrophoneSource`：pyjnius 调用 AudioRecord，PCM→RMS→归一化→deque
9. **Step 3.2** — 实现运行时权限请求 `RECORD_AUDIO`
10. **Step 3.3** — 实现平台检测自动切换数据源（Android→Mic, 其他→Mock）
11. **Step 3.4** — 验证：通过 Buildozer 打包 APK，真机安装测试

### Phase 4: 打磨与优化
**目标：达到接近 iPhone 语音备忘录的视觉和交互质量**

12. **Step 4.1** — 调色：根据 volume.webp 参考图微调颜色、透明度、背景
13. **Step 4.2** — 调参：调整 EMA 系数、BAR_MIN/MAX_HEIGHT、波形生成速率，使视觉节奏更自然
14. **Step 4.3** — 性能测试：Profile 渲染帧率，确保稳定 60fps
15. **Step 4.4** — 添加录音状态控制 UI（开始/停止按钮）

### 步骤依赖关系
- Phase 1 → Phase 2 → Phase 4（串行）
- Phase 3 可与 Phase 2 完成后并行于 Phase 4

---

## 七、关键文件清单

| 文件 | 作用 | 核心函数/类 |
|---|---|---|
| `main.py` | App 入口 | `WaveformApp(App).build()` |
| `waveform/widget.py` | 渲染组件 | `WaveformWidget(Widget).__init__()`, `.update(dt)`, `._create_bar_instructions()` |
| `waveform/audio_source.py` | 数据源 | `AudioSource(Protocol)`, `MockSource`, `MicrophoneSource` |
| `waveform/constants.py` | 设计常量 | `BAR_WIDTH`, `BAR_GAP`, `BAR_MIN_HEIGHT`, `BAR_MAX_HEIGHT`, `BAR_RADIUS`, `WAVEFORM_FPS` |
| `buildozer.spec` | 打包配置 | `android.permissions = RECORD_AUDIO` |

---

## 八、验证方案

1. **Phase 1 验证**：`python main.py` → 目测静态波形条：圆角、宽度 4dp、间距 6dp、高度各异、垂直居中 ✓
2. **Phase 2 验证**：`python main.py` → 目测动画：波形从右向左平滑滚动、右侧实时生成新 bar、无卡顿、有呼吸感节奏 ✓
3. **Phase 2 性能验证**：使用 Kivy Inspector 或 `Clock.get_fps()` 输出帧率，确认稳定 ≥55fps ✓
4. **Phase 3 验证**：真机安装 APK → 授权麦克风 → 对着手机说话 → 波形实时响应音量变化 ✓
5. **Mock 模式验证**：在 Android 上传入 `--mock` 参数或拒绝麦克风权限时，自动降级为 Mock 数据源，动画正常 ✓

---

## 九、设计决策记录

| 决策 | 选择 | 理由 |
|---|---|---|
| 框架 | Kivy | 唯一满足实时自定义渲染 + Android 音频访问的 Python 框架 |
| 渲染策略 | 指令属性更新 | 比 clear+redraw 高效一个数量级，避免 GL 对象重建 |
| 数据结构 | deque(maxlen) | O(1) 两端操作，自动窗口维护，线程安全 |
| 线程通信 | 无锁 deque | CPython GIL 保证原子性，避免 Lock 开销和死锁风险 |
| 平滑方案 | EMA 指数平滑 | 简单高效，一行代码，效果接近物理弹性 |
| 音频参数 | 44100Hz/Mono/16bit | Android 兼容性最广的配置 |
| 波形生成速率 | 25 bars/sec | 接近 iPhone 语音备忘录的视觉节奏 |

## 十、范围边界

**包含：**
- 仿 iPhone 语音备忘录波形滚动组件
- Mock 数据驱动模式（桌面可运行）
- Android 真机麦克风接入
- 基础录音状态控制

**排除：**
- 录音文件存储/回放功能
- iOS 平台适配
- 录音波形的回看/缩放交互
- 多种主题/配色切换

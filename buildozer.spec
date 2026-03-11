[app]
# Placeholder Buildozer config used as a starting point for Android packaging.
title = WaveformDemo
package.name = waveformdemo
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,webp
version = 0.1.0
requirements = python3,kivy,pyjnius
orientation = portrait
fullscreen = 1
android.permissions = RECORD_AUDIO

[buildozer]
log_level = 2
warn_on_root = 1

> 当前整合与验收状态见 [项目比对](docs/APP_COMPARISON.md)，操作说明见 [使用说明](docs/USER_GUIDE.md)。下文保留原始导入说明；不作为最新交付状态。

# StrideLab · 运动数据模拟实验室

当前工程归档：Android V0.1 + synthetic-running-data Skill V2.0。

## 项目入口
- `skills/synthetic-running-data/`：当前独立 Skill，优先使用；见其中 SKILL.md 和 README.md。
- `app/`：现有 Android WebView 工程（未完成 APK 编译）。
- `StrideLab_v0.1.html`：浏览器原型。
- `PRD.md`：历史产品需求基准。
- `design/`：图标及运行界面截图。
- `docs/ANDROID_V0.1_STATUS.md`：原 Android 说明及未完成事项。
- `.github/workflows/android.yml`：原有 Android 构建工作流，未在此归档中触发。

## Skill 使用
```bash
cd skills/synthetic-running-data
python scripts/test_skill.py
python scripts/generate.py --config example_config.json --output ./generated
```

## Android
原工程需要 JDK 17、Android SDK 35、Gradle 8.9。当前仅归档源码，不包含 APK。具体构建命令及限制见 docs/ANDROID_V0.1_STATUS.md。

## 数据用途
合成研究数据仅用于学习交流、教学、统计分析及授权测试，不可用于真实评测。真实地理参考和合成运动数据分开管理；FIT/TCX 为独立格式测试夹具。

## 归档范围
保留当前两个版本的源代码、设计、测试及配置；不包含此前产生的个人定位截图、历史批量运动记录或账号信息。归档未改变算法或进行新的实机验收。

# StrideLab Skill V2.0
不依赖Android。阅读 SKILL.md，直接使用 Python 3.10+ 执行；无需安装第三方包。

- `python scripts/generate.py --output ./generated` 默认生成
- `python scripts/generate.py --config example_config.json --output ./experiment` 自定义生成
- `python scripts/generate.py --config ./experiment/replay_config.json --only group_01_run_001 --revision 1 --output ./revision` 单条独立变体
- `python scripts/format_fixture.py --output ./fixture` 固定 FIT/TCX 格式测试样本
- `python scripts/test_skill.py` 回归测试

相较V1.1，新增有序多点、开放路径、固定/随机起点、方向、速度CV、疲劳情景、加减速开关、分组档案、指标选择、时长联动、独立种子、实际预览、重放和校验。默认研究格式改为CSV/JSON；FIT/TCX仅作独立短距离格式夹具。地图SDK交互、在线坐标转换、约束曲线拟合、真实设备校准及外部导入未完成，不算已验收。历史PRD附于references作为需求基准。

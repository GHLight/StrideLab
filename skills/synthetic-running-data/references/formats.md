# 数据协议与验证

研究输出：CSV逐秒样本（理想/观测局部x、y；理论/观测距离；速度及选定指标）、JSON会话和逐点数据、每组 summary.csv、manifest.json、实际数据预览SVG、每组ZIP和总ZIP。总清单含原始参数、replay_config.json（填入实际种子）、参考几何及各归档SHA256。WGS84参考点单独保存为 route_reference.geojson，不是运动记录。CSV的source以及JSON的synthetic保持来源标记。

固定格式夹具：`scripts/format_fixture.py` 生成50m/30s的无GPS FIT与TCX示例，保留合成来源标识；仅用于解析器测试，不读取真实场地或研究时间配置。FIT内部校验文件头、CRC、消息结构、必要消息和时间戳；TCX内部验证XML及采样点数量。FIT cadence表示周期数，CSV步频是步/分钟，两者不能混用。尚未经过 Garmin SDK、TCX官方XSD或任何第三方App实机验证。

参考规范（沿用V1.1所列链接，本轮未重新联网核实）：
- https://developer.garmin.com/fit/protocol/
- https://developer.garmin.com/fit/file-types/activity/
- https://www8.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd

所有包自动附 UTF-8 用途声明.txt。模拟数据不用于真实评测或作为人体实测证据。

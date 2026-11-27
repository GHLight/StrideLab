# V2.0 参数说明
JSON 键名区分大小写。null 或省略采用默认值（可空字段不强制填充）。

| 键 | 默认与约束 |
|---|---|
| groups | 1，1–30组 |
| runs_per_group | 5，整数或每组整数列表；每组1–200，总计不超过500 |
| count_range | 可选整数区间，与 runs_per_group 二选一 |
| distance_m | 2000，50–50000米，数字或[min,max] |
| pace_min_km | 6.0，2–30分钟/公里；6:30写6.5 |
| duration_s | 可选整数或区间；与 pace_min_km 二选一，程序计算第三量 |
| start_date | 2030-01-01，示例时间轴，ISO日期 |
| day_gap | [1,3]，整数天；固定值也可 |
| time_window | ["08:00","18:00"]，同日HH:MM，不跨午夜 |
| utc_offset_hours | 8，固定时差（不处理夏令时） |
| sample_seconds | 1，整数1–30秒，最后采样间隔可短于设置值 |
| track_length_m | 400，100–2000m，标称值；用户路线不自动缩放 |
| route_nodes | null；按路径顺序输入2–1000（开放）或3–1000（闭合）个点 |
| boundary_points | null；north/south/west/east 四点，与 route_nodes 二选一 |
| coordinate_system | WGS84（纬度、经度）或 LOCAL_M（x、y米）；有点时必填 |
| closed | true，闭合或开放 |
| random_start | true；开放路线必须false |
| fixed_start_m | 0，沿闭合路线从第一节点起的弧长；开放路线必须0 |
| direction | forward / reverse / random；开放路线对应端点 |
| speed_cv_pct | 5，0–20，随机速度变化目标 |
| gps_noise_m | 1.5，0–30m，长期二维观测误差RMS目标 |
| noise_correlation_s | 6，0.1–120秒，误差相关时间 |
| fatigue | none / normal / high，默认normal |
| scenario | steady / progressive_slowdown / interval，默认steady |
| start_acceleration / end_deceleration | true / true |
| profile_mode | shared / per_group，默认shared |
| resting_hr_bpm / max_hr_bpm / cadence_spm | 65 / 190 / 165，模型参数非医学预测 |
| profiles | null或对象列表，shared为1项，per_group为每组1项；可覆盖上面三个指标 |
| metrics | heart_rate、steps、cadence、step_length、ground_contact、vertical_oscillation 的任意子集 |
| seed | null时随机生成整数并记录实际值 |
| formats | ["csv","json"]，可选其中一个或全部；FIT/TCX用独立夹具命令 |

示例：开放的局部参考线 `{"route_nodes":[[0,0],[100,0],[100,100]],"coordinate_system":"LOCAL_M","closed":false,"random_start":false,"distance_m":200}`。闭合路径输入按顺序排列的节点，首尾会自动连接，重复的闭合末点会移除，连续重合点会报错。四点快捷模式按北东南西连接，非精确椭圆/跑道测绘；需要曲线细节时使用更多节点。默认标准虚拟环形采用高密度离散半圆。所有几何计算在局部米制平面进行，WGS84参考使用小范围等距近似，非大范围测地工具。地图选点、地址搜索、图形拖拽不是该命令行Skill的功能。

实际速度CV取20%–80%时段，模型噪声及疲劳趋势都影响结果。目标参数不是保证；0%随机速度噪声不意味着启用疲劳后完全匀速。距离与时长可能因整数秒舍入产生小配速差。速度阶段和心率滞后模型是教学示例，触地时间、垂直振幅未实测校准。误差目标不等于实测 RMS 或最大误差；高误差下逐点观测累计距离可能明显增长，不应把它当真实运动距离。

总样本预算200万点，单条最多8万点；资源约束为静态保护阈值，不是移动设备压测结论。跨日运动可由时间轴延续，但每日起跑时段不能跨午夜。

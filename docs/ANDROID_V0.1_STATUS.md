> 历史记录：此文描述最初归档状态。最新实现和实际验证边界见 [APP_COMPARISON.md](APP_COMPARISON.md)。

# StrideLab v0.1.0 — integrated development build

## 运行方式
- 浏览器：打开 `StrideLab_v0.1.html`，本地运行研究模拟；在线地图需网络，浏览器定位需安全上下文及权限。
- Android：Android Studio 打开工程目录，JDK 17、Android SDK 35、Gradle 8.9、AGP 8.7.3。当前为 Android WebView 实现，未迁移到 Compose。
- 自动构建：项目包含 `.github/workflows/android.yml`。将工程放入 GitHub 仓库，Actions 中运行 `Build Android test APK`，成功后下载 `StrideLab-debug-apk` 构建产物。未在本环境触发远程构建。
- 本地构建命令：`gradle --no-daemon :app:assembleDebug :app:lintDebug`。成功时 APK 位于 `app/build/outputs/apk/debug/app-debug.apk`。

## 本版内容
- 新低饱和配色、矢量应用图标、统一导航、表单开关、使用说明。
- OpenStreetMap 在线参考图：显式启用、按坐标跳转、地图拖动/缩放、中心准星、任意数量节点（最多120）、移动至准星、删除、反转、撤销最后添加点、闭合/开放测距及保存参考点；Android 原生前台定位权限桥。地图参考 GeoJSON 与局部运动模拟保持独立。
- 局部模拟路线编辑、样本批量生成、起点和方向、运动速度波动、疲劳、传感器误差、模拟生理指标、统计图、配置/汇总/单条和整批研究数据导出及用途声明。
- Android 系统文件选择器保存数据；不接管系统 GPS，不自动提交第三方运动成绩。

## 实际测试
`node tests/core.test.js`：通过。
`python tests/browser_test.py`：通过，手机尺寸 Chromium 测试、路线编辑、模拟、ZIP 验证、草稿恢复（模拟 localStorage）。
`python tests/map_test.py`：通过，地图瓦片由测试脚本替代，验证参考点、测距、删除、反转、GeoJSON 和说明弹窗，未验证真实联网。
APK 构建尝试失败：当前没有 Gradle 和 Android SDK，Google 下载域名 DNS 失败。未生成 APK、未执行 Android lint、未安装或真机验收。

## 限制和待完成项
在线底图仅为参考（普通地图，不是卫星图）；没有地址搜索、真实联网测试和地图服务生产配额/许可验收，正式发布前需要确定生产级地图服务。当前 OSM 仅按用户可见区域加载，不做离线瓦片批量下载。Android 定位桥和保存桥已编写但未实机验证；位置权限按需请求。仍需实现跨组项目、结果持久化、单条重算、日期实验调度、路径自由手绘、完整备份/恢复、FIT/TCX 专用测试夹具与第三方独立兼容性验证。模拟数据为局部米制坐标和相对时间，使用 CSV/JSON/ZIP 研究格式。生理模型未用人体实测数据校准；速度波动为名义输入，不保证目标 CV 精确达成。所有模拟数据仅供学习交流、教学和授权测试，不可用于真实评测。

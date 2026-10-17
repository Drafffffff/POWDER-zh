# POWDER 1.18 中文测试版

最新可运行文件：`output/powder118_zh_movement_sync.gba`。它包含当前全部译文和新的行动菜单。旧的 `*_demo.gba` 是早期三个字的演示，不是本次版本。

行动菜单采用原生 10px 点阵，紧凑字距，透明背景和黑色描边；每页七项，黄色箭头标记选中项。告示牌及帮助正文为 11px 有效字形，原版卷轴背景不变，每行 13px、最多八行。菜单和卷轴底部按键提示为 9px。设置等其他窗口沿用现有布局。

操作：Start 打开行动菜单；上下选择，左右翻页，A 执行，B 返回。Select 打开背包。L/R 保留原有行动绑定用途。

## 文件

- `output/powder118_zh_stable.gba`：可直接用 GBA 模拟器打开。
- `output/powder118_zh_stable.bps`：对应原版 `original/powder118.gba` 的补丁，已验证应用后逐字节一致。
- `output/powder118_zh_stable.json`：ROM 哈希、验证记录、范围。
- `output/powder118_zh_stable.png`：真实模拟器截图，三倍最近邻放大。
- `translations/`：3092 条去重翻译映射；游戏数据、消息、界面、帮助及补充文本。

原 ROM 保持不变。字体许可和来源见 `assets/fonts/`；游戏原有许可见 `source/`。本地测试产物尚未做完整通关与旧版本存档兼容测试。

## 构建与检查

已配置项目本地 GCC/libgba 工具链；以下命令在上级工作区目录执行。prepare 会重新生成暂存源码，不修改 `source/`。

```sh
python3 POWDER/tools/prepare_zh.py
python3 POWDER/tools/engine_zh.py
python3 POWDER/tools/menu_zh.py
python3 POWDER/tools/stability_zh.py
python3 POWDER/tools/movement_zh.py
python3 POWDER/tools/build_gba.py POWDER/build/zh_src
python3 POWDER/tools/validate_zh_build.py
python3 POWDER/tools/check_menu_runtime.py POWDER/build/gba_zh_src/powder.gba --core POWDER/tools/runtime/mgba_libretro.dylib --out POWDER/analysis/runtime/stable_final --scenario game
python3 POWDER/tools/package_zh.py
```

自动验证包含格式占位符、数据文本覆盖、UTF-8 边界与缓冲区检查，像素宽度换行与 9px 字形边界，以及 mGBA 中五页行动菜单均可访问、取消菜单后全画面逐像素恢复、保存重启后地图逐像素一致。界面截图覆盖背包、帮助、字体和图块切换；验证记录在 `analysis/zh_validation.json` 与 `analysis/runtime/stable_final/checks.json`。

告示牌运行截图在 `analysis/runtime/stable_tutorial/`；可重现步骤：

```sh
python3 POWDER/tools/check_menu_runtime.py POWDER/build/gba_zh_src/powder.gba --core POWDER/tools/runtime/mgba_libretro.dylib --out POWDER/analysis/runtime/stable_tutorial --scenario tutorial
```

`tools/menu_zh.py` 会生成字形并应用 `tools/ui_zh_overlay.inc`。卷轴阅读时临时使用位图显示，退出后恢复覆盖的 VRAM 和显示寄存器，游戏图块缓存保持完整。旧版 `readable_menu` 和 `compact_menu` 输出仍保留，方便对比。

## 切换稳定性修复

`output/powder118_zh_stable.gba` 是本次普通游戏版本；不会自动探索，也没有启用压力测试开关。

- 卷轴改用 Mode 4 双缓冲：先在 RAM 绘制，再在 VBlank 向后台页传输并翻页，退出时分区恢复显存。
- 行动菜单先生成完整图块和映射，再合并连续图块、在 VBlank 提交；避免显示期间回收和覆写图块。
- 地图、字体及图块集刷新采用 RAM 暂存，仅提交变化的图块与地图行；相邻行先合并成传输区间。
- 原 NO_HAM 的等待事件函数现在等待 VBlank；图块传输改用 DMA。
- 彩色字符保留原字符与颜色元数据，切换字体/图块集时重新生成，避免把虚拟颜色槽当作字母索引加载。

验证报告：`analysis/stability_validation.json`。在 mGBA 0.10.5 中连续切换行动菜单与卷轴各 30 轮，测试窗口内白屏中间帧由旧版的 92 帧降为 0 帧；两次测试窗口长度不同，新版包含额外重复切换。普通界面测试完成 268 次显存提交，测试专用构建在 60,000 帧自动探索中重建了 15 次场景，完成 4,161 次提交；均未检测到提交超出 VBlank。菜单退出恢复、保存读取地图一致性、UTF-8 缓冲区、字形边界和 BPS 补丁往返验证通过。

启动/加载时原有短暂黑色过渡仍可能出现；本次未做完整通关或实机测试。

以下额外命令用于重现压力测试，测试 ROM 只写入 `build/gba_zh_src_stress/`，不会替换普通游戏构建。

```sh
python3 POWDER/tools/check_menu_runtime.py POWDER/output/powder118_zh_compact_menu.gba --core POWDER/tools/runtime/mgba_libretro.dylib --out POWDER/analysis/runtime/baseline_final --scenario game --trace
python3 POWDER/tools/check_menu_runtime.py POWDER/build/gba_zh_src/powder.gba --core POWDER/tools/runtime/mgba_libretro.dylib --out POWDER/analysis/runtime/stable_final --scenario game --trace --stress 30
POWDER_STRESS_BUILD=1 python3 POWDER/tools/build_gba.py POWDER/build/zh_src
python3 POWDER/tools/check_menu_runtime.py POWDER/build/gba_zh_src_stress/powder.gba --core POWDER/tools/runtime/mgba_libretro.dylib --out POWDER/analysis/runtime/world_stress_final --scenario world --world-frames 60000 --trace
python3 POWDER/tools/check_stability_report.py
python3 POWDER/tools/package_zh.py
```

`--trace` 记录每帧哈希和纯色帧，并保存最多 1,000 张不同画面及纯色画面。`renderer_timing.json` 使用 ELF 符号和核心内存映射读取提交次数与超时次数，普通 ROM 中的计数器不会出现在游戏界面。


## 响应速度优化版

最新文件为 `output/powder118_zh_smooth.gba`，对应 BPS 补丁和验证清单使用同名文件。上一版 `powder118_zh_stable.gba` 保留用于对照。

- 已收到当前帧中断时，输入轮询直接处理，避免再次等待下一帧；画面提交仍等待完整 VBlank。
- 菜单同页移动只重画前后两个选项；描边用位运算生成，图块通过哈希去重并校验相等，空闲图块一次扫描。
- 菜单和卷轴的四个绘制热点移入 IWRAM，合计增加约 2.2KiB；按链接映射仍留出约 9KiB 至用户栈顶。
- 卷轴背景按纹理片段复制，字形每行掩码只读取一次；显存备份和地图暂存用 DMA 复制。
- 菜单 10px、正文 11px、提示 9px 不变；12 张界面及存档读取截图与上一版逐像素相同。

mGBA 中相同输入序列的完整画面响应：菜单上下 13→3 帧、左右翻页 12–13→4 帧、卷轴滚动 35–36→5 帧、打开菜单 13→4 帧。教程左右行走为 9→9 与 13→11 帧，复杂回合计算仍可能有停顿；这些数值不是整场游戏帧率或实机测量。

验证记录：`analysis/performance_validation.json`、`analysis/smooth_stability_validation.json`。构建仍按上文 prepare → engine → menu → stability → build 顺序执行，之后：

```sh
python3 POWDER/tools/validate_zh_build.py
python3 POWDER/tools/check_menu_runtime.py POWDER/output/powder118_zh_stable.gba --core POWDER/tools/runtime/mgba_libretro.dylib --out POWDER/analysis/runtime/latency_before --scenario game --trace --latency
python3 POWDER/tools/check_menu_runtime.py POWDER/output/powder118_zh_stable.gba --core POWDER/tools/runtime/mgba_libretro.dylib --out POWDER/analysis/runtime/latency_tutorial_before --scenario tutorial --trace --latency
python3 POWDER/tools/check_menu_runtime.py POWDER/build/gba_zh_src/powder.gba --core POWDER/tools/runtime/mgba_libretro.dylib --out POWDER/analysis/runtime/smooth_final --scenario game --trace --latency --stress 30
python3 POWDER/tools/check_menu_runtime.py POWDER/build/gba_zh_src/powder.gba --core POWDER/tools/runtime/mgba_libretro.dylib --out POWDER/analysis/runtime/smooth_tutorial --scenario tutorial --trace --latency
POWDER_STRESS_BUILD=1 python3 POWDER/tools/build_gba.py POWDER/build/zh_src
python3 POWDER/tools/check_menu_runtime.py POWDER/build/gba_zh_src_stress/powder.gba --core POWDER/tools/runtime/mgba_libretro.dylib --out POWDER/analysis/runtime/smooth_world --scenario world --world-frames 60000 --trace
python3 POWDER/tools/check_stability_report.py --prefix smooth
python3 POWDER/tools/check_performance.py
python3 POWDER/tools/package_zh.py --prefix smooth
```


## 物品操作菜单 9px

`output/powder118_zh_inventory9.gba` 保留响应速度优化，并把物品栏中 A 键打开的阅读、装备、丢弃等操作菜单从 8px 调整为 9px。每页八项、行距 13px，左右翻页，上下选择，A 执行、B 返回。物品名称、装备槽标签、主行动菜单及告示牌字号不变。

截图为 `output/powder118_zh_inventory9_inventory.png`。运行检查新增 `--inventory-checks`，验证物品菜单翻页、选择重绘、取消后完整恢复物品栏。以 `inventory9` 为 prefix 运行界面/教程/场景压力检查、稳定性报告和打包脚本，可复现此版本。


## 紧凑物品菜单

最新 `output/powder118_zh_inventory_compact.gba` 保持 9px 字号，将行距从 13px 收紧为 10px，每页从八项增加到十一项；普通物品操作列表可同页显示，单页时隐藏页码。9px 字形的相邻行共用黑色描边间隔；该菜单选择变化时完整重绘以免局部清除影响相邻描边，仍沿用 IWRAM 绘制和 VBlank 整体提交。底部提示保留 9px。

通过物品菜单导航、取消后物品栏恢复、其他菜单切换、存档读写、五轮反复切换和纯色帧/提交超时检查。报告：`analysis/inventory_compact_stability_validation.json`，本次为界面验证，未重复世界压力测试。打包前使用 `check_stability_report.py --prefix inventory_compact --ui-only` 和 `package_zh.py --prefix inventory_compact`。


## 紧凑 Start 菜单

`output/powder118_zh_compact_menus.gba` 将 Start 行动菜单行距由 15px 收紧至 12px，每页七项改为九项，总共四页，字号保持 10px。物品菜单维持 9px、10px 行距、每页十一项；正文与底部提示维持原字号。

本版通过四页导航、选择重绘、取消恢复、物品菜单导航、存档往返及五轮界面切换检查；未重复世界压力测试。模拟器响应保持上下选择 3 帧、翻页 4 帧，未检测到白色中间帧和显存提交超时。报告在 `analysis/compact_menus_stability_validation.json` 和 `analysis/runtime/compact_menus_final/input_latency.json`。

运行 `check_menu_runtime.py` 的 game 场景时加 `--action-pages 4 --inventory-checks --latency --trace --stress 5`，输出 prefix 为 `compact_menus`；后续执行 `check_stability_report.py --prefix compact_menus --ui-only` 和 `package_zh.py --prefix compact_menus`。


## 告示牌正文 10px

最新 `output/powder118_zh_reader10.gba` 将共用卷轴阅读器（告示牌及帮助正文）调整为与 Start 菜单一致的原生 10px 点阵字形，12px 行距、九行可见正文；底部提示保持 9px。换行按新的 10px 中文/5px ASCII 字距重新计算，L/R 每次滚动九行，末页边界和页码同步调整。Start 及物品菜单逐像素保持上一版样式。

验证通过 UTF-8/换行缓冲边界、四页 Start 导航、物品栏操作、存档往返、五轮界面反复切换；无白屏中间帧或显存提交超时，本次未重复世界压力测试。报告在 `analysis/reader10_stability_validation.json`，截图为 `output/powder118_zh_reader10_signpost.png`。构建及检查命令沿用 compact_menus 的参数，prefix 改为 reader10。


## Start 菜单上移

`output/powder118_zh_menus_up.gba` 把 Start 菜单整体上移 8px，首项文字顶端从屏幕 y=24 调整到 y=16；字号 10px、行距 12px、每页九项不变。背景保存、提交和退出恢复均使用新的面板位置；物品菜单、告示牌和其他界面不变。

通过四页导航、取消恢复、存档往返及五轮界面切换；本次为界面检查，未重复世界压力测试。报告位于 `analysis/menus_up_stability_validation.json`。构建与 UI 检查使用 reader10 同样参数，prefix 改为 menus_up。


## 对齐首项、缩小提示、按类分页

最新 `output/powder118_zh_grouped.gba` 将 Start 首项与页码统一放在屏幕 y=9，正文仍为 10px，行距 11px。面板为 112×136px，底部使用原生 Fusion Pixel 8px 提示；每页最多十一项。物品菜单保留 9px 和现有紧凑排版，告示牌保持 10px。

29 个动作按三页重排，原动作 ID 和标签/快捷键绑定同步生成，不改变存档中的动作 ID：

- 探索移动（11）：攀爬、搜索、查看、拾取、打开、关闭、移动、安全行走、奔跑、跳跃、小地图。
- 战斗与物品（9）：射击、使用魔杖、吐息、使用、食用、交换、释放、指挥、物品栏。
- 休息与系统（9）：等待、睡眠、祈祷、遗忘、命名、消息历史、指令菜单、许愿、设置。

左右翻页尽量保留行位置；目标页较短时落在最后一项，上下可连续跨页及首尾循环。紧凑行相邻描边在局部重绘时一起恢复，页码随后重绘，避免选中首项时擦掉数字。

检查覆盖 29 个不同选择画面、整圈首尾恢复、三页导航、物品操作、字体/图块切换、存档往返和五轮界面切换；模拟器中上下选择 3 帧、翻页 4 帧，无白色中间帧或提交超时。本次为界面验证，未重复世界压力测试。结果见 `analysis/grouped_stability_validation.json` 和 `analysis/runtime/grouped_final/`。截图为输出同名 PNG、`_page2.png`、`_page3.png`。

game 场景运行参数：`--action-pages 3 --grouped-actions --inventory-checks --latency --trace --stress 5`；教程参数不变，输出 prefix 为 grouped。执行 `check_stability_report.py --prefix grouped --ui-only` 和 `package_zh.py --prefix grouped` 打包。


## 地图移动响应优化（2026-10-12）

`output/powder118_zh_movement.gba` 保留 grouped 的排版、字体、29个动作分组与全部译文。实查 RG34XX「汉化测试」目录中的旧 ROM 哈希与 grouped 完全一致，故以该文件作性能基线。

- 对单步移动计时后，将地图刷新及四个高频图块写入函数放入独立 IWRAM 代码段，使用局部 O2 编译。
- 遍历地图时先比较现有图块，仅在变化时进入原有图块锁定和写入流程，避免每步对未变化格子调用约三千次 setter。
- 回合顺序、怪物 AI、视野判定、按键重复间隔、存档格式均不改变；布局沿用 grouped。
- 链接映射中 IWRAM 静态区末端至用户栈顶留出 6756 字节；这不是最大栈占用的认证。

相同教程输入的完成画面响应由 9/11 帧降至 6/8 帧，按60Hz折算从150/183ms降到100/133ms，每步少约50ms。单独计时构建的地图刷新由1098/1034扫描线降至415/350扫描线。教程七张截图逐像素相同；菜单响应保持原水平。数值来自 mGBA 0.10.5 的两个确定性教程样本，并非 RG34XX 实测延迟或整场游戏提速保证。

验证通过译文/UTF-8检查、29个动作、物品菜单、取消恢复、保存读取、五轮菜单/卷轴切换；60000帧世界压力测试重建19次场景，5810次显存提交未发现超出VBlank，UI测试未发现白色中间帧。报告为 `analysis/movement_performance.json` 和 `analysis/movement_stability_validation.json`。

完整构建顺序：prepare → engine → menu → stability → movement → build。界面验证使用 grouped 的三个动作页参数，输出目录为 `movement_final`；教程为 `movement_tutorial`，压力测试为 `movement_world`，再执行 `check_stability_report.py --prefix movement`、`package_zh.py --prefix movement`。

RG34XX 按用户要求直接替换 `汉化测试/powder118_zh_grouped.gba`，保持原菜单入口「powder118_zh」，移除独立移动优化测试入口；原有存档未改动。部署回读哈希见 `analysis/device/powder_movement_deployment.json`。旧版即时存档不应跨ROM加载；本次没有改动设备现有即时存档或电池存档。


## 修复镜头与人物分步移动（2026-10-12）

移动优化首版仍在回合计算开始前直接修改背景滚动寄存器；地图和人物图块则在回合末尾 VBlank 提交。这造成地图先移动、人物随后回到中心的中间画面。此前的最终画面一致性及响应耗时检查没有覆盖这一问题。

`movement_zh.py` 现在将 main.cpp/action.cpp 中世界移动、楼梯和读档的镜头坐标暂存，在同一次地图提交的 VBlank 中写入背景滚动寄存器。查看/瞄准界面的镜头调用保持即时更新。

`check_movement_sync.py` 重放两次教程左右移动，对比每帧地图区域与移动前后画面：旧版可复现中间画面，修复版两次均只有移动前后状态。最终七张教程截图相同，响应仍为6/8帧；29动作、物品菜单、存档往返、五轮界面切换和60000帧世界压力检查通过，未发现显存提交超出VBlank。该验证来自mGBA，掌机手感仍需实际游玩确认。

输出 `output/powder118_zh_movement_sync.gba` 及同名BPS补丁。设备直接替换原 `汉化测试/powder118_zh_grouped.gba`，菜单入口和现有存档未改动，回读哈希见 `analysis/device/powder_movement_sync_deployment.json`。需重新启动ROM，不应继续旧版本即时存档。验证/打包prefix为 `movement_sync`。

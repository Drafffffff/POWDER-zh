# POWDER 1.18 汉化逆向记录

目标 ROM：`original/powder118.gba`

- SHA-256：`20bf244560265e8215ea9df2d23c3c85a93bb49f1a91010a230d0d125cc3b654`
- GBA 标题：`POWDER118`
- 源码：`source/`（已复制到项目内，来源为 POWDER 1.18 源码包）

## 已确认

1. ROM 的主要游戏文本位于文件偏移 `0x1FF000..0x229800`，是 ASCII、NUL 结尾字符串；当前提取到约 3200 条候选文本。
2. 典型入口：`Welcome to POWDER!` 在 `0x20879C`，`Help` 在 `0x208ED8`，`New Game` 在 `0x21F47C`，`Really quit?` 在 `0x226C0C`。
3. 字符渲染是 8×8 tile，`glb_charidx[256]` 只缓存 256 个单字节字符；`gfx_getchartile()` 按 `glb_texttable[]` 给字符分配字形索引。源代码没有 UTF-8 解码器，也没有中文字体。
4. `source.txt` 只是数据定义的一部分；菜单、帮助和大量提示仍散落在 `main.cpp`、`gfxengine.cpp`、`msg.cpp` 等源码中。ROM 文本不能只靠 `source.txt` 全量覆盖。
5. 文本包含 POWDER 的语法：`%U`、`%MU`、`%IU`、`%R`、`%s` 以及 `<verb>` / `<I:be>` 等。翻译时必须原样保留这些占位符和动词标记，否则运行时语法替换会损坏。

## 当前可行路线

### 路线 A：源码重编译（推荐）

给 `gfxengine` 增加 UTF-8 解码或一个本地双字节编码层；扩展 `glb_texttable` / `glb_charidx` 与字库 BMP；修改文本换行宽度和 `strlen` 相关布局；再用 devkitARM + libgba 生成新 ROM。源码构建需要 `DEVKITARM`，当前环境没有检测到可用的 GBA 工具链，因此暂未伪造构建结果。

### 路线 B：ROM 直接补丁（仅适合短期验证）

等长或更短的 ASCII 替换可直接完成；更长翻译需要搬移字符串并修正引用指针。中文仍必须先增加字库和解码/映射代码，不能把 UTF-8 字节直接写入现有 ROM。

## 可复现工具

- `tools/extract_powder_text.py`：导出 ROM 字符串和源码 C/C++ 字面量，保留偏移与占位符。
- `tools/patch_ascii.py`：只允许 ASCII、等长或缩短替换，拒绝多匹配和扩容，避免误改指针。
- `tools/patch_chinese_demo.py`：利用 9 个未使用的 8×8 字库槽，构建“新游戏”静态 ROM 样例。
- `tools/validate_translations.py`：检查译文是否保留 POWDER 的 `%...` 与 `<...>` 占位符。
- `translations/zh_CN.tsv`：首批菜单/标题译文草表；`status=planned` 表示还没有写入 ROM。

运行提取：

```sh
python3 POWDER/tools/extract_powder_text.py \
  POWDER/original/powder118.gba \
  --source POWDER/source \
  --out POWDER/analysis/text
```

运行 ASCII 管线演示（不会写原 ROM）：

```sh
python3 POWDER/tools/patch_ascii.py \
  POWDER/original/powder118.gba POWDER/output/powder118_pipeline_demo.gba \
  --replace 'New Game=ZH Game'
```

这只是验证“定位 → 安全替换 → 保留 NUL → 输出副本”的流程，不是最终汉化版。

## 已修正的开源点阵样例

当前推荐版本是 `output/powder118_zh_pixel_shadow_demo.gba`，补上原字体的
不透明黑色阴影。原 Shadow 的 A 字形使用右下 `(1,1)` 偏移；新汉字按相同
方法叠加阴影，并将原生 7px 笔画整体上移 1px，以在 8×8 槽内留出阴影
空间。白色笔画形状没有缩放或增粗。非零黑色索引在普通图块组为 32、
Lomaka 为 31，避免把透明索引 0 当作黑色。此样例对五种字体统一使用阴影。

```sh
python3 POWDER/tools/patch_chinese_demo.py \
  POWDER/original/powder118.gba \
  POWDER/output/powder118_zh_pixel_shadow_demo.gba \
  --shadow --preview POWDER/analysis/chinese_pixel_shadow_demo.png
```

mGBA 实际画面：`analysis/runtime/pixel_shadow/boot_3x.png`。逐像素核验了
菜单里的 132 个白色/黑色像素，重绘结果一致，IPS 可完整恢复输出 ROM。
六组图块、五种字体的 90 个字形槽都验证保留原生点阵笔画且含不透明黑色。
阴影版 ROM SHA-256：
`1bca78cadbecf86c374262b49355465eb71036d79701260c0522326561c0dcf9`。

旧版 `powder118_zh_demo.gba` 已废弃：其字形槽位错了一位、仅改了 Classic
图块组，默认的 Akoi Meexx 没有改到；系统矢量字体缩成 8px 的方法也不适合。
请使用 `powder118_zh_pixel_demo.gba`。

新版使用 Fusion Pixel 2026.09.25 的原生 8px 简体 BDF，许可 OFL-1.1。
字体和全部许可保存在 `assets/fonts/fusion-pixel-8px/`。新增字节
`0x8c/0x8d/0x8e` 对应字形槽 **111/112/113**。补丁从真实 TILESET 表
`0x22BB78` 读取字体与调色板，覆盖全部六组内置图块的五种字体，共 90 个
字形槽。每组调色板分别选择白色，避免 Lomaka 的颜色索引与其他组不一致。

生成当前样例（必须从未修改的原 ROM 开始）：

```sh
python3 POWDER/tools/patch_chinese_demo.py \
  POWDER/original/powder118.gba \
  POWDER/output/powder118_zh_pixel_demo.gba \
  --preview POWDER/analysis/chinese_pixel_demo.png
```

输出同时生成 `.ips` 补丁和 `.json` 字形偏移记录。预览从写入后的默认
Akoi Meexx Shadow 字形数据读取，且只按整数倍最近邻放大。

当前 ROM SHA-256：
`4ae701ed7c68ba43f06a4fed201e5697a6e6b87e78b52e2010b03768e1d942c3`。
原 ROM 哈希保持不变。只修改字符表、`New Game` 字符串和空闲字形槽，
共 2471 字节。仍只有三个中文字符，尚未实现通用中文渲染或全量汉化。

## 运行验证

已使用从源码构建的 mGBA 0.10.5 libretro 核心进行独立模拟器验证（无系统
安装，无读取 OpenEmu 存档）。核心源提交：
`26b7884bc25a5933960f3cdcd98bac1ae14d42e2`。

- 实际菜单截图：`analysis/runtime/pixel/boot.png`（240×160）及 `boot_3x.png`。
- 逐像素检查菜单区域 `(16,48)..(40,56)`，字形与原始 BDF 完全一致。
- 向下/向上移动选项后，重绘区域字节一致，字形缓存正常。
- 按 A 后到达 Gender 选择画面，确认新游戏菜单功能正常。
- `.ips` 应用到原 ROM 后逐字节等于新 ROM。
- 验证记录：`analysis/runtime/checks.json`。

复现启动、重绘和新游戏截图：

```sh
python3 POWDER/tools/check_menu_runtime.py \
  POWDER/output/powder118_zh_pixel_demo.gba \
  --core POWDER/tools/runtime/mgba_libretro.dylib \
  --out POWDER/analysis/runtime/pixel
```

核心的 macOS ARM64 构建与 MPL-2.0 许可保存在 `tools/runtime/`。
这里尚未覆盖硬件、所有图块/字体运行组合及存档回归；非默认图块和字体
的覆盖目前来自 ROM 表、空槽断言和字形字节检查。

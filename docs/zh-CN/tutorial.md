# 教程：演示短片是怎么做出来的

[观看短片](../demo.mp4)。全长 15 秒：一只怕下雨的小蜗牛发现地湿了好滑，开心地滑走了。

它是 AI 代理只靠这个仓库做出来的。这一页会展示每一步做了什么，并附上真实的提示词。这些命令不需要你手动运行：**只要对 AI 说“帮我做一支动画短片”，它就会全部做完。** 读这篇是为了了解原理，也能让你更好地指挥 AI。

所有配置都在 [`examples/rainy-slide`](../../examples/rainy-slide)，可以直接复制。

**花费：** 大约 40 分钟，16 张生成图，生成的音频不到一分钟。

## 1. 从一句话开始

整个故事写在 [`story.md`](../../examples/rainy-slide/story.md) 里：

> 怕下雨的小蜗牛阿慢被青蛙点破：湿地面最好滑，它在雨里第一次“飞”了起来。

然后拆成四拍：害怕、青蛙的点子、发现、高潮。

**一开始就定好谁朝哪边。** 这支片子的规则是“蜗牛永远朝右走，青蛙朝左”。图是一张一张生成的，没有这条规则，对话的两个角色很容易背对背。

## 2. 设计角色

每个角色在 `config/anchors.tsv` 里占一行。形状和比例要写具体：

```
snail	A tiny original baby snail character seen from the side, facing screen right. Soft chubby rounded slug body in warm cream yellow, one big round spiral shell on its back in teal green...
```

```bash
python $S/paint.py anchors config/anchors.tsv
```

`$S` 是 `dula-flat-cel` skill 的 `scripts` 目录。后面每张画都以这张设定图为参考，所以这一步最重要。

## 3. 画姿势

接着是背景（`plates.tsv`）和每个姿势一行（`cels.tsv`）。要写清情绪和身体状态：

```
snail_fear	snail	Facing screen right. Scared: soft body squashed low and pulled half back under the shell, head tucked, eye stalks bent...
```

想让动作或场景连贯，就在最后一列写上要参照的那张：

```
snail_zoom_b	snail	...the next drawing of a bouncing slide...	snail_zoom_a
wet	...now soaking wet and shiny...	path
```

这支片子只有 6 个姿势。这就是它成本低的原因，也是有限动画的妙处：一张好画停住，就能传达很多。

```bash
python $S/paint.py plates config/plates.tsv
python $S/paint.py cels config/cels.tsv
python $S/prep_cels.py --bases-only
```

然后打开 `build/check_alpha.png`，在亮品红底上检查抠图。

## 4. 做嘴型

每张要说话的画，只改嘴，其他部分不动（`variants.tsv`）：

```
snail_fear_m1	snail_fear	Change only the mouth to open, a small rounded scared open mouth with dark inside.
```

```bash
python $S/paint.py variants config/variants.tsv
python $S/prep_cels.py
```

`prep_cels.py` 会压平颜色，并把每张变体锁回底图。在这支片子里，嘴型画和底图的差别只在嘴附近，所以换嘴时身体不会闪。

## 5. 配音

每个角色写一段对嗓音本身的描述，每句台词写念法（`film.json`）：

```json
"snail": {"desc": "一个大约六岁的小孩，声音细而软，喉咙有点紧，气息轻，语速中等偏慢，胆小"}
```

```json
{"id": "l01", "who": "snail", "text": "要下雨了……我最怕雨了！", "delivery": "发抖，声音发紧，最后三个字带一点哭腔"}
```

```bash
python <dula-voice 目录>/scripts/speak.py --dry-run    # 先看提示词，不花钱
python <dula-voice 目录>/scripts/speak.py
python <dula-voice 目录>/scripts/speak.py --sound "草地上持续的小雨声" --seconds 15 --out audio/sfx/rain.wav
```

这一步用你自己的[配音密钥](configuration.md#配音)。也可以用自己的录音，放进 `audio/voice/` 就行。

## 6. 调度镜头

`config/film.json` 就是镜头表。下面是高潮镜头（有删减）：

```json
{
  "id": "S4",
  "plate": {"key": "wet", "height": 1400, "x": [1050, 390], "y": 1290},
  "hold": 4,
  "lines": ["l04", "l05"],
  "fade_out": 0.6,
  "actors": [
    {"who": "snail", "cels": ["snail_zoom_a", "snail_zoom_b"], "cx": [-300, 1950], "t0": 0, "t1": 4.3,
     "ground": 1045, "height": 300, "bob": 10},
    {"overlay": true, "cels": ["rain_a", "rain_b", "rain_c"]}
  ]
}
```

四个简单的手法，让画面活起来：

| 手法 | 设置 | 效果 |
|---|---|---|
| 摇镜头 | 背景的 `x` 从 1050 到 390 | 世界从身边掠过 |
| 移动 | `cx` 从画外左边到画外右边 | 蜗牛穿过画面 |
| 换画 | 两张 `cels`，`hold: 4` | 一颠一颠地滑 |
| 下雨 | `make_rain.py`，再加 `overlay` | 整个场景都湿了 |

全部设置见 [film.json 说明](../../skills/dula-flat-cel/references/film-json.md)（英文）。

## 7. 渲染和检查

```bash
python $S/make_rain.py
python $S/build_film.py
python $S/render.py --stills 1,5.6,9,14     # 先看这几帧
python $S/render.py --range 0,8 -o output/test.mp4
python $S/render.py
python $S/check_mouths.py
```

如果画面里的角色在说话却没有嘴型可换，`build_film.py` 会直接报错。`check_mouths.py` 再核对实际显示的内容。在这支片子里，它查出有一句嘴只动了一次，因为一个响亮的字定下了整句的音量标准。给这句加上 `"mouth_open_at": 0.25` 就好了。

## 还能更好的地方

演示片是第一次尝试，原样展示，让你知道大概会得到什么：

- **前三个镜头几乎不动。** 加个摇镜头或多画一张会好很多。
- **第三个镜头的脖子太长。** 每个姿势都要检查比例，不对就重画。
- **两张背景不太像同一个地方。** 这支片子做的时候，背景还不能互相参照。示例的配置已经用上了这个功能，你做的应该会更连贯。
- **没有配乐。** 可以用 `bgm` 加一首你有权使用的音乐。

示例目录还用了这些新设置，所以重新生成的片子会和演示片不同：雨是叠加层，环境音听得见，有淡入淡出，轻声的字嘴也会动。而且图和声音每次都是新生成的，你的片子本来就会是独一无二的版本。

## 做你自己的片子

步骤不变，换个故事。想从这个示例开始的话：

1. 对 AI 说：“参考 `examples/rainy-slide` 做一支短片，讲一只怕黑的小猫。”
2. 它给你看角色设定图时，确认一下。
3. 看试片，说说想改什么，然后让它做完。

请使用你自己的原创角色，见[版权和协议](licenses.md)。

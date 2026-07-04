# Citationer — 产品需求文档 v2.1

> **状态**: 设计阶段  
> **作者**: Jason  
> **日期**: 2026-07-02  
> **更新**: 2026-07-04 — 新增 F-2.8 终端统计图表

---

## 变更说明 (v2.0 → v2.1)

本版本聚焦于一个核心增强：**在命令行终端中直接渲染统计图表**，让趋势、排名等数据可视化呈现，替代纯数字表格的输出方式。

---

## F-2.8 终端统计图表 🆕

### 背景与动机

当前 `stats` 命令组的全部输出均为 Rich 表格。表格精确但不够直观——趋势变化、大小对比需要用户从数字中自行想象。本功能引入终端原生图表渲染（基于 **plotext** 库，使用 braille 字符绘制连续曲线和色块），让结果一目了然。

### 技术选型

| 选项 | 折线图 | 条形图 | 中文 | 成熟度 | 结论 |
|------|--------|--------|------|--------|------|
| **plotext** v5.3 | ✅ braille 连续曲线 | ✅ 原生 hbar/vbar | ✅ | 成熟 | **选用** |
| uniplot v0.23 | ⚠️ 稀疏块状点 | ❌ 无条形图 | ⚠️ | 早期 | ❌ |
| termgraph | ❌ | ⚠️ 仅基础 | ❌ | — | ❌ |
| rich | ❌ | ⚠️ 进度条式 | ✅ | 成熟 | ❌ |
| matplotlib | ❌ 需 GUI | ❌ 无终端渲染 | ✅ | 成熟 | ❌ |

**实测对比 plotext vs uniplot 折线图**:

```
plotext (braille 连续曲线):          uniplot (稀疏块状点):
     ⢀⠤⠊                              ▝
  ⣀⠔⠊⠁                                 ▗
⡠⠔⠊                                       ▖
⡠⠒⠉                                     ▝
⡠⠊                                       ▗
                                         ▘
```

plotext 的 braille 字符无缝拼接成连续曲线；uniplot 的点之间有大段空白，不连贯。且 uniplot 完全没有条形图能力，无法用于 journals/authors/institutions 排名展示。

### 新增依赖

```toml
# pyproject.toml
[project.optional-dependencies]
viz = ["wordcloud>=1.9", "matplotlib>=3.8", "plotext>=5.3"]
```

### 功能设计

#### F-2.8.1 `stats yearly` — 年度发表趋势折线图

```
$ citationer stats yearly
```

**默认输出**: braille 折线图，x 轴 = 年份，y 轴 = 发表量，每个数据点有 marker，线条用 cyan 色。

**plotext 实际渲染效果**（简化示意）:

```
           Annual Publication Trend
  ┌──────────────────────────────────────────────────┐
  │                                             ⢀⠤⠊  │
  │                                        ⣀⠔⠊⠁     │
  │                                   ⡠⠔⠊          │
  │                              ⡠⠒⠉               │
  │                         ⡠⠊                     │
  │                   ⣀⠤⠒⠉                         │
  │              ⣀⠤⠒⠉                              │
  │        ⣀⣀⠤⠒⠉                                  │
  │  ⣀⣀⠤⠤⠒⠒⠉⠉                                    │
  └┬──────────┬──────────┬──────────┬──────────┬──┘
  2018       2020       2022       2024       2026
                 Year
```

**选项**:

| Flag | 效果 |
|------|------|
| (默认) | braille 折线图 + 底部一行统计数字（斜率、总量） |
| `--cumulative` | 双系列：柱状（年度量，左轴）+ 折线（累积量，右轴） |
| `--no-chart` | 回退为 Rich 表格（当前行为），适用于管道或重定向 |
| `--chart-only` | 仅显示图表，不附带统计数字 |

**TTY 检测**: 当 `sys.stdout.isatty()` 为 `False`（管道/重定向）时，自动禁用图表，输出 Rich 表格。

#### F-2.8.2 `stats journals` — 期刊排名条形图

```
$ citationer stats journals --top 10
```

**默认输出**: 水平条形图（`orientation='h'`），标签在左侧、条形向右侧延伸，颜色蓝色渐变。

**plotext 实际渲染效果**（简化示意）:

```
                     Top 10 Journals
  ┌──────────────────────────────────────────────────────┐
  │                                                      │
  │ SCIENTOMETRICS            ████████                   │
  │ PLOS ONE                  ██████████                 │
  │ NEUROIMAGE                ████████████               │
  │ SUSTAINABILITY            ██████████████             │
  │ IEEE ACCESS               ██████████████████         │
  │ SCIENCE                   ██████████████████████     │
  │ NATURE                    ████████████████████████   │
  │                                                      │
  └┬──────────────┬──────────────┬──────────────┬────────┘
  0              20             40             60
```

**选项**: `--no-chart` 恢复表格，`--chart-only` 仅图表。

#### F-2.8.3 `stats authors` — 作者排名条形图

格式同 journals，水平条形图。底部附加 Price 定律核心作者信息。

#### F-2.8.4 `stats institutions` — 机构排名条形图

格式同上，水平条形图。

#### F-2.8.5 颜色方案

```
折线图主线    → plotext cyan
折线图累积线  → plotext gold  
条形图        → plotext blue  (内置渐变色阶)
```

#### F-2.8.6 实现路径

```
src/citationer/viz/
├── __init__.py
├── charts.py            # matplotlib 静态图表 (已有)
└── terminal_charts.py   # plotext 终端图表 (新增)
```

`terminal_charts.py` 提供两个核心函数：

```python
def plot_line(years: list[int], counts: list[int],
              title: str, xlabel: str = "Year",
              ylabel: str = "Publications") -> str:
    """Render a braille line chart, return the ANSI string."""

def plot_hbar(labels: list[str], values: list[int],
              title: str, max_items: int = 20) -> str:
    """Render a horizontal bar chart, return the ANSI string."""
```

各 `stats` 子命令在 `--no-chart` 未设置时调用对应的渲染函数，`--chart-only` 时跳过表格直接显示图表。

#### F-2.8.7 变更影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `pyproject.toml` | 修改 | viz 组新增 `plotext>=5.3` |
| `src/citationer/viz/terminal_charts.py` | **新建** | `plot_line()`, `plot_hbar()` |
| `src/citationer/cli/stats_cmd.py` | 修改 | yearly/journals/authors/institutions 增加图表渲染 |

---

## 附录: 版本历史

| 版本 | 日期 | 主要内容 |
|------|------|---------|
| v1.0 | 2026-07-02 | Phase 1 MVP 原始需求 |
| v2.0 | 2026-07-03 | Phase 2: Text NLP、LLM、Network、Help 系统 |
| v2.1 | 2026-07-04 | 终端统计图表 (plotext braille line + hbar) |

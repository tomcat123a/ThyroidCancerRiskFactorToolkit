# 针对基于大模型的甲状腺癌风险因素抽取的方法代码库

[English](README.md)

**项目作者：** Yuqun Zeng  
**邮箱：** zengyuqun401@163.com  
**项目标题：** 针对基于大模型的甲状腺癌风险因素抽取的方法代码库（包括语义聚类，语义标记，同义词合并，统计，UMLS 匹配等功能）

这是一个适合首次公开发布到 GitHub 的开源代码库版本。仓库从 `preproc_thca.xlsx` 出发，围绕甲状腺癌风险因素抽取与整理，提供可安装、可运行、可扩展的分析流程，重点面向结构化输出和论文统计表，不包含画图模块。

## 这个仓库能做什么

它把 `论文写作1-2.pdf` / `论文写作1-2.docx` 中的方法流程整理成了一个可以复用的代码库，主要覆盖：

- 从宽表中展开甲状腺癌风险因素 triplet
- 国家与大洲标注
- 语义聚类与分级标签
- 同义词融合
- UMLS 风格标准化匹配
- 面向论文写作的统计表导出
- 中英文双语提示词管理，代码默认使用英文提示词

不包含：

- 画图功能
- 更早期原始文件预处理到 `preproc_thca.xlsx` 的步骤

## 首次公开发布版亮点

- 代码包结构清晰，主模块位于 `src/thca_risk_factor_toolkit/`
- 自带前 100 行 `.xlsx` 演示样例，可直接作为公开仓库示范数据
- 预留 `DeepSeek-V3.2` 与 `Gemini-3-pro` 的占位式配置
- 所有提示词单独放在 `prompt/` 目录
- README 默认英文展示，同时支持点击切换中文
- 增加了纯文本 ASCII 流程图，适合 GitHub 页面直接查看

## 快速开始

```bash
git clone <你的-github-仓库地址>
cd github_repo
bash scripts/install.sh
bash scripts/run_demo.sh
```

如果你已经拿到完整版 `preproc_thca.xlsx`，把 `config.json` 中的 `input_xlsx` 改成完整版路径后，再运行：

```bash
bash scripts/run_full.sh
```

## 流程概览

纯文本流程图：

- [docs/pipeline_flow_en.txt](docs/pipeline_flow_en.txt)
- [docs/release_structure_flow.txt](docs/release_structure_flow.txt)

流程摘要：

```text
preproc_thca.xlsx
  -> triplet 展开
  -> 国家 / 大洲补标
  -> 语义标签
  -> 同义词融合
  -> UMLS 匹配
  -> 中间结果工作簿
  -> 统计结果工作簿
```

## 主要输出

运行后会在 `outputs/` 下生成：

- `thca_intermediate_demo.xlsx` 或 `thca_intermediate_full.xlsx`
- `thca_statistics_demo.xlsx` 或 `thca_statistics_full.xlsx`
- `run_summary_demo.md` 或 `run_summary_full.md`

统计工作簿中包含和论文表格口径接近的多个 sheet，例如：

- `paper_year_basic_stats`
- `study_type_stats`
- `continent_year_bin_long`
- `continent_year_bin_pivot`
- `country_top10_papers`
- `country_top10_year_bin_long`
- `country_top10_year_bin_pivot`
- `label1_overall`
- `label1_year_bin`
- `evidence_grade_overall`
- `evidence_grade_year_bin`
- `endpoint_top3_factors`
- `factor_synonym_catalog`
- `umls_coverage_summary`

## 数据发布说明

公开仓库中只包含样例数据：

- `data/sample/preproc_thca_demo_first100.xlsx`

完整版 `preproc_thca.xlsx` 不直接放入仓库。若需要获取，请联系：

- Yuqun Zeng
- `zengyuqun401@163.com`

## 大模型配置说明

项目按照以下顺序加载 `config.json`：

1. 当前工作目录下的 `config.json`
2. 项目根目录下的 `config.json`

仓库提交的配置文件仅保留占位用的 URL 和 API Key，不包含真实线上值。需要启用 API 标注时，请自行填写。

已预留模型配置：

- `DeepSeek-V3.2`
- `Gemini-3-pro`

## 仓库结构

```text
github_repo/
├─ config.json
├─ config.example.json
├─ data/
│  ├─ demo_resources/
│  └─ sample/
├─ docs/
├─ prompt/
│  ├─ en/
│  └─ zh/
├─ scripts/
├─ src/thca_risk_factor_toolkit/
├─ agent_data/
└─ outputs/
```

## 提示词资源

所有提示词都单独保存在：

- `prompt/en/*.txt`
- `prompt/zh/*.txt`

仓库中同时保留中英文双语提示词，代码默认读取英文版。

## 文档索引

- [docs/architecture.md](docs/architecture.md)
- [docs/output_spec.md](docs/output_spec.md)
- [docs/manuscript_table_mapping.md](docs/manuscript_table_mapping.md)
- [docs/github_push.md](docs/github_push.md)
- [docs/github_about.txt](docs/github_about.txt)
- [docs/homepage_snippets.txt](docs/homepage_snippets.txt)
- [docs/pipeline_flow_en.txt](docs/pipeline_flow_en.txt)
- [docs/release_structure_flow.txt](docs/release_structure_flow.txt)

## GitHub 右上角 About 建议文案

```text
项目作者是Yuqun Zeng,邮箱是zengyuqun401@163.com，项目标题是，针对基于大模型的甲状腺癌风险因素抽取的方法代码库（包括语义聚类，语义标记，同义词合并，统计，umls匹配等功能）。
```

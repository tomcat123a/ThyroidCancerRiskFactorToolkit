# TCRiskFlow —— 针对基于大模型的甲状腺癌风险因素抽取的方法代码库

![TCRiskFlow 流程总览](docs/main_plot.png)

[English](README.md)

**项目作者：** Yuqun Zeng
**邮箱：** zengyuqun@hmc.edu.cn
**对应论文：** A scalable LLM-driven framework for evidence synthesis of disease associated risk factors: application to thyroid cancer.

本仓库是论文方法的公开可运行实现。从筛选后的摘要表（`abstracts_final.xlsx`，每篇论文一行，含标题与摘要）开始，依次执行：大模型结构化抽取、地理信息补标、标题去重与甲状腺相关三元组筛选，随后把风险因素划分到三级分类体系、归并为同义词组、匹配 UMLS 概念，并用一个复合证据分数驱动时间、地理与指南导向分析。

大模型调用采用 OpenAI 消息格式兼容的传输（见下文）：用户只需在 `config.json` 中填入 `model`、`api_url` 与 `api_key`。仓库内置演示样例（随机 100 行摘要 + 抽样同义词文件），可在不分发完整数据的情况下演示流程。

---

## 上游预处理（本仓库不实现）

本仓库实现的流程从 `abstracts_final.xlsx`（筛选后的摘要表）开始。上游文献筛选步骤在论文「Data Source and Preprocessing」一节中描述，**不属于本仓库**，其流程如下：

1. **检索** —— 使用预定义的 MeSH 词与自由文本关键词（“thyroid cancer”）从 Web of Science Core Collection 程序化检索文献，时间跨度为 1980 年 1 月至 2025 年 7 月（106,785 条记录，含标题、摘要、作者、机构、国家/地区、发表年份等元数据）。
2. **语言 / 来源 / 摘要筛选** —— 依次按语言、出版来源与摘要可用性筛选，剩余 56,800 条。
3. **文献类型过滤与去重** —— 进一步做文献类型过滤及按标题/摘要去重，得到 55,203 条唯一记录，即进入 TCRiskFlow 流程的最终语料（`abstracts_final.xlsx`）。

---

## 仓库覆盖的能力

| 能力 | 论文章节 | 脚本 |
| --- | --- | --- |
| 结构化摘要抽取（标题 + 摘要 → 因果三元组） | Structured abstract extraction module | `structured_extraction.py` |
| 按标题去重 | Data Source and Preprocessing | `deduplicate_title.py` |
| 甲状腺相关三元组筛选 | Structured abstract extraction module | `count_thyroid_triplets.py` |
| 三级语义分类 | Semantic taxonomy construction module | `factor_classifier.py`、`classify_risk_factors.py`、`hierarchy.py` |
| 同义词归一化（按 Level-3） | Synonym aggregation and normalization module | `group_synonyms.py`、`merge_age.py` |
| UMLS 标准化匹配 | Synonym aggregation and normalization module | `umls_match.py` |
| 复合证据分数 + 年份/大洲/分组统计 | Evidence quantification module；Temporal and spatiotemporal evolution analyses | `factor_scoring.py`、`factor_data.py`、`factor_data_semantic.py`、`factor_scores.py`、`evidence_quantification.py` |
| 指南一致性与差距分析 | Guideline-oriented concordance evaluation and gap analysis | `guideline_analysis.py` |
| 聚类对照实验（余弦层次聚类 vs. KMeans） | Clustering ablation test | `ablation/` |

---

## 论文方法与代码对应关系

| # | 论文章节 | 论文原文要点 | 脚本 | 关键参数 |
| --- | --- | --- | --- | --- |
| 1 | Structured abstract extraction module | "DeepSeek-V4 Pro ... JSON schema ... temperature 0.0 ... categorical variables restricted to predefined candidate options" | `structured_extraction.py` | `temperature=0.0`、非流式；每篇摘要最多 12 个三元组 |
| 2 | Data Source and Preprocessing | "title/abstract-based deduplication yielded unique records"（按标题/摘要去重） | `deduplicate_title.py` | 去重键 = `TI`，`keep="first"` |
| 3 | Structured abstract extraction module | "causal_triplets ... object.disease ... thyroid cancer" | `count_thyroid_triplets.py` | 疾病字段含 `thyr`（忽略大小写）；非甲状腺三元组前移压缩 |
| 4 | Semantic taxonomy construction module | "DeepSeek-V4 Pro and Doubao-1.8-Seed ... majority voting ... Level-3 assignments" | `factor_classifier.py`、`classify_risk_factors.py`、`hierarchy.py` | 单阶段 Level-3 分类；`factor-subcategory.json`（6 个 Level-1 / 24 个 Level-2 / 113 个 Level-3）；LLM 关闭时走规则兜底 |
| 5 | Synonym aggregation and normalization module | "synonym harmonization ... within predefined Level-3 categories ... case-insensitive lexicographic rule" | `group_synonyms.py`、`merge_age.py` | 规范键按 `(长度, 词)` 排序；`factor_id = SHA-256(factor_key)`；Age 程度词合并 |
| 6 | Synonym aggregation and normalization module（UMLS） | "QuickUMLS ... overlapping_criteria='score' ... threshold 0.809 ... discard <0.90" | `umls_match.py` | `SIMILARITY_THRESHOLD = 0.90`；按 CUI 去重、保留最高相似度 |
| 7 | Evidence quantification module | "Score = w_num·Z[log(n_paper)] + w_size·Z[log(n_sample)] + w_statsig·Z(S_statsig) + w_evigrade·Z(E_evigrade)"；权重 `W_num=2, W_size=1, W_statsig=1, W_evigrade=2` | `factor_scoring.py`、`factor_data.py`、`factor_scores.py`、`evidence_quantification.py` | p 值权重 1.0/0.5/0.1；GRADE 高/中/低/极低 = 4/3/2/1；全局 Z-score 用 `ddof=0` |
| 8 | Temporal and spatiotemporal evolution analyses | "five predefined periods (before 2000, 2001–2010, 2011–2015, 2016–2020 and 2021–2025)" | `factor_scores.py` | `YEAR_BINS` 含端点；按分数取 top-10 |
| 9 | Guideline-oriented concordance evaluation and gap analysis | "exact-group match ... shared-term match"；"Coverage = N_matched / N_total ×100%" | `guideline_analysis.py` | `guideline_match_policy="shared_term"`；覆盖率按 10%/5%/2%/1% 分位 |
| 10 | Clustering ablation test | "cosine average-linkage agglomerative ... k-means ... K = Level-3 类别数 ... ARI, NMI, purity, homogeneity, completeness, mapped macro-F1" | `ablation/`（详见 `docs/ablation_study.md`） | KMeans `random_state=42, n_init=20, max_iter=300, algorithm="lloyd"` |
| 11 | Statistical Analysis | "Counts and percentages ... medians with ranges ... χ², Cramér's V, NMI" | `statistics.py` | 文献计量表；详见 `docs/output_spec.md` |

---

## 快速开始

```bash
git clone <你的-github-仓库地址>
cd github_repo
bash scripts/install.sh
bash scripts/run_demo.sh
```

演示读取 `data/sample/abstracts_final_demo_first100.xlsx`，依次执行结构化抽取 → 地理补标 → 去重 → 甲状腺筛选 → 分类 → 同义词归一化 → 证据量化 → UMLS → 统计。由于结构化抽取依赖大模型，演示需要配置 API Key 才能产出结果；未配置时流程会打印明确提示后停止。

完整运行：把 `config.json` 中的 `input_xlsx` 改为完整 `abstracts_final.xlsx` 路径后运行：

```bash
bash scripts/run_full.sh
```

### 运行聚类对照实验

```bash
python scripts/run_ablation_main.py
```

所需数据形式、两种聚类方法与各统计标签的计算方法见 [docs/ablation_study.md](docs/ablation_study.md)。

---

## 仓库结构

```text
github_repo/
├─ config.json / config.example.json
├─ data/
│  ├─ sample/
│  │  ├─ abstracts_final_demo_first100.xlsx
│  │  └─ 09_factor_label_associations_semantic_merged_v2_demo_first100.csv
│  └─ demo_resources/
│     ├─ factor-subcategory.json
│     ├─ umls_concepts_demo.csv
│     ├─ country_continent_reference.csv
│     └─ guideline/{ATA 2015, NCCN 2023}/*.json
├─ prompt/{en,zh}/*.txt
├─ scripts/
│  ├─ run_demo_pipeline_main.py
│  ├─ run_full_pipeline_main.py
│  ├─ run_ablation_main.py
│  └─ build_demo_sample_main.py
├─ src/thca_risk_factor_toolkit/
│  ├─ common.py, hierarchy.py, factor_scoring.py, config.py, path_utils.py
│  ├─ structured_extraction.py
│  ├─ deduplicate_title.py
│  ├─ count_thyroid_triplets.py
│  ├─ classify_risk_factors.py, factor_classifier.py
│  ├─ group_synonyms.py, merge_age.py
│  ├─ factor_data.py, factor_data_semantic.py, factor_scores.py
│  ├─ guideline_analysis.py, evidence_quantification.py
│  ├─ umls_match.py, statistics.py, pipeline.py
│  └─ ablation/{__init__,config,metrics,clustering,run_ablation}.py
├─ docs/
└─ outputs/
```

---

## 主要输出

- `outputs/thca_intermediate_demo.xlsx` —— 三元组标签、同义词因子映射与 UMLS 匹配结果。
- `outputs/thca_statistics_demo.xlsx` —— 文献计量表、同义词目录与 UMLS 覆盖率。
- `outputs/10_factor_scores_semantic/` —— 证据分数、分组统计与指南分析（CSV + Excel）。

代表表：`factor_score_overall`、`factor_score_by_year_bin`、`year_score_top10`、`continent_year_label1_top10`、`label_3_overall`、`evidence_grade_overall`、`coverage_by_score_percentile`、`unmatched_factors`。详见 [docs/output_spec.md](docs/output_spec.md)。

---

## 数据发布说明

`data/sample/` 下的文件为**从完整数据中随机抽取的 100 行示例**，仅用于程序展示与端到端演示，**不用于分析或发表**。

完整 `abstracts_final.xlsx` 与完整 `09_factor_label_associations_semantic_merged_v2.csv` **不随仓库分发**。如需获取，请联系 **Yuqun Zeng**（`zengyuqun@hmc.edu.cn`），经批准后方可获得。

在完整数据上运行整个流程的方法：将完整 `abstracts_final.xlsx` 放置好，在 `config.json` 中设置 `input_xlsx`、启用大模型配置后，运行 `bash scripts/run_full.sh`（详见 [data/README.md](data/README.md)）。

---

## 大模型配置说明

本仓库仅提供 **OpenAI 消息格式兼容**的大模型客户端（`chat.completions` 消息结构），兼容 [OpenRouter](https://openrouter.ai)、[DeepSeek 开放平台](https://platform.deepseek.com) 等公开端点。启用 API 抽取与分类只需在 `config.json` 中填入 `model`、`api_url` 与 `api_key`。

生成方式始终与论文一致（「Prompt engineering and model control」一节）：**非流式**、**`temperature=0.0`**，每次请求/响应都记录到 `agent_data/` 以便追溯。模型名称严格遵循论文：

- `llm` —— `DeepSeek-V4-Pro`（OpenAI 兼容），主标注模型（结构化抽取、分类、同义词分组）。
- `secondary_llm` —— `Doubao-1.8-Seed`（OpenAI 兼容），第二独立标注模型。
- `adjudicator_llm` —— `Gemini-3-Pro`（Gemini 兼容），用于长上下文语义聚类与分歧裁决。

`provider` 仅用于选择传输协议（`openai_compatible` 或 `gemini_compatible`），不硬编码具体厂商。提示词存放在 `prompt/en`（代码默认读取）与 `prompt/zh`。

## 文档索引

- [docs/architecture.md](docs/architecture.md)
- [docs/ablation_study.md](docs/ablation_study.md)
- [docs/output_spec.md](docs/output_spec.md)
- [docs/manuscript_table_mapping.md](docs/manuscript_table_mapping.md)
- [docs/pipeline_flow_en.txt](docs/pipeline_flow_en.txt)

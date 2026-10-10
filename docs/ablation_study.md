# 聚类对照实验（Clustering Ablation Study）

对应论文「Methods → Clustering ablation test」一节。该实验回答一个核心问题：**仅凭文本嵌入的几何邻近能否复现最终的三级语义分类体系**？论文结论是否定的——嵌入空间的距离本身无法重现 LLM 辅助语义归纳加专家审核得到的类别边界，从而支持 LLM 语义归纳与专家监督合并的附加价值。

## 1. 依赖的数据形式

对照实验只读取 Step 09 第二轮语义合并产物：

```
data/sample/09_factor_label_associations_semantic_merged_v2_demo_first100.csv
```

必需列（`ablation/clustering.py` 中 `V2_REQUIRED_COLUMNS`）：

| 列名 | 含义 |
| --- | --- |
| `label_1` | 第一级（Level-1）领域 |
| `label_2` | 第二级（Level-2）类别 |
| `label_3` | 第三级（Level-3）类别（**作为外部语义参照**） |
| `factor_id` | 同义词组的稳定标识 |
| `factor_key` | 同义词组的 JSON 列表（`["term a", "synonym b"]`） |
| `factor_name` | 该组的代表词 |
| `factor_group_size` | 同义词数量 |

`factor_key` 会被展开成逐词行（`subject_name`），每个词携带其 `label_1/label_2/label_3`。`label_3` 仅用于 (a) 确定每个 Level-1 域内的聚类数 `K`，以及 (b) 事后评估一致性，**不参与聚类分配**。

还需要：

- 嵌入模型目录：`jina-embeddings-v5-text-small`（`sentence_transformers` 可加载），默认位于 `embedding/model_cache/jina-embeddings-v5-text-small`。
- 完整版实验读取完整 `09_factor_label_associations_semantic_merged_v2.csv`（22,708 个标准化因子，展开后约 31,906 个词）。公开仓库仅内置抽样样例，完整数据请联系作者获取。

## 2. 两种聚类方法

两个方法使用**完全相同**的词、嵌入向量和聚类数 `K`（`K` = 该 Level-1 域内 Level-3 类别数）。

### (a) 余弦平均连接层次聚类（Cosine hierarchy）

```text
距离度量   : cosine
连接方式   : average linkage（UPGMA）
切分方式   : 在 K 处切树（scipy.cluster.hierarchy.linkage + cut_tree）
```

实现见 `ablation/clustering.py::cosine_hierarchy_clustering`。对词向量两两计算余弦距离，用平均连接构建层次树，再切出恰好 `K` 个簇。

### (b) 同 K 的 KMeans

```text
随机种子   : 42
n_init     : 20
max_iter   : 300
算法       : Lloyd
```

实现见 `ablation/clustering.py::kmeans_clustering`，参数与论文「Methods → Clustering ablation test」一致。

### 嵌入生成

```text
模型        : jina-embeddings-v5-text-small
任务提示    : task="clustering"
归一化      : L2 归一化（sklearn.preprocessing.normalize, norm="l2"）
```

每个 Level-1 域内独立生成嵌入并独立聚类（见 `run_ablation.py`）。KMeans 对聚类数设定存在中等敏感性（论文 Supplementary Fig. 4 的敏感性分析），因此主对照固定 `K` = Level-3 类别数，另提供 Gap 统计量方案作为备选（见 `backend/ablation_study_src` 完整实现）。

## 3. 各统计标签的计算方法

实现见 `ablation/metrics.py`。所有指标都在「真实标签 = 最终 Level-3 标签，预测标签 = 聚类簇 id」上计算。

| 指标 | 定义 | 公式 / 说明 |
| --- | --- | --- |
| **ARI** | 调整兰德指数 | `sklearn.metrics.adjusted_rand_score` |
| **NMI** | 归一化互信息 | `sklearn.metrics.normalized_mutual_info_score` |
| **Purity** | 纯度 | `sum(max(每列)) / 样本总数`，即每个簇内众数类别的样本占比的加权平均 |
| **Homogeneity** | 同质性 | `sklearn.metrics.homogeneity_score` |
| **Completeness** | 完整性 | `sklearn.metrics.completeness_score` |
| **Mapped macro-F1** | 映射后宏 F1 | 先用匈牙利算法（`scipy.optimize.linear_sum_assignment`）对「簇 → Level-3 类别」做一对一映射，再对每个类别计算 F1（无样本分配的类别 F1 记为 0），最后取未加权平均 |

**汇总口径**：论文对各指标报告「六个 Level-1 域的未加权平均」（`metrics.py::unweighted_mean`）。因此 `hierarchy_vs_v2_ari`、`kmeans_vs_v2_ari` 等字段按域分别保存，最后跨域取算术平均。

## 4. 运行

```bash
python scripts/run_ablation_main.py
```

输出（`outputs/ablation_study/`）：

- `clustering_ablation_summary.csv` —— 每个 Level-1 域一行：词数、因子数、`K`、两方法的 ARI/NMI/purity/macro-F1。
- `clustering_ablation_metrics.csv` —— 每个 (Level-1, 聚类方案) 一行的完整指标。

注意：嵌入模型需要 GPU/CPU 推理环境与 `sentence-transformers`、`torch`、`scikit-learn`、`scipy` 依赖。公开仓库默认不随附模型权重，运行前需将 `jina-embeddings-v5-text-small` 放到 `embedding/model_cache/` 或修改 `config.json` 的 `clustering_ablation.model_dir`。

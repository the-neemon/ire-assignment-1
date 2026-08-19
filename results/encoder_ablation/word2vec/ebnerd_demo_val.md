# ebnerd_demo — val

6,872 impressions, 6,872 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5234 [0.5154, 0.5309] | 0.3456 [0.3387, 0.3526] | 0.3814 [0.3736, 0.3897] | 0.4627 [0.4564, 0.4694] |
| emb | 0.5140 [0.5065, 0.5221] | 0.3388 [0.3317, 0.3463] | 0.3704 [0.3624, 0.3794] | 0.4538 [0.4473, 0.4608] |
| fused | 0.5288 [0.5211, 0.5367] | 0.3459 [0.3397, 0.3529] | 0.3845 [0.3772, 0.3929] | 0.4630 [0.4567, 0.4694] |
| fused+popularity | 0.5661 [0.5587, 0.5731] | 0.3616 [0.3545, 0.3685] | 0.4060 [0.3979, 0.4135] | 0.4810 [0.4743, 0.4872] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8078 | 13.6199 | 0.1120 |
| emb | 0.8033 | 13.6133 | 0.1119 |
| fused | 0.8061 | 13.6158 | 0.1123 |
| fused+popularity | 0.8065 | 13.5935 | 0.1100 |

## AUC by slice

cold = history length <= 44; head = clicked article with >= 41 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 697 | 0.5497 [0.5253, 0.5750] | 0.5514 [0.5291, 0.5748] | 0.5638 [0.5399, 0.5887] | 0.5919 [0.5707, 0.6155] |
| warm | 6,175 | 0.5204 [0.5131, 0.5288] | 0.5097 [0.5013, 0.5182] | 0.5249 [0.5173, 0.5333] | 0.5632 [0.5563, 0.5712] |
| head | 105 | 0.4914 [0.4303, 0.5590] | 0.6471 [0.5814, 0.7109] | 0.5458 [0.4903, 0.6071] | 0.6401 [0.5890, 0.6939] |
| tail | 6,767 | 0.5239 [0.5156, 0.5316] | 0.5119 [0.5045, 0.5197] | 0.5286 [0.5200, 0.5362] | 0.5649 [0.5572, 0.5726] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0114 [0.0090, 0.0138] | 0.0217 [0.0185, 0.0250] | 0.0434 [0.0386, 0.0479] |
| emb | 0.0063 [0.0044, 0.0083] | 0.0140 [0.0114, 0.0169] | 0.0327 [0.0283, 0.0366] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 697 | 0.0488 [0.0330, 0.0646] | 0.0344 [0.0215, 0.0473] | -0.0143 [-0.0345, +0.0057] | no |
| warm | 6,175 | 0.0428 [0.0381, 0.0476] | 0.0325 [0.0282, 0.0371] | -0.0103 [-0.0165, -0.0035] | yes |
| head | 105 | 0.0966 [0.0435, 0.1551] | 0.1905 [0.1238, 0.2667] | +0.0939 [-0.0095, +0.1905] | no |
| tail | 6,767 | 0.0426 [0.0383, 0.0480] | 0.0302 [0.0262, 0.0344] | -0.0123 [-0.0189, -0.0069] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | -0.0094 [-0.0197, +0.0008] | no |
| emb - bm25 (ndcg@10) | -0.0090 [-0.0164, -0.0010] | yes |
| fused - emb (auc) | +0.0149 [+0.0068, +0.0227] | yes |
| fused - emb (ndcg@10) | +0.0092 [+0.0027, +0.0158] | yes |
| fused - bm25 (auc) | +0.0054 [+0.0010, +0.0103] | yes |
| fused - bm25 (ndcg@10) | +0.0003 [-0.0025, +0.0035] | no |
| fused+popularity - fused (auc) | +0.0372 [+0.0316, +0.0426] | yes |
| fused+popularity - fused (ndcg@10) | +0.0179 [+0.0134, +0.0223] | yes |
| emb - bm25 (recall@50) | -0.0051 [-0.0080, -0.0022] | yes |
| emb - bm25 (recall@100) | -0.0077 [-0.0118, -0.0033] | yes |
| emb - bm25 (recall@200) | -0.0107 [-0.0164, -0.0043] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.

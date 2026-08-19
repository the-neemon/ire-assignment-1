# ebnerd_demo — val

6,872 impressions, 6,872 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5234 [0.5154, 0.5309] | 0.3456 [0.3387, 0.3526] | 0.3814 [0.3736, 0.3897] | 0.4627 [0.4564, 0.4694] |
| emb | 0.4877 [0.4797, 0.4954] | 0.3199 [0.3132, 0.3261] | 0.3518 [0.3436, 0.3594] | 0.4367 [0.4298, 0.4427] |
| fused | 0.5234 [0.5154, 0.5309] | 0.3456 [0.3387, 0.3526] | 0.3814 [0.3736, 0.3897] | 0.4627 [0.4564, 0.4694] |
| fused+popularity | 0.5589 [0.5514, 0.5656] | 0.3599 [0.3526, 0.3667] | 0.4029 [0.3948, 0.4103] | 0.4785 [0.4717, 0.4847] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8078 | 13.6199 | 0.1120 |
| emb | 0.8096 | 13.6067 | 0.1115 |
| fused | 0.8078 | 13.6199 | 0.1120 |
| fused+popularity | 0.8079 | 13.5918 | 0.1101 |

## AUC by slice

cold = history length <= 44; head = clicked article with >= 41 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 697 | 0.5497 [0.5253, 0.5750] | 0.4924 [0.4670, 0.5159] | 0.5497 [0.5253, 0.5750] | 0.5708 [0.5484, 0.5954] |
| warm | 6,175 | 0.5204 [0.5131, 0.5288] | 0.4872 [0.4798, 0.4959] | 0.5204 [0.5131, 0.5288] | 0.5575 [0.5501, 0.5652] |
| head | 105 | 0.4914 [0.4303, 0.5590] | 0.5484 [0.4974, 0.5987] | 0.4914 [0.4303, 0.5590] | 0.5903 [0.5402, 0.6467] |
| tail | 6,767 | 0.5239 [0.5156, 0.5316] | 0.4868 [0.4786, 0.4945] | 0.5239 [0.5156, 0.5316] | 0.5584 [0.5503, 0.5663] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0114 [0.0090, 0.0138] | 0.0217 [0.0185, 0.0250] | 0.0434 [0.0386, 0.0479] |
| emb | 0.0070 [0.0051, 0.0089] | 0.0123 [0.0097, 0.0148] | 0.0325 [0.0282, 0.0368] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 697 | 0.0488 [0.0330, 0.0646] | 0.0244 [0.0143, 0.0359] | -0.0244 [-0.0430, -0.0029] | yes |
| warm | 6,175 | 0.0428 [0.0381, 0.0476] | 0.0334 [0.0294, 0.0378] | -0.0094 [-0.0154, -0.0028] | yes |
| head | 105 | 0.0966 [0.0435, 0.1551] | 0.0476 [0.0095, 0.0860] | -0.0490 [-0.1185, +0.0190] | no |
| tail | 6,767 | 0.0426 [0.0383, 0.0480] | 0.0322 [0.0279, 0.0364] | -0.0103 [-0.0173, -0.0045] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | -0.0356 [-0.0469, -0.0244] | yes |
| emb - bm25 (ndcg@10) | -0.0261 [-0.0344, -0.0179] | yes |
| fused - emb (auc) | +0.0356 [+0.0244, +0.0469] | yes |
| fused - emb (ndcg@10) | +0.0261 [+0.0179, +0.0344] | yes |
| fused - bm25 (auc) | +0.0000 [+0.0000, +0.0000] | no |
| fused - bm25 (ndcg@10) | +0.0000 [+0.0000, +0.0000] | no |
| fused+popularity - fused (auc) | +0.0355 [+0.0295, +0.0410] | yes |
| fused+popularity - fused (ndcg@10) | +0.0157 [+0.0115, +0.0198] | yes |
| emb - bm25 (recall@50) | -0.0044 [-0.0077, -0.0015] | yes |
| emb - bm25 (recall@100) | -0.0094 [-0.0137, -0.0053] | yes |
| emb - bm25 (recall@200) | -0.0109 [-0.0175, -0.0047] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.

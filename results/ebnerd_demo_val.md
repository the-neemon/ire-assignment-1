# ebnerd_demo — val

6,872 impressions, 6,872 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5234 [0.5154, 0.5309] | 0.3456 [0.3387, 0.3526] | 0.3814 [0.3736, 0.3897] | 0.4627 [0.4564, 0.4694] |
| emb | 0.5363 [0.5284, 0.5440] | 0.3514 [0.3439, 0.3589] | 0.3900 [0.3818, 0.3983] | 0.4673 [0.4605, 0.4742] |
| fused | 0.5430 [0.5352, 0.5504] | 0.3570 [0.3500, 0.3642] | 0.3966 [0.3884, 0.4045] | 0.4736 [0.4670, 0.4801] |
| fused+popularity | 0.5654 [0.5577, 0.5726] | 0.3616 [0.3540, 0.3687] | 0.4049 [0.3965, 0.4131] | 0.4811 [0.4744, 0.4875] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8078 | 13.6199 | 0.1120 |
| emb | 0.7990 | 13.6136 | 0.1112 |
| fused | 0.7993 | 13.6196 | 0.1117 |
| fused+popularity | 0.8036 | 13.5905 | 0.1100 |

## AUC by slice

cold = history length <= 44; head = clicked article with >= 41 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 697 | 0.5497 [0.5253, 0.5750] | 0.5407 [0.5159, 0.5649] | 0.5581 [0.5362, 0.5825] | 0.5763 [0.5560, 0.5977] |
| warm | 6,175 | 0.5204 [0.5131, 0.5288] | 0.5358 [0.5280, 0.5442] | 0.5413 [0.5335, 0.5494] | 0.5642 [0.5568, 0.5717] |
| head | 105 | 0.4914 [0.4303, 0.5590] | 0.5070 [0.4428, 0.5700] | 0.4836 [0.4212, 0.5475] | 0.5864 [0.5335, 0.6448] |
| tail | 6,767 | 0.5239 [0.5156, 0.5316] | 0.5368 [0.5284, 0.5446] | 0.5439 [0.5354, 0.5514] | 0.5651 [0.5572, 0.5726] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0114 [0.0090, 0.0138] | 0.0217 [0.0185, 0.0250] | 0.0434 [0.0386, 0.0479] |
| emb | 0.0163 [0.0133, 0.0196] | 0.0256 [0.0218, 0.0292] | 0.0468 [0.0416, 0.0517] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 697 | 0.0488 [0.0330, 0.0646] | 0.0531 [0.0373, 0.0689] | +0.0043 [-0.0143, +0.0258] | no |
| warm | 6,175 | 0.0428 [0.0381, 0.0476] | 0.0461 [0.0415, 0.0512] | +0.0034 [-0.0032, +0.0097] | no |
| head | 105 | 0.0966 [0.0435, 0.1551] | 0.0667 [0.0190, 0.1143] | -0.0299 [-0.0952, +0.0287] | no |
| tail | 6,767 | 0.0426 [0.0383, 0.0480] | 0.0465 [0.0413, 0.0517] | +0.0040 [-0.0031, +0.0100] | no |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0129 [+0.0029, +0.0231] | yes |
| emb - bm25 (ndcg@10) | +0.0046 [-0.0028, +0.0122] | no |
| fused - emb (auc) | +0.0067 [+0.0027, +0.0107] | yes |
| fused - emb (ndcg@10) | +0.0062 [+0.0022, +0.0103] | yes |
| fused - bm25 (auc) | +0.0196 [+0.0119, +0.0275] | yes |
| fused - bm25 (ndcg@10) | +0.0108 [+0.0053, +0.0163] | yes |
| fused+popularity - fused (auc) | +0.0224 [+0.0171, +0.0272] | yes |
| fused+popularity - fused (ndcg@10) | +0.0075 [+0.0033, +0.0118] | yes |
| emb - bm25 (recall@50) | +0.0050 [+0.0013, +0.0092] | yes |
| emb - bm25 (recall@100) | +0.0039 [-0.0010, +0.0086] | no |
| emb - bm25 (recall@200) | +0.0034 [-0.0032, +0.0099] | no |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.

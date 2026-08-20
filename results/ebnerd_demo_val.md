# ebnerd_demo — val

6,872 impressions, 6,872 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5234 [0.5154, 0.5309] | 0.3456 [0.3387, 0.3526] | 0.3814 [0.3736, 0.3897] | 0.4627 [0.4564, 0.4694] |
| emb | 0.5602 [0.5524, 0.5677] | 0.3656 [0.3585, 0.3727] | 0.4045 [0.3963, 0.4126] | 0.4824 [0.4759, 0.4890] |
| fused | 0.5627 [0.5549, 0.5701] | 0.3693 [0.3618, 0.3768] | 0.4093 [0.4010, 0.4176] | 0.4843 [0.4773, 0.4912] |
| fused+popularity | 0.5861 [0.5783, 0.5924] | 0.3774 [0.3694, 0.3844] | 0.4239 [0.4155, 0.4316] | 0.4947 [0.4878, 0.5010] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8078 | 13.6199 | 0.1120 |
| emb | 0.7951 | 13.6448 | 0.1128 |
| fused | 0.7957 | 13.6418 | 0.1128 |
| fused+popularity | 0.8002 | 13.6055 | 0.1100 |

## AUC by slice

cold = history length <= 44; head = clicked article with >= 41 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 697 | 0.5497 [0.5253, 0.5750] | 0.5765 [0.5533, 0.6008] | 0.5901 [0.5682, 0.6131] | 0.6081 [0.5856, 0.6308] |
| warm | 6,175 | 0.5204 [0.5131, 0.5288] | 0.5583 [0.5506, 0.5669] | 0.5596 [0.5517, 0.5679] | 0.5836 [0.5763, 0.5907] |
| head | 105 | 0.4914 [0.4303, 0.5590] | 0.6917 [0.6340, 0.7517] | 0.6663 [0.6110, 0.7212] | 0.7209 [0.6704, 0.7731] |
| tail | 6,767 | 0.5239 [0.5156, 0.5316] | 0.5581 [0.5510, 0.5663] | 0.5611 [0.5543, 0.5688] | 0.5840 [0.5771, 0.5922] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0114 [0.0090, 0.0138] | 0.0217 [0.0185, 0.0250] | 0.0434 [0.0386, 0.0479] |
| emb | 0.0100 [0.0077, 0.0124] | 0.0196 [0.0164, 0.0228] | 0.0400 [0.0354, 0.0446] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 697 | 0.0488 [0.0330, 0.0646] | 0.0430 [0.0287, 0.0588] | -0.0057 [-0.0273, +0.0143] | no |
| warm | 6,175 | 0.0428 [0.0381, 0.0476] | 0.0396 [0.0348, 0.0445] | -0.0032 [-0.0091, +0.0030] | no |
| head | 105 | 0.0966 [0.0435, 0.1551] | 0.0476 [0.0095, 0.0952] | -0.0490 [-0.1075, +0.0095] | no |
| tail | 6,767 | 0.0426 [0.0383, 0.0480] | 0.0399 [0.0352, 0.0445] | -0.0027 [-0.0093, +0.0030] | no |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0368 [+0.0268, +0.0465] | yes |
| emb - bm25 (ndcg@10) | +0.0197 [+0.0125, +0.0272] | yes |
| fused - emb (auc) | +0.0026 [-0.0011, +0.0065] | no |
| fused - emb (ndcg@10) | +0.0019 [-0.0018, +0.0056] | no |
| fused - bm25 (auc) | +0.0393 [+0.0308, +0.0472] | yes |
| fused - bm25 (ndcg@10) | +0.0215 [+0.0158, +0.0278] | yes |
| fused+popularity - fused (auc) | +0.0234 [+0.0179, +0.0285] | yes |
| fused+popularity - fused (ndcg@10) | +0.0104 [+0.0056, +0.0147] | yes |
| emb - bm25 (recall@50) | -0.0013 [-0.0045, +0.0017] | no |
| emb - bm25 (recall@100) | -0.0020 [-0.0063, +0.0022] | no |
| emb - bm25 (recall@200) | -0.0034 [-0.0093, +0.0027] | no |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.

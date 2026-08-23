# mind_small — test

73,152 impressions, 73,152 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5685 [0.5663, 0.5707] | 0.3108 [0.3086, 0.3134] | 0.2868 [0.2843, 0.2895] | 0.3479 [0.3456, 0.3505] |
| emb | 0.6369 [0.6349, 0.6391] | 0.3510 [0.3487, 0.3536] | 0.3341 [0.3317, 0.3369] | 0.3937 [0.3914, 0.3961] |
| fused | 0.6381 [0.6361, 0.6402] | 0.3536 [0.3513, 0.3563] | 0.3361 [0.3335, 0.3389] | 0.3956 [0.3933, 0.3981] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8428 | 16.9268 | 0.0536 |
| emb | 0.8215 | 16.9259 | 0.0523 |
| fused | 0.8182 | 16.9245 | 0.0529 |

## AUC by slice

cold = history length <= 3; head = clicked article with >= 152 train clicks

| slice | n | bm25 | emb | fused |
|---|---|---|---|---|
| cold | 7,529 | 0.5196 [0.5127, 0.5266] | 0.5618 [0.5547, 0.5681] | 0.5601 [0.5531, 0.5666] |
| warm | 65,623 | 0.5741 [0.5720, 0.5765] | 0.6455 [0.6431, 0.6478] | 0.6470 [0.6447, 0.6493] |
| zero_history | 2,214 | 0.5125 [0.5003, 0.5253] | 0.5125 [0.5003, 0.5253] | 0.5125 [0.5003, 0.5253] |
| head | 860 | 0.6238 [0.6077, 0.6391] | 0.6223 [0.6066, 0.6371] | 0.6347 [0.6191, 0.6503] |
| tail | 72,292 | 0.5678 [0.5655, 0.5701] | 0.6371 [0.6351, 0.6392] | 0.6381 [0.6361, 0.6401] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0062 [0.0057, 0.0068] | 0.0126 [0.0119, 0.0133] | 0.0226 [0.0215, 0.0235] |
| emb | 0.0077 [0.0071, 0.0083] | 0.0136 [0.0129, 0.0144] | 0.0237 [0.0227, 0.0248] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 7,529 | 0.0129 [0.0107, 0.0152] | 0.0155 [0.0129, 0.0183] | +0.0026 [-0.0002, +0.0052] | no |
| warm | 65,623 | 0.0237 [0.0226, 0.0247] | 0.0247 [0.0237, 0.0259] | +0.0010 [-0.0002, +0.0023] | no |
| zero_history | 2,214 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | +0.0000 [+0.0000, +0.0000] | no |
| head | 860 | 0.0896 [0.0728, 0.1063] | 0.0969 [0.0790, 0.1143] | +0.0073 [-0.0047, +0.0192] | no |
| tail | 72,292 | 0.0218 [0.0208, 0.0227] | 0.0229 [0.0219, 0.0238] | +0.0011 [-0.0001, +0.0023] | no |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0684 [+0.0659, +0.0709] | yes |
| emb - bm25 (ndcg@10) | +0.0458 [+0.0436, +0.0479] | yes |
| fused - emb (auc) | +0.0012 [+0.0005, +0.0018] | yes |
| fused - emb (ndcg@10) | +0.0020 [+0.0010, +0.0029] | yes |
| fused - bm25 (auc) | +0.0696 [+0.0675, +0.0718] | yes |
| fused - bm25 (ndcg@10) | +0.0478 [+0.0460, +0.0496] | yes |
| emb - bm25 (recall@50) | +0.0015 [+0.0009, +0.0021] | yes |
| emb - bm25 (recall@100) | +0.0011 [+0.0002, +0.0019] | yes |
| emb - bm25 (recall@200) | +0.0012 [+0.0001, +0.0024] | yes |

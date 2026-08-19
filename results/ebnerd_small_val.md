# ebnerd_small — val

64,365 impressions, 64,365 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5205 [0.5177, 0.5230] | 0.3418 [0.3393, 0.3443] | 0.3794 [0.3766, 0.3823] | 0.4607 [0.4585, 0.4630] |
| emb | 0.5309 [0.5282, 0.5336] | 0.3484 [0.3460, 0.3508] | 0.3868 [0.3839, 0.3894] | 0.4659 [0.4638, 0.4682] |
| fused | 0.5376 [0.5346, 0.5402] | 0.3512 [0.3489, 0.3535] | 0.3916 [0.3889, 0.3944] | 0.4696 [0.4673, 0.4716] |
| fused+popularity | 0.5630 [0.5604, 0.5653] | 0.3582 [0.3559, 0.3605] | 0.4039 [0.4011, 0.4066] | 0.4792 [0.4771, 0.4813] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8039 | 16.3525 | 0.1142 |
| emb | 0.7953 | 16.3469 | 0.1127 |
| fused | 0.7966 | 16.3481 | 0.1128 |
| fused+popularity | 0.8000 | 16.3358 | 0.1093 |

## AUC by slice

cold = history length <= 42; head = clicked article with >= 379 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 6,463 | 0.5281 [0.5206, 0.5366] | 0.5331 [0.5251, 0.5411] | 0.5452 [0.5373, 0.5527] | 0.5650 [0.5576, 0.5723] |
| warm | 57,902 | 0.5196 [0.5169, 0.5222] | 0.5307 [0.5281, 0.5334] | 0.5367 [0.5340, 0.5394] | 0.5628 [0.5603, 0.5653] |
| head | 1,094 | 0.5091 [0.4903, 0.5266] | 0.5516 [0.5341, 0.5689] | 0.5404 [0.5235, 0.5576] | 0.6263 [0.6108, 0.6410] |
| tail | 63,271 | 0.5207 [0.5180, 0.5233] | 0.5306 [0.5280, 0.5331] | 0.5375 [0.5349, 0.5400] | 0.5619 [0.5594, 0.5642] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0052 [0.0047, 0.0058] | 0.0110 [0.0101, 0.0118] | 0.0214 [0.0202, 0.0225] |
| emb | 0.0098 [0.0091, 0.0106] | 0.0171 [0.0160, 0.0181] | 0.0276 [0.0263, 0.0288] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 6,463 | 0.0284 [0.0245, 0.0323] | 0.0314 [0.0269, 0.0354] | +0.0030 [-0.0026, +0.0084] | no |
| warm | 57,902 | 0.0206 [0.0195, 0.0218] | 0.0272 [0.0258, 0.0285] | +0.0066 [+0.0049, +0.0082] | yes |
| head | 1,094 | 0.0229 [0.0137, 0.0320] | 0.0146 [0.0082, 0.0220] | -0.0082 [-0.0183, +0.0009] | no |
| tail | 63,271 | 0.0214 [0.0203, 0.0226] | 0.0279 [0.0266, 0.0291] | +0.0065 [+0.0047, +0.0081] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0105 [+0.0069, +0.0140] | yes |
| emb - bm25 (ndcg@10) | +0.0052 [+0.0023, +0.0077] | yes |
| fused - emb (auc) | +0.0066 [+0.0050, +0.0082] | yes |
| fused - emb (ndcg@10) | +0.0037 [+0.0021, +0.0051] | yes |
| fused - bm25 (auc) | +0.0171 [+0.0143, +0.0198] | yes |
| fused - bm25 (ndcg@10) | +0.0088 [+0.0068, +0.0107] | yes |
| fused+popularity - fused (auc) | +0.0254 [+0.0236, +0.0273] | yes |
| fused+popularity - fused (ndcg@10) | +0.0096 [+0.0082, +0.0110] | yes |
| emb - bm25 (recall@50) | +0.0046 [+0.0037, +0.0055] | yes |
| emb - bm25 (recall@100) | +0.0061 [+0.0049, +0.0073] | yes |
| emb - bm25 (recall@200) | +0.0062 [+0.0046, +0.0079] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.

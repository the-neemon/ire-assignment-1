# ebnerd_demo — test

25,356 impressions, 25,356 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5125 [0.5088, 0.5166] | 0.3273 [0.3241, 0.3308] | 0.3591 [0.3551, 0.3632] | 0.4418 [0.4387, 0.4453] |
| emb | 0.5295 [0.5255, 0.5334] | 0.3341 [0.3306, 0.3377] | 0.3685 [0.3642, 0.3726] | 0.4492 [0.4457, 0.4525] |
| fused | 0.5300 [0.5264, 0.5341] | 0.3357 [0.3321, 0.3394] | 0.3700 [0.3661, 0.3743] | 0.4508 [0.4475, 0.4543] |
| fused+popularity | 0.5728 [0.5691, 0.5768] | 0.3559 [0.3523, 0.3596] | 0.3974 [0.3932, 0.4017] | 0.4725 [0.4690, 0.4760] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.7964 | 13.9755 | 0.2178 |
| emb | 0.7910 | 13.9698 | 0.2175 |
| fused | 0.7916 | 13.9698 | 0.2180 |
| fused+popularity | 0.7944 | 13.9673 | 0.2130 |

## AUC by slice

cold = history length <= 40; head = clicked article with >= 72 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 2,725 | 0.5102 [0.4987, 0.5225] | 0.5351 [0.5243, 0.5465] | 0.5326 [0.5205, 0.5442] | 0.5869 [0.5746, 0.5987] |
| warm | 22,631 | 0.5128 [0.5087, 0.5171] | 0.5288 [0.5245, 0.5331] | 0.5297 [0.5255, 0.5341] | 0.5711 [0.5669, 0.5751] |
| head | 57 | 0.5908 [0.5141, 0.6607] | 0.7890 [0.7254, 0.8509] | 0.7771 [0.7125, 0.8333] | 0.8887 [0.8484, 0.9253] |
| tail | 25,299 | 0.5123 [0.5085, 0.5165] | 0.5289 [0.5250, 0.5327] | 0.5295 [0.5254, 0.5335] | 0.5721 [0.5684, 0.5761] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0108 [0.0095, 0.0122] | 0.0216 [0.0199, 0.0234] | 0.0390 [0.0368, 0.0413] |
| emb | 0.0072 [0.0061, 0.0082] | 0.0145 [0.0130, 0.0159] | 0.0266 [0.0246, 0.0286] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 2,725 | 0.0360 [0.0294, 0.0429] | 0.0220 [0.0165, 0.0272] | -0.0139 [-0.0228, -0.0055] | yes |
| warm | 22,631 | 0.0394 [0.0368, 0.0420] | 0.0272 [0.0251, 0.0292] | -0.0122 [-0.0152, -0.0090] | yes |
| head | 57 | 0.1078 [0.0351, 0.1930] | 0.0965 [0.0351, 0.1842] | -0.0113 [-0.1165, +0.1028] | no |
| tail | 25,299 | 0.0389 [0.0366, 0.0411] | 0.0265 [0.0243, 0.0284] | -0.0124 [-0.0154, -0.0095] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0170 [+0.0118, +0.0218] | yes |
| emb - bm25 (ndcg@10) | +0.0074 [+0.0036, +0.0109] | yes |
| fused - emb (auc) | +0.0005 [-0.0013, +0.0026] | no |
| fused - emb (ndcg@10) | +0.0015 [-0.0003, +0.0035] | no |
| fused - bm25 (auc) | +0.0175 [+0.0135, +0.0214] | yes |
| fused - bm25 (ndcg@10) | +0.0089 [+0.0059, +0.0117] | yes |
| fused+popularity - fused (auc) | +0.0427 [+0.0401, +0.0455] | yes |
| fused+popularity - fused (ndcg@10) | +0.0217 [+0.0195, +0.0241] | yes |
| emb - bm25 (recall@50) | -0.0037 [-0.0055, -0.0019] | yes |
| emb - bm25 (recall@100) | -0.0071 [-0.0094, -0.0050] | yes |
| emb - bm25 (recall@200) | -0.0124 [-0.0152, -0.0095] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.

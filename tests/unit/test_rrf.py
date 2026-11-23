from app.core.rrf import reciprocal_rank_fusion


def test_rrf_prefers_items_in_both_lists():
    fused = reciprocal_rank_fusion([[1, 2, 3], [2, 4, 1]], top_n=3)
    ids = [f.item_id for f in fused]
    assert ids[0] in {1, 2}

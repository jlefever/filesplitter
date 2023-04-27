import time

import pandas as pd
import scipy as sp
from sklearn.cluster import DBSCAN
from ordered_set import OrderedSet as oset

from filesplitter import ilp
from filesplitter.graph import group_by_scc, group_by_wcc, group_edges_by
from filesplitter.loading import Dataset
from filesplitter.naming import NameSimilarity

USE_INIT_TEXT_CLUSTERING = True
TEXT_EPS = 0.30
TEXT_MIN_PTS = 3
ALLOW_DUP_NAMES = True

USE_ALL = True
CUT_EPS = 1/2
MAX_WEIGHT = 16


# Big mess but it works
def to_name_cluster_labels(entities_df: pd.DataFrame, sim: NameSimilarity, labels: list[int]):
    label_dict = {}
    curr = max(*labels) + 1
    for _, row in entities_df.iterrows():
        if row["name"] in label_dict:
            continue
        if row["kind"] != "file":
            label = labels[sim.get_doc_ix(row["name"])]
            if label >= 0:
                label_dict[row["name"]] = label
                continue
        label_dict[row["name"]] = curr
        curr += 1
    res = []
    for _, row in entities_df.iterrows():
        res.append(label_dict[row["name"]])
    return res


# This function was extracted from a Jupyter notebook.
def cluster_dataset(ds: Dataset) -> pd.DataFrame:
    # ...
    entities_df = ds.entities_df()
    edges = oset((r["src_id"], r["tgt_id"]) for _, r in ds.deps_df().iterrows())

    if USE_INIT_TEXT_CLUSTERING:
        # Cluster by name
        similarity = NameSimilarity(list(ds.targets_df["name"]), allow_dup_names=ALLOW_DUP_NAMES)
        dbscan = DBSCAN(eps=TEXT_EPS, min_samples=TEXT_MIN_PTS, metric="precomputed")
        labels = dbscan.fit(similarity.dist_mat)
        entities_df["name_id"] = to_name_cluster_labels(entities_df, similarity, labels)
        
        # Print cluster info
        n_clusters = max(*labels) + 1
        max_cluster_len = sp.stats.mode([l for l in labels if l >= 0], keepdims=False).count
        print("Found {} text clusters with a max size of {}.".format(n_clusters, max_cluster_len))
    else:
        # Create a "name_id" for each entity that groups targets according to their name
        entities_df["name_id"] = entities_df.groupby("name").ngroup()

    # Create a "strong_id" for each entity that groups targets according the strongly connected componant of their name
    name_edges = group_edges_by(edges, entities_df["name_id"])
    entities_df["strong_id"] = group_by_scc(entities_df["name_id"], name_edges)

    # Create a "weak_id" for each entity that groups targets according the weakly connected componant of their strong_id
    strong_edges = group_edges_by(edges, entities_df["strong_id"])
    entities_df["weak_id"] = group_by_wcc(entities_df["strong_id"], strong_edges)

    # ...
    def get_entity_weight(id: int) -> int:
        kind = entities_df.loc[id]["kind"]
        return 0 if kind == "file" else 1

    def get_strong_weight(strong_id: int) -> int:
        ids = entities_df[entities_df["strong_id"] == strong_id].index
        return sum(get_entity_weight(id) for id in ids)

    def cluster(edges: set[tuple[int, int]], active: set[int], name: str) -> dict[int, str]:
        active_edges = set((a, b) for a, b in edges if a in active and b in active)
        
        density = len(active_edges) / len(active)
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        prefix = f"[{name}]".ljust(18) + f" ({timestamp})   "
        info = f"{len(active_edges)} edges and {len(active)} nodes = {density:0.4f} density"
        print(prefix + f"Starting... ({info})", end="\t")

        default_res = {i: name for i in active}

        if sum(get_strong_weight(strong_id) for strong_id in active) <= MAX_WEIGHT:
            print("Aborted. Weight under threshold.")
            return default_res

        def w(strong_id: int) -> int:
            if strong_id not in active:
                return 0
            return get_strong_weight(strong_id)

        # There are two ways to use `active`:
        # 1) Use ILP to bisect only the active elements
        #    - This might be faster.
        # 2) Use ILP to bisect all elements, but non-active elements are weighted to 0
        #    - This might produce better results.
        if USE_ALL:
            active_edges = edges

        start = time.perf_counter()
        cut_weight, labels = ilp.partition(list(active_edges), w, lambda i, j: 1, 2, CUT_EPS)
        if labels is None:
            print("Aborted. Failed to partition.")
            return default_res
        elapsed = time.perf_counter() - start
        print(f"Bisected with a cut weight of {cut_weight} in {elapsed:0.4f} secs.")

        active_A = active & {i for i, l in labels.items() if l == 0}
        active_B = active & {i for i, l in labels.items() if l == 1}
        res_A = cluster(edges, active_A, name + "A")
        res_B = cluster(edges, active_B, name + "B")
        return res_A | res_B
    
    # ...
    block_names = {}

    for weak_id in range(entities_df["weak_id"].max() + 1):
        # The strong_ids inside the current weakly connected component (wcc)
        wcc_nodes = set(entities_df[entities_df["weak_id"] == weak_id]["strong_id"])
        wcc_edges = {(a, b) for a, b in strong_edges if a in wcc_nodes and b in wcc_nodes}
        block_names |= cluster(wcc_edges, wcc_nodes, name=f"W{weak_id}")

    entities_df["block_name"] = [block_names.get(i) for i in entities_df["strong_id"]]
    entities_df["block_id"] = entities_df.groupby("block_name").ngroup()
    return entities_df

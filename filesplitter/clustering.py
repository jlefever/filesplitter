import time

import numpy as np
import pandas as pd
import scipy as sp
from sklearn.cluster import DBSCAN
from ordered_set import OrderedSet as oset

from filesplitter import ilp
from filesplitter.graph import group_by_scc, group_by_wcc, group_edges_by
from filesplitter.loading import Dataset
from filesplitter.naming import NameSimilarity

# This is the first round of clustering
USE_INIT_TEXT_CLX = False
TEXT_CLX_EPS = 0.30
TEXT_CLX_MIN_PTS = 3

# This is for use in the ILP portion
USE_TEXT_EDGES = True
TEXT_EDGE_MIN_SIM = 0.35 # or use percentile?
TEXT_EDGE_MULTIPLIER = 8

# This applies to any form of text comparison
ALLOW_DUP_NAMES = True

# All edges weights are multiplied by this then rounded to the nearest integer
UNIT_EDGE_WEIGTH = 512

# This is the call-based ILP portion
USE_ALL = True
CUT_EPS = 1/2
MAX_WEIGHT = 24


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


# For text edges
def group_sim(sim: NameSimilarity, a_names: list[str], b_names: list[str]) -> list[float]:
    weights = []
    for a_name in a_names:
        if not sim.has_doc(a_name):
            continue
        for b_name in b_names:
            if not sim.has_doc(b_name):
                continue
            weights.append(sim.sim(a_name, b_name))
    return weights


def min_group_sim(sim: NameSimilarity, a_names: list[str], b_names: list[str]):
    weights = group_sim(sim, a_names, b_names)
    return np.min(weights) if len(weights) != 0 else 0


def avg_group_sim(sim: NameSimilarity, a_names: list[str], b_names: list[str]):
    weights = group_sim(sim, a_names, b_names)
    return np.average(weights) if len(weights) != 0 else 0


def max_group_sim(sim: NameSimilarity, a_names: list[str], b_names: list[str]):
    weights = group_sim(sim, a_names, b_names)
    return np.max(weights) if len(weights) != 0 else 0


def build_txt_edges(entities_df: pd.DataFrame, sim: NameSimilarity) -> dict[tuple[int, int], float]:
    edges = {}
    nonfiles = entities_df[entities_df["kind"] != "file"]
    strong_names = nonfiles.groupby("strong_id")["name"].apply(list).to_dict()
    strong_ids = list(strong_names.keys())
    for a_ix in range(len(strong_ids)):
        a_names = strong_names[a_ix]
        for b_ix in range(a_ix + 1, len(strong_ids)):
            b_names = strong_names[b_ix]
            score = max_group_sim(sim, a_names, b_names)
            if score >= TEXT_EDGE_MIN_SIM:
                edges[(a_ix, b_ix)] = score
    return edges


# This function was extracted from a Jupyter notebook.
def cluster_dataset(ds: Dataset) -> pd.DataFrame:
    # ...
    entities_df = ds.entities_df()
    edges = oset((r["src_id"], r["tgt_id"]) for _, r in ds.deps_df().iterrows())

    # Create a text similarity thing (may not even use it)
    similarity = NameSimilarity(list(ds.targets_df["name"]), allow_dup_names=ALLOW_DUP_NAMES)

    if USE_INIT_TEXT_CLX:
        # Cluster by name
        dbscan = DBSCAN(eps=TEXT_CLX_EPS, min_samples=TEXT_CLX_MIN_PTS, metric="precomputed")
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
    txt_edge_weights = build_txt_edges(entities_df, similarity)
    txt_edges = set(txt_edge_weights.keys())

    # ...
    def get_entity_weight(id: int) -> int:
        kind = entities_df.loc[id]["kind"]
        return 0 if kind == "file" else 1

    def get_strong_weight(strong_id: int) -> int:
        ids = entities_df[entities_df["strong_id"] == strong_id].index
        return sum(get_entity_weight(id) for id in ids)

    def get_edge_weight(a_strong_id: int, b_strong_id: int) -> int:
        weight = 0
        key = (a_strong_id, b_strong_id)
        if key in strong_edges:
            weight += UNIT_EDGE_WEIGTH
        if USE_TEXT_EDGES and key in txt_edges:
            weight += round(txt_edge_weights[key] * UNIT_EDGE_WEIGTH * TEXT_EDGE_MULTIPLIER)
        return weight

    def cluster(dep_edges: set[tuple[int, int]], txt_edges: set[tuple[int, int]], active: set[int], name: str) -> dict[int, str]:
        active_dep_edges = set((a, b) for a, b in dep_edges if a in active and b in active)
        active_txt_edges = set((a, b) for a, b in txt_edges if a in active and b in active)
        
        # Print info
        active_edges = active_dep_edges | active_txt_edges
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
            active_dep_edges = dep_edges
            active_txt_edges = txt_edges

        start = time.perf_counter()
        if USE_TEXT_EDGES:
            cut_weight, labels = ilp.partition2(active_dep_edges, active_txt_edges, w, get_edge_weight, 2, CUT_EPS)
        else:
            cut_weight, labels = ilp.partition(list(active_dep_edges), w, lambda i, j: 1, 2, CUT_EPS)
        if labels is None:
            print("Aborted. Failed to partition.")
            return default_res
        elapsed = time.perf_counter() - start
        print(f"Bisected with a cut weight of {cut_weight} in {elapsed:0.4f} secs.")

        active_A = active & {i for i, l in labels.items() if l == 0}
        active_B = active & {i for i, l in labels.items() if l == 1}
        res_A = cluster(dep_edges, txt_edges, active_A, name + "A")
        res_B = cluster(dep_edges, txt_edges, active_B, name + "B")
        return res_A | res_B
    
    # ...
    block_names = {}

    for weak_id in range(entities_df["weak_id"].max() + 1):
        # The strong_ids inside the current weakly connected component (wcc)
        wcc_nodes = set(entities_df[entities_df["weak_id"] == weak_id]["strong_id"])
        wcc_dep_edges = {(a, b) for a, b in strong_edges if a in wcc_nodes and b in wcc_nodes}
        wcc_txt_edges = {(a, b) for a, b in txt_edges if a in wcc_nodes and b in wcc_nodes}
        block_names |= cluster(wcc_dep_edges, wcc_txt_edges, wcc_nodes, name=f"W{weak_id}")

    entities_df["block_name"] = [block_names.get(i) for i in entities_df["strong_id"]]
    entities_df["block_id"] = entities_df.groupby("block_name").ngroup()
    return entities_df

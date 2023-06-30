import os
from collections import defaultdict
from random import shuffle

import numpy as np
import pandas as pd

from filesplitter.dv8 import write_dsm, write_drh
from filesplitter.clustering import cluster_dataset
from filesplitter.loading import load_dataset


def count_blocks_touched(partition: dict[int, int], user_touches: set[int]) -> int:
    return len({partition[id] for id in user_touches})


def avg_blocks_touched(
    partition: dict[int, int], touches: dict[str, set[int]]
) -> float:
    return np.average([count_blocks_touched(partition, t) for _, t in touches.items()])


def get_sizes(partition: dict[int, int]) -> list[int]:
    inverted = defaultdict(set)
    for entity, block in partition.items():
        inverted[block].add(entity)
    return list(sorted((len(x) for x in inverted.values()), reverse=True))


def rand_partition(sizes: list[int], entities: set[int]) -> dict[int, int]:
    rand_order = list(entities)
    shuffle(rand_order)
    partition = {}
    curr = 0
    for block, size in enumerate(sizes):
        for entity in rand_order[curr : curr + size]:
            partition[entity] = block
        curr += size
    return partition


def calc_abpa(
    entities_df: pd.DataFrame, touches_df: pd.DataFrame
) -> tuple[float, float]:
    targets_df = entities_df.loc[~(entities_df["kind"] == "file")].copy()
    partition = {k: v for k, v in targets_df["block_id"].items()}

    # ...
    touches = defaultdict(set)
    for _, row in touches_df.iterrows():
        touches[row["author_email"]].add(row["entity_id"])

    # ...
    real = avg_blocks_touched(partition, touches)

    # ...
    sizes = get_sizes(partition)
    entities_set = set(partition.keys())

    # ...
    trials = [
        avg_blocks_touched(rand_partition(sizes, entities_set), touches)
        for _ in range(5_000)
    ]
    return (real, np.average(trials))


def calc_abpc(
    entities_df: pd.DataFrame, touches_df: pd.DataFrame
) -> tuple[float, float]:
    targets_df = entities_df.loc[~(entities_df["kind"] == "file")].copy()
    partition = {k: v for k, v in targets_df["block_id"].items()}

    # ...
    touches = defaultdict(set)
    for _, row in touches_df.iterrows():
        touches[row["sha1"]].add(row["entity_id"])

    # ...
    real = avg_blocks_touched(partition, touches)

    # ...
    sizes = get_sizes(partition)
    entities_set = set(partition.keys())

    # ...
    trials = [
        avg_blocks_touched(rand_partition(sizes, entities_set), touches)
        for _ in range(5_000)
    ]
    return (real, np.average(trials))


def validate_subjects(subjects: pd.DataFrame, data_dir: str, results_dir: str):
    if os.path.exists(results_dir):
        raise RuntimeError("the results dir '{}' already exists".format(results_dir))
    os.makedirs(results_dir)

    n_blocks = []
    real_ABPAs = []
    null_ABPAs = []
    real_ABPCs = []
    null_ABPCs = []

    for i, (_, row) in enumerate(subjects.iterrows()):
        subject_name = row["subject_name"]
        print("Working on Subject {}: {}".format(i, subject_name))
        ds = load_dataset(os.path.join(data_dir, row["project"] + ".db"), row["filename"])
        entities_df = cluster_dataset(ds)
        entities_df.to_csv(os.path.join(results_dir, "{}.csv".format(subject_name)))
        n_blocks.append(entities_df.groupby("block_name").ngroups)
        
        # Dump DV8 Data
        targets_df = entities_df.loc[~(entities_df["kind"] == "file")]
        dsm_path = os.path.join(results_dir, "{}.dsm.json".format(subject_name))
        write_dsm(dsm_path, subject_name, targets_df, ds.target_deps_df)
        drh_path = os.path.join(results_dir, "{}.drh.json".format(subject_name))
        write_drh(drh_path, subject_name + "-drh", targets_df)

        # Validate
        real_ABPA, null_ABPA = calc_abpa(entities_df, ds.touches_df)
        real_ABPAs.append(real_ABPA)
        null_ABPAs.append(null_ABPA)
        real_ABPC, null_ABPC = calc_abpc(entities_df, ds.touches_df)
        real_ABPCs.append(real_ABPC)
        null_ABPCs.append(null_ABPC)

    subjects["n_blocks"] = n_blocks

    subjects["real_ABPA"] = real_ABPAs
    subjects["null_ABPA"] = null_ABPAs
    subjects["real_ABPA_ratio"] = subjects["real_ABPA"] / subjects["n_blocks"]
    subjects["null_ABPA_ratio"] = subjects["null_ABPA"] / subjects["n_blocks"]

    subjects["real_ABPC"] = real_ABPCs
    subjects["null_ABPC"] = null_ABPCs
    subjects["real_ABPC_ratio"] = subjects["real_ABPC"] / subjects["n_blocks"]
    subjects["null_ABPC_ratio"] = subjects["null_ABPC"] / subjects["n_blocks"]

    subjects.to_csv(os.path.join(results_dir, "_summary.csv"))
from pathlib import Path
from collections import defaultdict
from random import shuffle

import numpy as np
import pandas as pd


def count_blocks_touched(partition: dict[int, int], user_touches: set[int]) -> int:
    return len({partition[id] for id in user_touches})


def avg_blocks_touched_by_user(
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


def validate(
    entities_df: pd.DataFrame, touches_df: pd.DataFrame
) -> tuple[float, float]:
    targets_df = entities_df.loc[~(entities_df["kind"] == "file")].copy()
    partition = {k: v for k, v in targets_df["block_id"].items()}

    # ...
    touches = defaultdict(set)
    for _, row in touches_df.iterrows():
        touches[row["author_email"]].add(row["entity_id"])

    # ...
    real = avg_blocks_touched_by_user(partition, touches)

    # ...
    sizes = get_sizes(partition)
    entities_set = set(partition.keys())

    # ...
    trials = [
        avg_blocks_touched_by_user(rand_partition(sizes, entities_set), touches)
        for _ in range(5_000)
    ]
    return (real, np.average(trials))

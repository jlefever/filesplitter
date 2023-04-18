import sqlite3
from dataclasses import dataclass

import pandas as pd

from filesplitter import db


@dataclass
class Dataset:
    targets_df: pd.DataFrame
    target_deps_df: pd.DataFrame
    clients_df: pd.DataFrame
    client_deps_df: pd.DataFrame
    outgoing_type_names: list[str]
    touches_df: pd.DataFrame

    def entities_df(self) -> pd.DataFrame:
        return pd.concat([self.targets_df, self.clients_df])

    def deps_df(self) -> pd.DataFrame:
        return pd.concat([self.target_deps_df, self.client_deps_df])


def load_dataset(db_path: str, filename: str) -> Dataset:
    with sqlite3.connect(db_path) as con:
        db.create_temp_tables(con)
        lead_ref_name = db.fetch_lead_ref_name(con)
        files_df = db.fetch_entities_by_name(con, filename)
        files_df = files_df[files_df["kind"] == "file"]
        if len(files_df) < 1:
            raise RuntimeError(f"No files named '{filename}' found")
        if len(files_df) > 1:
            raise RuntimeError(f"Too many files named '{filename}' found")
        top_id = int(files_df.iloc[0]["id"])
        targets_df = db.fetch_children(con, lead_ref_name, top_id)
        # If there is only one top level item (e.g. a Java class), skip to its children
        if len(targets_df) == 1:
            top_id = int(targets_df.index[0])
            targets_df = db.fetch_children(con, lead_ref_name, top_id)
        target_deps_df = db.fetch_internal_deps(con, str(top_id))
        clients_df = db.fetch_clients(con, filename)
        client_deps_df = db.fetch_client_deps(con, top_id, filename)
        outgoing_type_names = db.fetch_outgoing_type_names(con, top_id)
        touches_df = db.fetch_touches(con, lead_ref_name, top_id)
        return Dataset(
            targets_df,
            target_deps_df,
            clients_df,
            client_deps_df,
            outgoing_type_names,
            touches_df,
        )

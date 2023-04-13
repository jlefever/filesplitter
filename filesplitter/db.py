from pathlib import Path
import inspect
import pandas as pd
import sqlite3
from dataclasses import dataclass
from functools import cache


Con = sqlite3.Connection

QUERIES_PATH = Path(__file__).absolute().parent.joinpath("queries")


def _get_query(query_name: str) -> str:
    return QUERIES_PATH.joinpath(f"{query_name}.sql").read_text()


def _get_query_by_caller_name() -> str:
    func_name = inspect.stack()[1][3]
    return _get_query(func_name)


def create_temp_tables(con: Con):
    con.executescript(_get_query("_prelude"))


def fetch_candidate_files(con: Con, ref_name: str, min_locs: int) -> pd.DataFrame:
    params = {"ref_name": ref_name, "min_locs": min_locs}
    return pd.read_sql(_get_query_by_caller_name(), con, params=params)


def fetch_children(con: Con, ref_name: str, target_id: int) -> pd.DataFrame:
    params = {"ref_name": ref_name, "target_id": str(target_id)}
    return pd.read_sql(_get_query_by_caller_name(), con, index_col="id", params=params)


def fetch_client_deps(con: Con, target_id: int, target_file: str) -> pd.DataFrame:
    params = {"target_id": str(target_id), "target_file": target_file}
    return pd.read_sql(_get_query_by_caller_name(), con, params=params)


def fetch_clients(con: Con, target_file: str) -> pd.DataFrame:
    params = {"target_file": target_file}
    return pd.read_sql(_get_query_by_caller_name(), con, index_col="id", params=params)


def fetch_entities_by_name(con: Con, name: str) -> pd.DataFrame:
    params = {"name": name}
    return pd.read_sql(_get_query_by_caller_name(), con, params=params)


def fetch_internal_deps(con: Con, target_id: str) -> pd.DataFrame:
    params = {"target_id": target_id}
    return pd.read_sql(_get_query_by_caller_name(), con, params=params)


def fetch_outgoing_type_names(con: Con, target_id: int) -> list[str]:
    params = {"target_id": str(target_id)}
    return list(pd.read_sql(_get_query_by_caller_name(), con, params=params)["name"])


def fetch_refs(con: Con) -> pd.DataFrame:
    return pd.read_sql(_get_query_by_caller_name(), con)


def fetch_lead_ref_name(con: Con) -> str:
    return fetch_refs(con).iloc[0]["name"]


@dataclass
class Dataset:
    targets_df: pd.DataFrame
    target_deps_df: pd.DataFrame
    clients_df: pd.DataFrame
    client_deps_df: pd.DataFrame
    outgoing_type_names: list[str]

    @cache
    def entities_df(self) -> pd.DataFrame:
        return pd.concat([self.targets_df, self.clients_df])

    @cache
    def deps_df(self) -> pd.DataFrame:
        return pd.concat([self.target_deps_df, self.client_deps_df])


def load_dataset(db_path: str, filename: str) -> Dataset:
    with sqlite3.connect(db_path) as con:
        create_temp_tables(con)
        lead_ref_name = fetch_lead_ref_name(con)
        files_df = fetch_entities_by_name(con, filename)
        files_df = files_df[files_df["kind"] == "file"]
        if len(files_df) < 1:
            raise RuntimeError(f"No files named '{filename}' found")
        if len(files_df) > 1:
            raise RuntimeError(f"Too many files named '{filename}' found")
        top_id = int(files_df.iloc[0]["id"])
        targets_df = fetch_children(con, lead_ref_name, top_id)
        # If there is only one top level item (e.g. a Java class), skip to its children
        if len(targets_df) == 1:
            top_id = int(targets_df.index[0])
            targets_df = fetch_children(con, lead_ref_name, top_id)
        target_deps_df = fetch_internal_deps(con, str(top_id))
        clients_df = fetch_clients(con, filename)
        client_deps_df = fetch_client_deps(con, top_id, filename)
        outgoing_type_names = fetch_outgoing_type_names(con, top_id)
        return Dataset(
            targets_df, target_deps_df, clients_df, client_deps_df, outgoing_type_names
        )

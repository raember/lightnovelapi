import os
from typing import Dict


def make_sure_dir_exists(path: str):
    if not os.path.exists(path):
        os.makedirs(path)  # Don't use exists_ok=True; Might have '..' in path


def query_to_dict(query: str) -> Dict[str, str]:
    dic = {}
    for entry in query.split('&'):
        key, value = tuple(entry.split('='))
        dic[key] = value
    return dic

import os


def make_sure_dir_exists(path: str):
    if not os.path.exists(path):
        os.makedirs(path)  # Don't use exists_ok=True; Might have '..' in path

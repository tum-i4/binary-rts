import hashlib
from pathlib import Path


def hash_file(file_path: Path, algo: str = "sha256") -> str:
    """
    Computes the hash in chunks.

    :param file_path:
    :param algo: Hash function, possible values are sha1, sha256, or md5
    :return:
    """
    if algo == "sha1":
        h = hashlib.sha1()
    elif algo == "md5":
        h = hashlib.md5()
    else:
        h = hashlib.sha256()

    with file_path.open(mode="rb") as file:
        while True:
            # Reading is buffered, so we can read smaller chunks.
            chunk = file.read(h.block_size)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def hash_string(string: str, algo: str = "sha256") -> str:
    """
    Computes the hash for a string.

    :param string:
    :param algo: Hash function, possible values are sha1, sha256, or md5
    :return:
    """
    str_bytes: bytes = string.encode()
    if algo == "sha1":
        h = hashlib.sha1(str_bytes)
    elif algo == "md5":
        h = hashlib.md5(str_bytes)
    else:
        h = hashlib.sha256(str_bytes)
    return h.hexdigest()

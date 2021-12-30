import argparse
import base64
import hashlib
import os
import stat
from typing import Set

from hurry.filesize import size as size_str

CHUNK_SIZE = 1024 * 1024 * 32  # 32MB


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find files contained in [reference] that are missing in [test_directory]"
    )
    parser.add_argument(
        "reference_hashes_file", help="reference directory hashes file path"
    )
    parser.add_argument("test_hashes_file", help="test directory hashes file path")
    args = parser.parse_args()

    reference_hashes = set()  # type: Set[str]
    print("Reading reference file...")
    with open(args.reference_hashes_file, "r", encoding="utf-8") as hashes_file_handle:
        line_no = 0
        while True:
            line = hashes_file_handle.readline()
            if not line:
                break

            line_no += 1
            parts = line.split("  ")
            if len(parts) >= 3 and len(parts[0]) == 32:
                reference_hashes.add(parts[0])
            else:
                print(
                    "Problem on {} line {} ({})".format(
                        args.reference_hashes_file, line_no, line
                    )
                )

    print(
        "Reference file has {} lines and {} unique hashes".format(
            line_no,
            len(reference_hashes),
        )
    )

    print("Reading test file...")
    with open(args.test_hashes_file, "r", encoding="utf-8") as hashes_file_handle:
        line_no = 0
        while True:
            line = hashes_file_handle.readline()
            if not line:
                break

            line_no += 1
            parts = line.split("  ")
            if len(parts) >= 3 and len(parts[0]) == 32:
                if parts[0] in reference_hashes:
                    reference_hashes.remove(parts[0])
            else:
                print(
                    "Problem on {} line {} ({})".format(
                        args.test_hashes_file, line_no, line
                    )
                )

    if len(reference_hashes) == 0:
        print("No files are missing")
    else:
        print("{} unique files are missing:".format(len(reference_hashes)))

        with open(
            args.reference_hashes_file, "r", encoding="utf-8"
        ) as hashes_file_handle:
            while True:
                line = hashes_file_handle.readline()
                if not line:
                    break

                line_no += 1
                parts = line.split("  ")
                if parts[0] in reference_hashes:
                    missing_file = base64.b64decode(parts[2])
                    try:
                        print(missing_file.decode("utf-8"))
                    except:
                        print(
                            "(approx) " + missing_file.decode("utf-8", errors="ignore")
                        )

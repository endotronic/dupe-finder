import argparse
import base64
from os import makedirs, path
from shutil import copy2
from typing import Set


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Copy files produced by find_missing_files.py"
    )
    parser.add_argument("missing_files", help="file containing paths of files to copy")
    parser.add_argument(
        "source",
        help="source directory (indicates which subdirectories are needed in the destination)",
    )
    parser.add_argument(
        "destination", help="destination directory (subdirectories will be made)"
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        help="write to stdout instead of copying",
        action="store_true",
    )
    args = parser.parse_args()

    source_dir = path.normpath(args.source).encode("utf-8")
    destination_dir = path.abspath(args.destination).encode("utf-8")
    known_dirs = set()  # type: Set[bytes]

    with open(args.missing_files, "r", encoding="utf-8") as missing_items_file_handle:
        line_no = 0
        while True:
            line = missing_items_file_handle.readline()
            if not line:
                break

            line_no += 1
            try:
                missing_file_path = base64.b64decode(line)
                if path.commonpath([missing_file_path, source_dir]) != source_dir:
                    raise Exception(
                        "{} is not contained in source {}".format(
                            missing_file_path.decode("utf-8", "ignore"), source_dir
                        )
                    )

                rel = path.relpath(missing_file_path, source_dir)
                dest = path.normpath(path.join(destination_dir, rel))

                needed_paths = []
                parent = dest
                while True:
                    parent, child = path.split(parent)
                    if not child:
                        raise Exception(
                            "Problem with destionation "
                            + dest.decode("utf-8", "ignore")
                        )
                    if parent in known_dirs:
                        break
                    elif path.exists(parent):
                        known_dirs.add(parent)
                        break
                    else:
                        needed_paths.append(parent)

                if args.dry_run:
                    needed_paths.reverse()
                    for needed_path in needed_paths:
                        known_dirs.add(needed_path)
                        print("MKDIR")
                        print(needed_path.decode("utf-8", "ignore"))
                        print()

                    print("COPY")
                    print("FROM: " + missing_file_path.decode("utf-8", "ignore"))
                    print("  TO: " + dest.decode("utf-8", "ignore"))
                    print()
                else:
                    print("Copying {}...".format(rel.decode("utf-8", "ignore")))
                    makedirs(needed_paths[0], exist_ok=False)
                    copy2(missing_file_path, dest)  # type: ignore
            except Exception as e:
                print("problem on line {}: {}".format(line_no, e))

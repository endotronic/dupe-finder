import argparse
import base64
from os import path
from typing import Dict


def get_common_path(hashes_file: str) -> bytes:
    paths = []
    with open(hashes_file, "r", encoding="utf-8") as hashes_file_handle:
        line_no = 0
        while True:
            line = hashes_file_handle.readline()
            if not line:
                break

            line_no += 1
            parts = line.split("  ")
            if len(parts) >= 3 and len(parts[0]) == 32:
                path_bytes = base64.b64decode(parts[2])
                paths.append(path.dirname(path_bytes))
            else:
                raise Exception(
                    "Problem on {} line {} ({})".format(hashes_file, line_no, line)
                )

    return path.commonpath(paths)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find files contained in [reference] that are missing in [test_directory], requiring relative path to be the same"
    )
    parser.add_argument(
        "reference_hashes_file", help="reference directory hashes file path"
    )
    parser.add_argument("test_hashes_file", help="test directory hashes file path")
    parser.add_argument(
        "-o",
        "--output",
        help="output file path (optional)",
    )
    parser.add_argument(
        "-f",
        "--filenames-only",
        help="compare filenames only",
        action="store_true",
    )
    parser.add_argument(
        "--reference-path",
        help="path to reference; subpaths will be treated as relative",
    )
    parser.add_argument(
        "--test-path",
        help="path to test; subpaths will be treated as relative",
    )
    args = parser.parse_args()

    reference_path = bytes()
    if not args.reference_path:
        reference_path = get_common_path(args.reference_hashes_file)

    test_path = bytes()
    if not args.reference_path:
        test_path = get_common_path(args.test_hashes_file)

    print(
        "Assuming reference path {!r} and test path {!r}".format(
            reference_path, test_path
        )
    )

    if args.reference_path:
        reference_path = bytes(args.reference_path, encoding="utf-8")
        print("Reference path override: " + args.reference_path)

    if args.test_path:
        test_path = bytes(args.test_path, encoding="utf-8")
        print("Test path override: " + args.test_path)

    reference_files = dict()  # type: Dict[bytes, str]
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
                path_bytes = base64.b64decode(parts[2])
                if not path_bytes.startswith(reference_path):
                    continue

                relpath = path.relpath(path_bytes, start=reference_path)
                reference_files[relpath] = parts[0]
            else:
                message = "Problem on {} line {} ({})".format(
                    args.reference_hashes_file, line_no, line
                )
                raise Exception(message)
    print(
        "Reference file has {} lines and {} unique hashes".format(
            line_no,
            len(reference_files),
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
                path_bytes = base64.b64decode(parts[2])
                if not path_bytes.startswith(test_path):
                    continue

                relpath = path.relpath(path_bytes, start=test_path)
                if relpath in reference_files:
                    if args.filenames_only:
                        del reference_files[relpath]
                    else:
                        if reference_files[relpath] == parts[0]:
                            del reference_files[relpath]
                        else:
                            print("Hash mismatch on " + str(relpath))
            else:
                message = "Problem on {} line {} ({})".format(
                    args.reference_hashes_file, line_no, line
                )
                raise Exception(message)

    output_file = None
    if args.output:
        output_file = open(args.output, "w")
    try:
        if len(reference_files) == 0:
            print("No files are missing")
        else:
            print("{} files are missing".format(len(reference_files)))

            for filename in reference_files.keys():
                if output_file:
                    output_file.write(parts[2].strip() + "\n")

                try:
                    print(filename.decode("utf-8"))
                except:
                    print("(approx) " + filename.decode("utf-8", errors="ignore"))
    finally:
        if output_file:
            output_file.close()

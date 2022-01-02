import argparse
import base64
from typing import Set


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find files contained in [reference] that are missing in [test_directory]"
    )
    parser.add_argument(
        "reference_hashes_file", help="reference directory hashes file path"
    )
    parser.add_argument("test_hashes_file", help="test directory hashes file path")
    parser.add_argument(
        "-r",
        "--relaxed",
        help="skip any input lines with bad formatting instead of failing",
    )
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
                message = "Problem on {} line {} ({})".format(
                    args.reference_hashes_file, line_no, line
                )
                if args.relaxed:
                    print(message)
                else:
                    raise Exception(message)

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
                message = "Problem on {} line {} ({})".format(
                    args.reference_hashes_file, line_no, line
                )
                if args.relaxed:
                    print(message)
                else:
                    raise Exception(message)

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

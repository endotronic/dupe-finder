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
        "-o",
        "--output",
        help="output file path (optional)",
    )
    parser.add_argument(
        "-e",
        "--errors-file",
        help="file path to output errors (optional, v1 only)",
    )
    parser.add_argument(
        "-h",
        "--hashes-file",
        help="file path to output missing hashes (optional)",
    )
    parser.add_argument(
        "-r",
        "--relaxed",
        help="skip any input lines with bad formatting instead of failing",
        action="store_true",
    )
    parser.add_argument(
        "--silent-errors",
        help="don't report problems on stdout",
        action="store_true",
    )
    parser.add_argument(
        "-s",
        "--silent-warnings",
        help="don't report problems on stdout",
        action="store_true",
    )
    parser.add_argument(
        "--v1",
        help="v1: file contents contain two columns",
        action="store_true",
    )
    args = parser.parse_args()

    reference_hashes = set()  # type: Set[str]
    if not args.v1:
        print("Reading reference file...")
        with open(
            args.reference_hashes_file, "r", encoding="utf-8"
        ) as hashes_file_handle:
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
                        if not args.silent_errors:
                            print(message)
                    else:
                        raise Exception(message)
    else:

        errors_file = None
        if args.errors_file:
            errors_file = open(args.errors_file, "w")
        try:
            print("Reading reference file (v1 format)...")

            with open(args.reference_hashes_file, "rb") as hashes_file_handle:
                line_no = 0
                line = ""
                while True:
                    line_bytes = hashes_file_handle.readline()
                    if not line_bytes:
                        break

                    prev_line = line
                    try:
                        line = line_bytes.decode("utf-8", errors="strict").strip()
                    except:
                        line = line_bytes.decode("utf-8", errors="ignore").strip()
                        message = (
                            "WARN: Failed to decode {} line {} (approx {})".format(
                                args.reference_hashes_file, line_no, line
                            )
                        )
                        if not args.silent_warnings:
                            print(message)

                    if line[0] == "\\":
                        message = "WARN: Found {} line {} (approx {}) starts with slash. Ignoring slash.".format(
                            args.reference_hashes_file, line_no, line
                        )
                        if not args.silent_warnings:
                            print(message)
                        line = line[1:]

                    line_no += 1
                    parts = line.split("  ", 1)
                    if len(parts) == 2 and len(parts[0]) == 32:
                        reference_hashes.add(parts[0])
                    else:
                        message = "ERR: Problem on {} line {} ({})".format(
                            args.reference_hashes_file, line_no, line
                        )
                        if args.relaxed:
                            if not args.silent_errors:
                                if errors_file:
                                    errors_file.write(line + "\n")
                                else:
                                    print(message)
                        else:
                            raise Exception(message)
        finally:
            if errors_file:
                errors_file.close()

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

    if args.hashes_file:
        print("Preserving hashes...")
        with open(args.output, "w") as hashes_file:
            for hash in reference_hashes:
                hashes_file.write(hash + "\n")

    output_file = None
    if args.output:
        output_file = open(args.output, "w")
    try:
        if len(reference_hashes) == 0:
            print("No files are missing")
        else:
            print("{} unique files are missing:".format(len(reference_hashes)))

            if not args.v1:
                print("Re-reading reference file...")
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
                            if output_file:
                                output_file.write(parts[2].strip() + "\n")

                            missing_file = base64.b64decode(parts[2])
                            try:
                                print(missing_file.decode("utf-8"))
                            except:
                                print(
                                    "(approx) "
                                    + missing_file.decode("utf-8", errors="ignore")
                                )

            else:
                print("Re-reading reference file (v1 format)...")
                with open(args.reference_hashes_file, "rb") as hashes_file_handle:
                    line_no = 0
                    line = ""
                    while True:
                        line_bytes = hashes_file_handle.readline()
                        if not line_bytes:
                            break

                        line = line_bytes.decode("utf-8", errors="ignore").strip()
                        if line[0] == "\\":
                            line = line[1:]

                        line_no += 1
                        parts = line.split("  ", 1)
                        if parts[0] in reference_hashes:
                            missing_file = parts[1]
                            if output_file:
                                b64path = (
                                    base64.b64encode(missing_file)
                                    .decode("utf-8")
                                    .strip()
                                )
                                output_file.write(parts[1].strip() + "\n")

                            print(missing_file)
    finally:
        if output_file:
            output_file.close()

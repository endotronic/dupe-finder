import argparse
import base64
import hashlib
import os
import stat
from time import time

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


class DiskReader:
    def __init__(
        self, directory, hashes_file, sizes_file, rewrite, trust_all_hashes
    ) -> None:
        self.directory = directory
        self.hashes_file = hashes_file
        self.sizes_file = sizes_file
        self.rewrite = rewrite
        self.trust_all_hashes = trust_all_hashes

    def run(self):
        self.files_count = 0
        self.symlinks_count = 0
        self.others_count = 0
        self.total_size = 0
        self.errors_count = 0

        print("Producing:")
        if self.rewrite:
            print(hashes_file + " (rewriting)")
        else:
            print(hashes_file)
        if self.trust_all_hashes:
            print(sizes_file + " (ignoring)")
        elif self.rewrite:
            print(sizes_file + " (rewriting)")
        else:
            print(sizes_file)

        spaces = "".join([" " for _ in range(48)])

        known_hashes_dict = dict()
        if os.path.exists(hashes_file):
            print("Reading existing hashes file...")
            with open(hashes_file, "r", encoding="utf-8") as hashes_file_handle:
                while True:
                    line = hashes_file_handle.readline()
                    if not line:
                        break

                    parts = line.split("  ")
                    if len(parts) >= 3 and len(parts[0]) == 32:
                        b64path = parts[2].strip()
                        known_hashes_dict[b64path] = parts[0].strip()

        known_sizes_dict = dict()
        if os.path.exists(sizes_file) and not self.trust_all_hashes:
            print("Reading existing sizes file...")
            with open(sizes_file, "r", encoding="utf-8") as sizes_file_handle:
                while True:
                    line = sizes_file_handle.readline()
                    if not line:
                        break

                    parts = line.split("  ")
                    if len(parts) >= 3:
                        try:
                            b64path = parts[2].strip()
                            known_sizes_dict[b64path] = int(parts[0].strip())
                        except:
                            pass

        hashes_file_mode = "a" if len(known_hashes_dict) and not self.rewrite else "w"
        sizes_file_mode = "a" if len(known_sizes_dict) and not self.rewrite else "w"

        last_output = 0
        with open(
            hashes_file, hashes_file_mode, encoding="utf-8"
        ) as hashes_file_handle, open(
            sizes_file, sizes_file_mode, encoding="utf-8"
        ) as sizes_file_handle:
            try:
                print("Walking filesystem...")
                for root_bytes, dirs_bytes, files_bytes in os.walk(
                    str(self.directory).encode("utf-8"), onerror=self.on_error
                ):
                    for name_bytes in files_bytes:
                        path_bytes = os.path.join(root_bytes, name_bytes)
                        if os.path.islink(path_bytes):
                            self.symlinks_count += 1
                            continue

                        st_mode = os.stat(path_bytes).st_mode
                        if (
                            stat.S_ISBLK(st_mode)
                            or stat.S_ISCHR(st_mode)
                            or stat.S_ISFIFO(st_mode)
                            or stat.S_ISSOCK(st_mode)
                        ):
                            self.others_count += 1
                            continue

                        self.files_count += 1
                        fixed_path = path_bytes.decode("utf-8", errors="replace")
                        b64path = base64.b64encode(path_bytes).decode("utf-8").strip()

                        try:
                            path_bytes.decode("utf-8", errors="strict")
                            is_utf8 = "utf-8"
                        except:
                            is_utf8 = "unknown-encoding"

                        try:
                            size = os.path.getsize(path_bytes)
                            write_to_sizes_file = self.rewrite
                            hash_needs_refresh = not self.trust_all_hashes
                            if b64path in known_sizes_dict:
                                if known_sizes_dict[b64path] == size:
                                    hash_needs_refresh = False
                                else:
                                    write_to_sizes_file = True
                                del known_sizes_dict[b64path]
                            else:
                                write_to_sizes_file = True

                            self.total_size += size
                            if write_to_sizes_file:
                                sizes_file_handle.write(
                                    "{}  {}  {}\n".format(size, is_utf8, b64path)
                                )

                            write_to_hashes_file = self.rewrite
                            if b64path in known_hashes_dict and not hash_needs_refresh:
                                hash = known_hashes_dict[b64path]
                                del known_hashes_dict[b64path]
                            else:
                                write_to_hashes_file = True
                                with open(path_bytes, "rb") as f:
                                    size_read = 0
                                    hasher = hashlib.md5()
                                    while True:
                                        try:
                                            buf = f.read(CHUNK_SIZE)
                                        except KeyboardInterrupt:
                                            print("Stopped on " + fixed_path)
                                            raise

                                        size_read += len(buf)
                                        if not buf:
                                            break
                                        if size_read < size:
                                            display_filename = fixed_path
                                            if len(display_filename) > 30:
                                                display_filename = (
                                                    "..."
                                                    + fixed_path[len(fixed_path) - 27 :]
                                                )

                                            progress = "Reading {} ({}%). Completed {} in {} files...\r".format(
                                                display_filename,
                                                int(100 * size_read / size),
                                                size_str(self.total_size),
                                                self.files_count,
                                            )
                                            print(progress, end="")

                                        hasher.update(buf)

                                    hash = hasher.hexdigest()

                            if write_to_hashes_file:
                                hashes_file_handle.write(
                                    "{}  {}  {}\n".format(hash, is_utf8, b64path)
                                )

                        except Exception as error:
                            if isinstance(error, KeyboardInterrupt):
                                raise

                            self.errors_count += 1
                            try:
                                print(error.message)
                            except:
                                print(error)

                    now = int(time())
                    if now != last_output:
                        progress = "Working: {} in {} files with {} errors and {} ignored files...{}\r".format(
                            size_str(self.total_size),
                            self.files_count,
                            self.errors_count,
                            self.symlinks_count + self.others_count,
                            spaces,
                        )
                        print(progress, end="")
                        last_output = now

            except KeyboardInterrupt:
                print()
                print("Interrupted")
                if self.rewrite and (len(known_hashes_dict) or len(known_sizes_dict)):
                    print("Preserving existing hashes and sizes...")
                    for b64path, size in known_sizes_dict.items():
                        sizes_file_handle.write(
                            "{}  preserved  {}\n".format(size, b64path.strip())
                        )
                    for b64path, hash in known_hashes_dict.items():
                        hashes_file_handle.write(
                            "{}  preserved  {}\n".format(hash, b64path.strip())
                        )

        print()
        print("Files: {}".format(self.files_count))
        print("Skipped symlinks: {}".format(self.symlinks_count))
        print("Skipped block devices, FIFOs, etc: {}".format(self.others_count))
        print("Errors: {}".format(self.errors_count))

    def on_error(self, error):
        self.errors_count += 1
        try:
            print(error.message)
        except:
            print(error)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find hashes and sizes for dupe-finder"
    )
    parser.add_argument("directory", help="root directory for searching")
    parser.add_argument("-z", "--hashes_file", help="hashes file path")
    parser.add_argument("-s", "--sizes_file", help="sizes file path")
    parser.add_argument(
        "-r",
        "--rewrite",
        help="rewrite output files instead of appending",
        action="store_true",
    )
    parser.add_argument(
        "-t",
        "--trust-all-hashes",
        help="skip checking file sizes and trust all known hashes",
        action="store_true",
    )
    args = parser.parse_args()

    dirname = os.path.basename(args.directory)
    assert dirname

    hashes_file = dirname + "_files_hashes.txt"
    if args.hashes_file:
        hashes_file = args.hashes_file

    sizes_file = dirname + "_files_sizes.txt"
    if args.sizes_file:
        sizes_file = args.sizes_file

    hashes_file = os.path.abspath(hashes_file)
    sizes_file = os.path.abspath(sizes_file)

    reader = DiskReader(
        args.directory, hashes_file, sizes_file, args.rewrite, args.trust_all_hashes
    )
    reader.run()

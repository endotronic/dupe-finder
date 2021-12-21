import argparse
import hashlib
import os

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
        description="Find hashes and sizes for dupe-finder"
    )
    parser.add_argument("directory", help="root directory for searching")
    parser.add_argument("-z", "--hashes_file", help="hashes file path")
    parser.add_argument("-s", "--sizes_file", help="sizes file path")
    args = parser.parse_args()

    dirname = os.path.basename(args.directory)
    assert dirname

    hashes_file = dirname + "_files_hashes.txt"
    if args.hashes_file:
        hashes_file = args.hashes_file

    sizes_file = dirname + "_files_sizes.txt"
    if args.sizes_file:
        sizes_file = args.sizes_file

    errors_count = 0

    def on_error(error):
        errors_count += 1
        try:
            print(error.message)
        except:
            print(error)

    files_count = 0
    symlinks_count = 0
    total_size = 0

    hashes_file = os.path.abspath(hashes_file)
    sizes_file = os.path.abspath(sizes_file)
    print("Producing:")
    print(hashes_file)
    print(sizes_file)

    spaces = "".join([" " for _ in range(48)])

    with open(hashes_file, "w", encoding="utf-8") as hashes_file_handle, open(
        sizes_file, "w", encoding="utf-8"
    ) as sizes_file_handle:
        for root, dirs, files in os.walk(args.directory, onerror=on_error):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path):
                    symlinks_count += 1
                    continue

                files_count += 1

                try:
                    size = os.path.getsize(path)
                    total_size += size
                    sizes_file_handle.write("{}  {}\n".format(size, path))

                    with open(path, "rb") as f:
                        size_read = 0
                        hasher = hashlib.md5()
                        while True:
                            buf = f.read(CHUNK_SIZE)
                            size_read += len(buf)
                            if not buf:
                                break
                            if size_read < size:
                                display_filename = path
                                if len(display_filename) > 30:
                                    display_filename = "..." + path[len(path) - 27 :]

                                progress = "Reading {} ({}%). Completed {} in {} files with {} errors...\r".format(
                                    display_filename,
                                    int(100 * size_read / size),
                                    size_str(total_size),
                                    files_count,
                                    errors_count,
                                )
                                print(progress, end="")

                            hasher.update(buf)

                        hash = hasher.hexdigest()
                        hashes_file_handle.write("{}  {}\n".format(hash, path))

                except Exception as error:
                    errors_count += 1
                    try:
                        print(error.message)
                    except:
                        print(error)

            progress = "Working: {} in {} files with {} errors...{}\r".format(
                size_str(total_size),
                files_count,
                errors_count,
                spaces,
            )
            print(progress, end="")

    print()
    print("Files: {}".format(files_count))
    print("Skipped symlinks: {}".format(symlinks_count))
    print("Errors: {}".format(errors_count))

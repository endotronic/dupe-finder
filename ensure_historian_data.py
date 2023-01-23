import argparse
import base64
from os import path
from typing import Dict, Set


EXCLUDED_FILES = (
    b"config.yaml",
    b"content.yaml",
    b"praw.ini",
    b"historian.db",
    b"historian.db-journal",
    b".DS_Store",
    b"._.DS_Store",
    b"debug.log",
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find data contained in [reference] that is missing in [test_directory]"
    )
    parser.add_argument(
        "reference_hashes_file", help="reference directory hashes file path"
    )
    parser.add_argument("test_hashes_file", help="test directory hashes file path")
    parser.add_argument(
        "-s",
        "--test-symlinks",
        help="check for presence of posts and comments html in symlinks dir",
        action="store_true",
    )
    parser.add_argument(
        "-d",
        "--show-duplicate-ref-content",
        help="indicate when duplicate reference content was found",
        action="store_true",
    )
    parser.add_argument(
        "-e",
        "--show_extraneous_html",
        help="indicate when extraneous HTML found in reference",
        action="store_true",
    )
    args = parser.parse_args()

    reference_posts = dict()  # type: Dict[bytes, bytes]
    reference_comments = dict()  # type: Dict[bytes, bytes]
    reference_content = dict()  # type: Dict[bytes, bytes]
    reference_authors = dict()  # type: Dict[bytes, bytes]
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
                if path.basename(path_bytes) in EXCLUDED_FILES:
                    continue
                elif b"post binaries" in path_bytes:
                    reference_posts[path.basename(path_bytes)] = path_bytes
                elif b"post_binaries" in path_bytes:
                    reference_posts[path.basename(path_bytes)] = path_bytes
                elif b"comment binaries" in path_bytes:
                    reference_comments[path.basename(path_bytes)] = path_bytes
                elif b"historian/content" in path_bytes:
                    if b".thumb256.jpg" in path_bytes:
                        continue

                    content_hash = path.basename(path.dirname(path_bytes))
                    if path.basename(path_bytes) != b"record.yaml":
                        if content_hash.decode("utf-8") != parts[0]:
                            if path_bytes.endswith(b"Shortcut.lnk"):
                                print("Skipping accidental shortcut " + str(path_bytes))
                                continue
                            print(
                                "Hash does not match {}: {}".format(
                                    parts[0], str(path_bytes)
                                )
                            )
                            reference_content[parts[0].encode("utf-8")] = path_bytes
                            reference_content[content_hash] = path_bytes
                        if (
                            content_hash in reference_content
                            and args.show_duplicate_ref_content
                        ):
                            print("Content found twice: " + str(path_bytes))
                        reference_content[content_hash] = path_bytes
                elif b"author config" in path_bytes:
                    author, ext = path.splitext(path.basename(path_bytes))
                    if ext != b".yaml":
                        raise Exception("Unexpected extension in " + str(path_bytes))
                    reference_authors[author] = path_bytes
                elif b"/authors/" in path_bytes:
                    filename, ext = path.splitext(path.basename(path_bytes))
                    if ext == b".html":
                        if filename.startswith(b"comment"):
                            fparts = filename.split(b" ")
                            assert len(fparts) == 2 or (
                                len(fparts) == 3 and fparts[2] == b"(edited)"
                            )
                            reference_comments[fparts[1]] = path_bytes
                        else:
                            fparts = filename.split(b" ")
                            if len(fparts) > 1:
                                reference_posts[fparts[0]] = path_bytes
                            elif b"old" in path_bytes or b"OLD" in path_bytes:
                                # Old style
                                reference_comments[fparts[0]] = path_bytes
                            elif args.show_extraneous_html:
                                print("Don't understand file " + str(path_bytes))
                    else:
                        reference_content[filename] = path_bytes
                elif b"/posts/" in path_bytes or b"/subreddits/" in path_bytes:
                    filename, ext = path.splitext(path.basename(path_bytes))
                    if ext == b".html":
                        fparts = filename.split(b" ")
                        if len(fparts) > 1:
                            reference_posts[fparts[0]] = path_bytes
                        elif b"old" in path_bytes:
                            if args.show_extraneous_html:
                                print("Don't understand file " + str(path_bytes))
                        else:
                            raise Exception("Don't understand file " + str(path_bytes))
                    else:
                        reference_content[filename] = path_bytes
                elif b"thumbnails" in path_bytes:
                    continue
                elif path.basename(path.dirname(path_bytes)) == b"historian":
                    print("Skipping top level file " + str(path_bytes))
                else:
                    raise Exception("Path not expected: " + str(path_bytes))
            else:
                message = "Problem on {} line {} ({})".format(
                    args.reference_hashes_file, line_no, line
                )
                raise Exception(message)
    print(
        "Reference file has {} posts, {} comments, {} content items, and {} authors".format(
            len(reference_posts),
            len(reference_comments),
            len(reference_content),
            len(reference_authors),
        )
    )

    test_posts = dict()  # type: Dict[bytes, bytes]
    test_comments = dict()  # type: Dict[bytes, bytes]
    test_content = dict()  # type: Dict[bytes, bytes]
    test_authors = dict()  # type: Dict[bytes, bytes]
    symlink_posts = dict()  # type: Dict[bytes, bytes]
    symlink_comments = dict()  # type: Dict[bytes, bytes]
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
                if path.basename(path_bytes) in EXCLUDED_FILES:
                    continue
                elif b"historian/posts" in path_bytes:
                    test_posts[path.basename(path_bytes)] = path_bytes
                elif b"historian/comments" in path_bytes:
                    test_comments[path.basename(path_bytes)] = path_bytes
                elif b"historian/content" in path_bytes:
                    if b".thumb256.jpg" in path_bytes:
                        continue

                    content_hash = path.basename(path.dirname(path_bytes))
                    if path.basename(path_bytes) != b"record.yaml":
                        if content_hash.decode("utf-8") != parts[0]:
                            if path_bytes.endswith(b"Shortcut.lnk"):
                                print("Skipping accidental shortcut " + str(path_bytes))
                                continue
                            raise Exception(
                                "Hash does not match {}: {}".format(
                                    parts[0], str(path_bytes)
                                )
                            )
                        if content_hash in test_content:
                            raise Exception("Content found twice: " + str(path_bytes))
                        test_content[content_hash] = path_bytes
                elif b"historian/symlinks/" in path_bytes:
                    if b"symlinks/authors" in path_bytes:
                        filename, ext = path.splitext(path.basename(path_bytes))
                        if ext == b".html":
                            if filename.startswith(b"comment"):
                                fparts = filename.split(b" ")
                                assert len(fparts) == 2 or (
                                    len(fparts) == 3 and fparts[2] == b"(edited)"
                                )
                                symlink_comments[fparts[1]] = path_bytes
                            else:
                                fparts = filename.split(b" ")
                                if len(fparts) > 1:
                                    symlink_posts[fparts[0]] = path_bytes
                                else:
                                    raise Exception(
                                        "Don't understand file " + str(path_bytes)
                                    )
                        else:
                            raise Exception(
                                "Content file not expected: " + str(path_bytes)
                            )
                elif b"/authors/" in path_bytes:
                    author, ext = path.splitext(path.basename(path_bytes))
                    if ext != b".yaml":
                        raise Exception("Unexpected extension in " + str(path_bytes))
                    test_authors[author] = path_bytes
                elif path.basename(path.dirname(path_bytes)) == b"historian":
                    print("Skipping top level file " + str(path_bytes))
                else:
                    raise Exception("Path not expected: " + str(path_bytes))
            else:
                message = "Problem on {} line {} ({})".format(
                    args.test_hashes_file, line_no, line
                )
                raise Exception(message)

    print(
        "Test file has {} posts, {} comments, {} content items, and {} authors".format(
            len(test_posts),
            len(test_comments),
            len(test_content),
            len(test_authors),
        )
    )

    test_symlinks = args.test_symlinks
    print("Computing missing posts...")
    for ref_post, ref_path in reference_posts.items():
        if ref_post not in test_posts:
            str_post = ref_post.decode("utf-8")
            str_path = ref_path.decode("utf-8")
            print("Post {} from {} not in test directory".format(str_post, str_path))
        if test_symlinks and ref_post not in symlink_posts:
            str_post = ref_post.decode("utf-8")
            str_path = ref_path.decode("utf-8")
            print("Post {} from {} not in symlinks".format(str_post, str_path))

    print()
    print("Computing missing comments...")
    for ref_comment, ref_path in reference_comments.items():
        if ref_comment not in test_comments:
            str_comment = ref_comment.decode("utf-8")
            str_path = ref_path.decode("utf-8")
            print(
                "Comment {} from {} not in test directory".format(str_comment, str_path)
            )
        if test_symlinks and ref_comment not in symlink_posts:
            str_comment = ref_comment.decode("utf-8")
            str_path = ref_path.decode("utf-8")
            print("Comment {} from {} not in symlinks".format(str_comment, str_path))

    print()
    print("Computing missing content...")
    for ref_content_hash, ref_path in reference_content.items():
        if ref_content_hash not in test_content:
            str_content_hash = ref_content_hash.decode("utf-8")
            str_path = ref_path.decode("utf-8")
            print(
                "Content {} from {} not in test directory".format(
                    str_content_hash, str_path
                )
            )

    print()
    print("Done.")

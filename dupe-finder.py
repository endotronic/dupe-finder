from __future__ import annotations

from collections import defaultdict
import hashlib
from os import listdir, path, sep
import sys
from typing import Dict, List, Generator, Optional, Sequence, Set, Text, Tuple

import attr


@attr.s
class File:
    name = attr.ib(type=Text)
    absolute_path = attr.ib(type=Text)
    size = attr.ib(type=int)
    md5_hash_cache = attr.ib(type=Optional[int], default=None)
    parent_dir = attr.ib(type=Optional["Directory"], default=None)
    duplicates = attr.ib(type=Optional[Sequence["File"]], default=None)

    @classmethod
    def populate(cls, name: Text, absolute_path: Text) -> "File":
        size = path.getsize(absolute_path)
        return File(name, absolute_path, size)

    @property
    def data(self):
        # type: () -> bytes
        with open(self.absolute_path, "rb") as f:
            return f.read()

    @property
    def md5_hash(self):
        # type: () -> int
        if self.md5_hash_cache:
            return self.md5_hash_cache

        hasher = hashlib.md5()
        hasher.update(self.data)
        hex_digest = hasher.hexdigest()
        self.md5_hash_cache = int(hex_digest, 16)
        return self.md5_hash_cache


@attr.s
class Directory:
    name = attr.ib(type=Text)
    absolute_path = attr.ib(type=Text)
    files = attr.ib(type=List[File])
    subdirectories = attr.ib(type=List["Directory"])
    contained_hashes_cache = attr.ib(type=Optional[Set[int]], default=None)
    parent_dir = attr.ib(type=Optional["Directory"], default=None)
    entirely_duplicated_cache = attr.ib(type=Optional[bool], default=None)

    @property
    def contained_hashes(self) -> Set[int]:
        if self.contained_hashes_cache is not None:
            return self.contained_hashes_cache
        else:
            self.contained_hashes_cache = {
                file.md5_hash for file in self.files if file.md5_hash
            }
            for subdirectory in self.subdirectories:
                self.contained_hashes_cache.update(subdirectory.contained_hashes)

            return self.contained_hashes_cache

    @property
    def is_entirely_duplicated(self) -> bool:
        if self.entirely_duplicated_cache is not None:
            return self.entirely_duplicated_cache
        else:
            self.entirely_duplicated_cache = self._compute_is_entirely_duplicated()
            return self.entirely_duplicated_cache

    def _compute_is_entirely_duplicated(self) -> bool:
        for file in self.files:
            if not file.duplicates:
                return False

            if all([f.parent_dir == self for f in file.duplicates]):
                # unique file with only duplicates here
                return False

            if all([self.contains_recursive(f) for f in file.duplicates]):
                # It doesn't exist outside this subtree,
                # so we can't say this dir is entirely duped
                return False

        for subdirectory in self.subdirectories:
            if not subdirectory.is_entirely_duplicated:
                return False

        return True

    def contains_recursive(self, file: File) -> bool:
        if file.parent_dir == self:
            return True
        for subdirectory in self.subdirectories:
            if subdirectory.contains_recursive(file):
                return True
        return False

    @classmethod
    def populate(cls, absolute_path: Text, name: Optional[Text] = None) -> "Directory":
        files = []  # type: List[File]
        subdirectories = []  # type: List[Directory]

        fs_items = [Text(i) for i in listdir(absolute_path) if not i.startswith(".")]
        for fs_item in fs_items:
            item_path = path.join(absolute_path, fs_item)
            if path.isdir(item_path):
                subdir = cls.populate(item_path, fs_item)
                subdirectories.append(subdir)
            else:
                file = File.populate(item_path, fs_item)
                files.append(file)

        dir_name = name or path.dirname(absolute_path)
        dir = Directory(dir_name, absolute_path, files, subdirectories)
        for file in files:
            file.parent_dir = dir
        for subdir in subdirectories:
            subdir.parent_dir = dir
        return dir

    @classmethod
    def populate_from_records(
        cls, absolute_path: Text, sizes_file: Text, hashes_file: Text
    ) -> "Directory":
        dir_name = path.dirname(absolute_path)
        root_dir = Directory(dir_name, absolute_path, [], [])
        current_dir = root_dir

        hashes = {}  # Dict[Text, int]
        with open(hashes_file) as file_in:
            for line in file_in:
                hex_digest, _, file_path = line.strip().partition(" ")
                norm_path = path.normpath(file_path)
                hashes[norm_path] = int(hex_digest, 16)

        with open(sizes_file) as file_in:
            for line in file_in:
                size_str, _, file_path = line.strip().partition(" ")
                norm_path = path.normpath(file_path)
                assert norm_path in hashes, "Hash missing for file " + norm_path

                dir_path, filename = path.split(norm_path)
                file = File(filename, norm_path, 0)
                file.size = int(size_str)
                file.md5_hash_cache = hashes[norm_path]
                if path.normpath(dir_path) != current_dir.absolute_path:
                    current_dir = root_dir.recursive_make(dir_path)
                current_dir.files.append(file)
                file.parent_dir = current_dir

        return root_dir

    def get_files_recursive(self) -> Generator[File, None, None]:
        for file in self.files:
            yield file
        for subdirectory in self.subdirectories:
            for file in subdirectory.get_files_recursive():
                yield file

    def get_parents_recursive(self) -> Generator["Directory", None, None]:
        if self.parent_dir:
            yield self.parent_dir
            for ancestor in self.parent_dir.get_parents_recursive():
                yield ancestor

    def recursive_make(self, full_path: Text) -> "Directory":
        if self.absolute_path == full_path:
            return self

        normalized_path = path.normpath(full_path)
        norm_path_components = list(filter(None, normalized_path.split(sep)))
        this_path_components = list(filter(None, self.absolute_path.split(sep)))
        assert (
            norm_path_components[0 : len(this_path_components)] == this_path_components
        )
        missing_components = norm_path_components[len(this_path_components) :]
        return self.recursive_make_with_components(missing_components)

    def recursive_make_with_components(
        self, missing_components: List[Text]
    ) -> "Directory":
        if len(missing_components) == 0:
            return self

        for subdirectory in self.subdirectories:
            if subdirectory.name == missing_components[0]:
                return subdirectory.recursive_make_with_components(
                    missing_components[1:]
                )

        subdir_name = missing_components[0]
        subdir_path = path.join(self.absolute_path, subdir_name)
        new_dir = Directory(subdir_name, subdir_path, [], [])
        self.subdirectories.append(new_dir)
        new_dir.parent_dir = self
        return new_dir.recursive_make_with_components(missing_components[1:])


def file_dupes(
    root_path: Text, sizes_file: Optional[Text], hashes_file: Optional[Text]
) -> None:
    absolute_path = path.abspath(root_path)

    if sizes_file and hashes_file:
        root_dir = Directory.populate_from_records(root_path, sizes_file, hashes_file)
    else:
        root_dir = Directory.populate(absolute_path)

    # Group files by size
    files_by_size = defaultdict(list)
    for file in root_dir.get_files_recursive():
        files_by_size[file.size].append(file)

    # Group files by hash when same-sized files are found
    files_by_hash = defaultdict(list)
    for _, files in files_by_size.items():
        if len(files) < 2:
            continue
        for file in files:
            files_by_hash[file.md5_hash].append(file)

    # Find duplicate files
    dirs_with_dupes = dict()  # type: Dict[Text, Directory]
    duplicates_by_size_and_hash = defaultdict(
        list
    )  # type: Dict[Tuple[int, int], List[File]]
    for _, files in files_by_hash.items():
        if len(files) < 2:
            continue
        for file in files:
            file.duplicates = files

            assert file.parent_dir, "Found orphaned file"
            dirs_with_dupes[file.parent_dir.absolute_path] = file.parent_dir
            for parent in file.parent_dir.get_parents_recursive():
                dirs_with_dupes[parent.absolute_path] = parent

            key = (file.size, file.md5_hash)
            duplicates_by_size_and_hash[key].append(file)

    # Print duplicate files in order by size
    print("------ FILES ------")
    dupe_keys = sorted(duplicates_by_size_and_hash, reverse=True)
    for key in dupe_keys:
        size, hash = key
        files = duplicates_by_size_and_hash[key]
        print(
            "{} bytes ({}): \n{}\n".format(
                size, hash, ", ".join([file.absolute_path for file in files])
            )
        )

    # Print entirely duplicated directories
    print("--- DIRECTORIES ---")
    directories_and_sizes = list()  # type: List[Tuple[int, Directory]]
    for directory in dirs_with_dupes.values():
        if directory.is_entirely_duplicated and (
            not directory.parent_dir or not directory.parent_dir.is_entirely_duplicated
        ):
            total_size = sum([f.size for f in directory.get_files_recursive()])
            directories_and_sizes.append((total_size, directory))
    for total_size, directory in sorted(directories_and_sizes, reverse=True):
        if total_size:
            print(
                "{} entirely duplicated ({} bytes)".format(
                    directory.absolute_path, total_size
                )
            )
        else:
            num_files = len(list(directory.get_files_recursive()))
            print(
                "{} entirely duplicated ({} files)".format(
                    directory.absolute_path, num_files
                )
            )


if __name__ == "__main__":
    assert len(sys.argv) in (
        2,
        4,
    ), "Usage: dupe-finder.py <top-level dir> <sizes file> <hashes file>"
    # Sizes `file: find / -type f -exec du -b {} \; > sizes_file.txt `
    # Hashes file: `file: find / -type f -exec md5sum {} \; > hashes_file.txt `
    root_dir = sys.argv[1]

    hashes_file = sizes_file = None
    if len(sys.argv) == 4:
        sizes_file = sys.argv[2]
        hashes_file = sys.argv[3]

    file_dupes(root_dir, sizes_file, hashes_file)

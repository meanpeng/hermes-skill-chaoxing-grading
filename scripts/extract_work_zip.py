#!/usr/bin/env python3
"""
Extract Chaoxing work zip files across Windows, Linux, and macOS.

Chaoxing zip filenames are often encoded as GBK. Python 3.11+ supports
ZipFile(metadata_encoding=...), and this script falls back gracefully on older
Python versions.
"""

import argparse
import os
import sys
import zipfile


def parse_args():
    parser = argparse.ArgumentParser(description="Extract a Chaoxing work zip.")
    parser.add_argument("zip_file", help="Input zip file.")
    parser.add_argument("-d", "--output-dir", default="output_dir", help="Extraction directory.")
    parser.add_argument("--encoding", default="gbk", help="Filename encoding. Default: gbk")
    return parser.parse_args()


def safe_extract(zip_file, output_dir):
    base = os.path.abspath(output_dir)
    os.makedirs(base, exist_ok=True)
    for member in zip_file.infolist():
        target = os.path.abspath(os.path.join(base, member.filename))
        if os.path.commonpath([base, target]) != base:
            raise ValueError(f"Unsafe zip path: {member.filename}")
        zip_file.extract(member, base)


def open_zip(path, encoding):
    with zipfile.ZipFile(path) as probe:
        has_utf8_names = any(info.flag_bits & 0x800 for info in probe.infolist())
    if has_utf8_names:
        return zipfile.ZipFile(path)
    try:
        return zipfile.ZipFile(path, metadata_encoding=encoding)
    except TypeError:
        return zipfile.ZipFile(path)


def main():
    args = parse_args()
    with open_zip(args.zip_file, args.encoding) as zip_file:
        safe_extract(zip_file, args.output_dir)
    print(f"Extracted to {os.path.abspath(args.output_dir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

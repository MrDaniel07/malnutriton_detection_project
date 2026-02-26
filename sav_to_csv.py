#!/usr/bin/env python3
"""Convert SPSS .sav files to CSV files.

Usage examples:
  python sav_to_csv.py /path/to/file.sav
  python sav_to_csv.py /path/to/folder --recursive --labels --outdir csv_output

Options:
  --labels    : replace coded values with value labels when available
  --recursive : search folders recursively for .sav files
  --outdir    : output directory (defaults to same folder as input)
"""
import argparse
import os
import glob
import sys
import pyreadstat
import pandas as pd


def convert_file(sav_path, out_dir=None, apply_labels=False):
    sav_path = os.path.abspath(sav_path)
    base = os.path.splitext(os.path.basename(sav_path))[0]
    if out_dir is None:
        out_dir = os.path.dirname(sav_path)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, base + '.csv')

    print(f"Loading: {sav_path}")
    df, meta = pyreadstat.read_sav(sav_path)

    if apply_labels:
        # variable_to_value_labels maps variable -> value-label-set name
        vmap = getattr(meta, 'variable_to_value_labels', None) or getattr(meta, 'variable_value_labels', None) or {}
        valuesets = getattr(meta, 'value_labels', {})
        for var, labelset in (vmap.items() if isinstance(vmap, dict) else []):
            if var in df.columns:
                mapping = None
                # labelset may be a string key into value_labels, or the mapping itself
                if isinstance(labelset, str) and labelset in valuesets:
                    mapping = valuesets[labelset]
                elif isinstance(labelset, dict):
                    mapping = labelset
                if mapping:
                    # map coded values to labels; preserve NaNs
                    df[var] = df[var].map(mapping).where(~df[var].isna(), df[var])

    print(f"Writing: {out_path}")
    df.to_csv(out_path, index=False, encoding='utf-8')
    return out_path


def convert_folder(folder, out_dir=None, recursive=False, apply_labels=False):
    pattern = '**/*.sav' if recursive else '*.sav'
    files = glob.glob(os.path.join(folder, pattern), recursive=recursive)
    if not files:
        print('No .sav files found in', folder)
        return []
    out_files = []
    for f in files:
        try:
            out_files.append(convert_file(f, out_dir=out_dir or os.path.dirname(f), apply_labels=apply_labels))
        except Exception as e:
            print(f"Failed to convert {f}: {e}", file=sys.stderr)
    return out_files


def main():
    parser = argparse.ArgumentParser(description='Convert SPSS .sav files to CSV')
    parser.add_argument('input', help='Input .sav file or directory')
    parser.add_argument('--outdir', help='Output directory (optional)')
    parser.add_argument('--labels', action='store_true', help='Map coded values to value labels when available')
    parser.add_argument('--recursive', action='store_true', help='Search directories recursively')
    args = parser.parse_args()

    if os.path.isfile(args.input) and args.input.lower().endswith('.sav'):
        convert_file(args.input, out_dir=args.outdir, apply_labels=args.labels)
    elif os.path.isdir(args.input):
        convert_folder(args.input, out_dir=args.outdir, recursive=args.recursive, apply_labels=args.labels)
    else:
        print('Input must be a .sav file or a directory containing .sav files')


if __name__ == '__main__':
    main()

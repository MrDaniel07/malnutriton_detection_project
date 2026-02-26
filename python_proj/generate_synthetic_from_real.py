#!/usr/bin/env python3
"""Generate large synthetic CSV by resampling real filtered MICS rows.

This script reads `csv_output/filtered/combined_ch_lagos_ogun_under10.csv`,
resamples rows with replacement to produce a larger dataset, removes any
precomputed `any_mal` column (so the app computes malnutrition from z-scores),
and writes metadata indicating the growth reference context.
"""
import os
import json
import argparse
import pandas as pd


def main(input_path='csv_output/filtered/combined_ch_lagos_ogun_under10.csv', out_path='csv_output/large_synthetic.csv', n=20000, random_state=42):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    df = pd.read_csv(input_path, low_memory=False)
    if df.empty:
        raise ValueError('Input filtered dataset is empty')

    # Resample with replacement to create synthetic size
    sampled = df.sample(n=n, replace=True, random_state=random_state).reset_index(drop=True)

    # Ensure only Lagos/Ogun in HH7 (if HH7 is numeric code, set to 24/27 mapping)
    # Map any label variants to numeric codes if possible
    def map_state(v):
        if pd.isna(v):
            return v
        s = str(v).strip().lower()
        if 'lagos' in s:
            return 24
        if 'ogun' in s:
            return 27
        try:
            iv = int(float(v))
            if iv in (24, 27):
                return iv
        except Exception:
            pass
        # fallback: keep original
        return v

    if 'HH7' in sampled.columns:
        sampled['HH7'] = sampled['HH7'].apply(map_state)

    # Remove any precomputed label so model computes it from z-scores
    if 'any_mal' in sampled.columns:
        sampled = sampled.drop(columns=['any_mal'])

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    sampled.to_csv(out_path, index=False)

    # Write metadata
    meta = {
        'source': input_path,
        'n_rows': int(len(sampled)),
        'notes': 'Rows resampled with replacement from combined Lagos/Ogun filtered data',
        'growth_reference': 'WHO child growth standards (interpretation: West Africa context)',
        'HH7_mapping': {'Lagos': 24, 'Ogun': 27}
    }
    meta_path = out_path + '.meta.json'
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)

    print('Wrote', out_path)
    print('Wrote metadata', meta_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate synthetic CSV by resampling real MICS rows')
    parser.add_argument('--input', default='csv_output/filtered/combined_ch_lagos_ogun_under10.csv')
    parser.add_argument('--out', default='csv_output/large_synthetic.csv')
    parser.add_argument('--n', type=int, default=20000)
    args = parser.parse_args()
    main(input_path=args.input, out_path=args.out, n=args.n)

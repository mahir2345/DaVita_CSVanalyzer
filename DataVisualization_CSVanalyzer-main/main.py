"""
DaVita - AI-Powered Data Intelligence Platform

Original base structure: DataViz CSV Analyzer (unknown author)

Enhanced and Transformed by: Mahir
Copyright (c) 2026 Mahir. All Rights Reserved.

Major Enhancements & Transformations:
- AI-powered correlation analysis using Google Gemini
- Intelligent null-value handling with correlation preservation
- AI explanations and recommendations system
- Automated imputation strategy selection
- Real-time data quality assessment
- Renamed and rebranded as DaVita

This enhanced version constitutes a derivative work with substantial
original contributions. The AI features and correlation-aware null handling
are the intellectual property of Mahir.
"""

from flask import Flask, render_template, request, send_file, jsonify
import os
import sys
import json
import io
import threading
import time
from dotenv import load_dotenv

# Import webbrowser for auto-opening browser
import webbrowser

# Load environment variables from .env file
load_dotenv()

# Set matplotlib backend BEFORE importing pyplot
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

# Now import other libraries
import pandas as pd
import numpy as np
import seaborn as sns
from datetime import datetime
from itertools import combinations
import warnings
warnings.filterwarnings('ignore')

"""
NOTE: External AI (Google Gemini) has been removed.
All "AI" style explanations are now generated locally with simple heuristics.
This keeps the app completely free and offline-friendly.
"""

# Set environment variables for matplotlib
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'
plt.ioff()  # Turn off interactive mode

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Get absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
OUTPUT_DIR = os.path.join(STATIC_DIR, 'outputs')
TEMP_DIR = '/tmp/matplotlib'

# Create necessary directories with error handling
for directory in [STATIC_DIR, OUTPUT_DIR, TEMP_DIR]:
    try:
        os.makedirs(directory, exist_ok=True)
        os.chmod(directory, 0o777)  # Ensure write permissions
    except Exception as e:
        print(f"Warning: Could not create {directory}: {e}")

def infer_and_cast_dataframe(
    df: pd.DataFrame,
    *,
    numeric_min_non_null_ratio: float = 0.6,
    datetime_min_non_null_ratio: float = 0.6,
):
    """
    Robustly infer and cast column types for real-world CSVs.

    - Strips column name whitespace
    - Attempts numeric casting for "numeric-looking" object columns (handles commas, currency, %, parentheses)
    - Attempts datetime casting for "date-looking" columns
    - Detects boolean-like columns

    Returns: (cast_df, info)
      info = { 'numeric': [...], 'categorical': [...], 'datetime': [...], 'boolean': [...] }
    """
    working = df.copy()

    # Normalize column names
    working.columns = [str(c).strip() for c in working.columns]

    # Drop unnamed columns (common in Excel exports)
    unnamed = [c for c in working.columns if c.lower().startswith('unnamed:')]
    if unnamed:
        working = working.drop(columns=unnamed, errors='ignore')

    boolean_cols = []
    datetime_cols = []
    numeric_cols = []

    def _clean_numeric_text(s: pd.Series) -> pd.Series:
        # Convert to string safely, normalize, handle negatives in parentheses.
        t = s.astype(str).str.strip()
        t = t.replace({'': np.nan, 'nan': np.nan, 'None': np.nan, 'NULL': np.nan, 'null': np.nan})
        t = t.str.replace('\u00A0', ' ', regex=False).str.strip()
        # (123) -> -123
        t = t.str.replace(r'^\((.*)\)$', r'-\1', regex=True)
        # Remove common thousands separators, currency signs, and percent sign
        t = t.str.replace(',', '', regex=False)
        t = t.str.replace('$', '', regex=False).str.replace('€', '', regex=False).str.replace('£', '', regex=False).str.replace('৳', '', regex=False)
        t = t.str.replace('%', '', regex=False)
        return t

    def _is_boolean_like(s: pd.Series) -> bool:
        # Accepts common boolean tokens. Require most non-null values to be from the set.
        non_null = s.dropna()
        if non_null.empty:
            return False
        vals = non_null.astype(str).str.strip().str.lower().unique().tolist()
        allowed = {'true', 'false', 'yes', 'no', 'y', 'n', '0', '1', 't', 'f'}
        return set(vals).issubset(allowed) and len(set(vals)) <= 2

    def _to_boolean(s: pd.Series) -> pd.Series:
        m = {
            'true': True, 't': True, 'yes': True, 'y': True, '1': True,
            'false': False, 'f': False, 'no': False, 'n': False, '0': False,
        }
        return s.astype(str).str.strip().str.lower().map(m)

    for col in list(working.columns):
        series = working[col]

        # Already numeric
        if pd.api.types.is_numeric_dtype(series.dtype):
            numeric_cols.append(col)
            continue

        # Boolean-like (do this before numeric casting so '0/1' can be boolean when appropriate)
        if pd.api.types.is_object_dtype(series.dtype) or pd.api.types.is_string_dtype(series.dtype):
            if _is_boolean_like(series):
                working[col] = _to_boolean(series)
                boolean_cols.append(col)
                continue

        # Try datetime casting (only for non-numeric columns)
        try:
            dt = pd.to_datetime(series, errors='coerce')
            dt_ratio = float(dt.notna().mean()) if len(dt) else 0.0
            # Avoid converting integer-like IDs to timestamps (require at least 3 distinct parsed values)
            if dt_ratio >= datetime_min_non_null_ratio and dt.nunique(dropna=True) >= 3:
                working[col] = dt
                datetime_cols.append(col)
                continue
        except Exception:
            pass

        # Try numeric casting for object/string columns
        if pd.api.types.is_object_dtype(series.dtype) or pd.api.types.is_string_dtype(series.dtype):
            cleaned = _clean_numeric_text(series)
            num = pd.to_numeric(cleaned, errors='coerce')
            num_ratio = float(num.notna().mean()) if len(num) else 0.0
            if num_ratio >= numeric_min_non_null_ratio and num.nunique(dropna=True) > 1:
                working[col] = num
                numeric_cols.append(col)
                continue

    # Final type lists after casting
    numeric_cols = working.select_dtypes(include=[np.number]).columns.tolist()
    datetime_cols = working.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]']).columns.tolist()
    # Booleans: keep those we cast + native bool columns
    boolean_cols = sorted(set(boolean_cols + working.select_dtypes(include=['bool']).columns.tolist()))
    categorical_cols = [
        c for c in working.columns
        if c not in set(numeric_cols) | set(datetime_cols) | set(boolean_cols)
    ]

    info = {
        'numeric': numeric_cols,
        'categorical': categorical_cols,
        'datetime': datetime_cols,
        'boolean': boolean_cols,
    }

    return working, info

def read_csv_smart(file_storage) -> pd.DataFrame:
    """
    Robust CSV reader for real-world exports.

    Handles:
    - UTF-8 with BOM, cp1252
    - delimiter inference (comma/semicolon/tab/pipe)
    - Excel-style "title row" above the header (skips it if detected)
    - bad rows (skips if needed)
    """
    raw = file_storage.read()
    file_storage.seek(0)

    # Try common encodings
    last_err = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            text = raw.decode(enc)
            break
        except Exception as e:
            last_err = e
            text = None
    if text is None:
        raise ValueError(f"Could not decode CSV bytes. Last error: {last_err}")

    # Try separator inference (python engine required for sep=None)
    def _read(sep, skiprows=0):
        return pd.read_csv(
            io.StringIO(text),
            sep=sep,
            engine="python",
            skiprows=skiprows,
            on_bad_lines="skip",
        )

    # First attempt: auto-sep
    try:
        df = _read(sep=None, skiprows=0)
    except Exception:
        # Fallback: common separators
        for sep in [",", ";", "\t", "|"]:
            try:
                df = _read(sep=sep, skiprows=0)
                break
            except Exception:
                df = None

    if df is None:
        raise ValueError("Failed to parse CSV. Please verify file format.")

    # Detect "title row" issue:
    # If many column names are "Unnamed" OR very few non-null values in first data row,
    # and reading with skiprows=1 yields more meaningful headers, then skip first row.
    try:
        unnamed_ratio = sum(str(c).lower().startswith("unnamed") for c in df.columns) / max(1, len(df.columns))
        first_row_non_null = int(df.iloc[0].notna().sum()) if len(df) else 0

        if unnamed_ratio >= 0.5 or (len(df.columns) >= 4 and first_row_non_null <= 2):
            df2 = _read(sep=None, skiprows=1)
            # Keep df2 if it looks better (fewer unnamed cols and more reasonable header)
            unnamed_ratio2 = sum(str(c).lower().startswith("unnamed") for c in df2.columns) / max(1, len(df2.columns))
            if len(df2.columns) >= len(df.columns) and unnamed_ratio2 < unnamed_ratio:
                df = df2
    except Exception:
        pass

    # Trim string cells
    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col].dtype) or pd.api.types.is_string_dtype(df[col].dtype):
            df[col] = df[col].astype(str).str.strip().replace({'': np.nan, 'nan': np.nan})

    return df

def generate_visualizations(df, output_dir):
    """Generate all visualizations from the dataframe"""
    plots = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Force matplotlib to use Agg backend
        plt.switch_backend('Agg')
        
        # Set style with white background
        sns.set_style("whitegrid")
        plt.rcParams['figure.facecolor'] = 'white'
        plt.rcParams['axes.facecolor'] = 'white'
        plt.rcParams['text.color'] = 'black'
        plt.rcParams['axes.labelcolor'] = 'black'
        plt.rcParams['xtick.color'] = 'black'
        plt.rcParams['ytick.color'] = 'black'
        plt.rcParams['grid.color'] = '#e0e0e0'
        plt.rcParams['font.size'] = 10
        
    except Exception as e:
        print(f"Error setting matplotlib config: {e}")
    
    # Get numeric and categorical columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    print(f"Found {len(numeric_cols)} numeric columns and {len(categorical_cols)} categorical columns")
    
    # 1. Correlation Heatmap
    if len(numeric_cols) >= 2:
        try:
            fig, ax = plt.subplots(figsize=(10, 8))
            corr = df[numeric_cols].corr()
            sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", 
                       linewidths=0.5, linecolor="gray", square=True,
                       cbar_kws={"shrink": 0.8}, ax=ax)
            ax.set_title('Correlation Heatmap', fontsize=16, fontweight='bold', pad=20)
            plt.tight_layout()
            filename = f'heatmap_{timestamp}.png'
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            plots.append(('Correlation Heatmap', filename))
            print(f"Generated: {filename}")
        except Exception as e:
            print(f"Error generating heatmap: {e}")
    
    # 2. Distribution Histogram
    if len(numeric_cols) >= 1:
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            col = numeric_cols[0]
            sns.histplot(df[col].dropna(), bins=30, kde=True, color='skyblue', 
                        edgecolor='black', alpha=0.7, ax=ax)
            mean_val = df[col].mean()
            median_val = df[col].median()
            ax.axvline(mean_val, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.2f}')
            ax.axvline(median_val, color='blue', linestyle='-.', linewidth=2, label=f'Median: {median_val:.2f}')
            ax.set_title(f'Distribution of {col}', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel(col, fontsize=12)
            ax.set_ylabel('Frequency', fontsize=12)
            ax.legend(fontsize=10)
            ax.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            filename = f'histogram_{timestamp}.png'
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            plots.append(('Distribution Histogram', filename))
            print(f"Generated: {filename}")
        except Exception as e:
            print(f"Error generating histogram: {e}")
    
    # 3. Box Plot
    if len(numeric_cols) >= 1:
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            cols_to_plot = numeric_cols[:min(5, len(numeric_cols))]
            df[cols_to_plot].boxplot(patch_artist=True, ax=ax)
            ax.set_title('Box Plot - Outlier Detection', fontsize=16, fontweight='bold', pad=20)
            ax.set_ylabel('Values', fontsize=12)
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            ax.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            filename = f'boxplot_{timestamp}.png'
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            plots.append(('Box Plot', filename))
            print(f"Generated: {filename}")
        except Exception as e:
            print(f"Error generating boxplot: {e}")
    
    # 4. Scatter Plot
    if len(numeric_cols) >= 2:
        try:
            fig, ax = plt.subplots(figsize=(10, 8))
            x_col, y_col = numeric_cols[0], numeric_cols[1]
            colors = np.random.rand(len(df))
            sizes = 50
            scatter = ax.scatter(df[x_col], df[y_col], c=colors, s=sizes, 
                       cmap='viridis', alpha=0.6, edgecolors='black', linewidth=0.5)
            plt.colorbar(scatter, ax=ax, label='Color Scale')
            ax.set_title(f'Scatter Plot: {x_col} vs {y_col}', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel(x_col, fontsize=12)
            ax.set_ylabel(y_col, fontsize=12)
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            filename = f'scatter_{timestamp}.png'
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            plots.append(('Scatter Plot', filename))
            print(f"Generated: {filename}")
        except Exception as e:
            print(f"Error generating scatter plot: {e}")
    
    # 5. Bar Chart
    if len(categorical_cols) >= 1:
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            col = categorical_cols[0]
            value_counts = df[col].value_counts().head(10)
            colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(value_counts)))
            bars = ax.bar(range(len(value_counts)), value_counts.values, 
                          color=colors, edgecolor='black', linewidth=1.2)
            ax.set_xticks(range(len(value_counts)))
            ax.set_xticklabels(value_counts.index, rotation=45, ha='right')
            ax.set_title(f'Top Categories - {col}', fontsize=16, fontweight='bold', pad=20)
            ax.set_ylabel('Count', fontsize=12)
            ax.grid(axis='y', alpha=0.3)
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom', fontsize=10)
            plt.tight_layout()
            filename = f'barchart_{timestamp}.png'
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            plots.append(('Bar Chart', filename))
            print(f"Generated: {filename}")
        except Exception as e:
            print(f"Error generating bar chart: {e}")
    
    # 6. Line Plot
    if len(numeric_cols) >= 1:
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            col = numeric_cols[0]
            data_sample = df[col].dropna().head(100)
            ax.plot(range(len(data_sample)), data_sample.values, 
                    marker='o', linestyle='-', linewidth=2, markersize=4, color='purple')
            ax.set_title(f'Line Plot - {col}', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Index', fontsize=12)
            ax.set_ylabel(col, fontsize=12)
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            filename = f'lineplot_{timestamp}.png'
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            plots.append(('Line Plot', filename))
            print(f"Generated: {filename}")
        except Exception as e:
            print(f"Error generating line plot: {e}")
    
    # 7. Violin Plot
    if len(numeric_cols) >= 2:
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            cols_to_plot = numeric_cols[:min(4, len(numeric_cols))]
            data_to_plot = [df[col].dropna().values for col in cols_to_plot]
            parts = ax.violinplot(data_to_plot, showmeans=True, showmedians=True)
            ax.set_xticks(range(1, len(cols_to_plot) + 1))
            ax.set_xticklabels(cols_to_plot, rotation=45, ha='right')
            ax.set_title('Violin Plot - Distribution Comparison', fontsize=16, fontweight='bold', pad=20)
            ax.set_ylabel('Values', fontsize=12)
            ax.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            filename = f'violin_{timestamp}.png'
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            plots.append(('Violin Plot', filename))
            print(f"Generated: {filename}")
        except Exception as e:
            print(f"Error generating violin plot: {e}")
    
    # 8. KDE Plot
    if len(numeric_cols) >= 1:
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            cols = numeric_cols[:min(3, len(numeric_cols))]
            for col in cols:
                sns.kdeplot(df[col].dropna(), fill=True, alpha=0.5, linewidth=2, label=col, ax=ax)
            ax.set_title('KDE Plot - Density Distribution', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Value', fontsize=12)
            ax.set_ylabel('Density', fontsize=12)
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            filename = f'kde_{timestamp}.png'
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            plots.append(('KDE Plot', filename))
            print(f"Generated: {filename}")
        except Exception as e:
            print(f"Error generating KDE plot: {e}")
    
    print(f"Successfully generated {len(plots)} plots")
# 12. Advanced Box Plot with Swarm
    if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
        try:
            cat_col = categorical_cols[0]
            num_col = numeric_cols[0]
            sample_df = df.sample(n=min(500, len(df)))
            fig, ax = plt.subplots(figsize=(12, 7), facecolor='white')

            sns.boxplot(
                x=cat_col,
                y=num_col,
                data=sample_df,
                palette='Set2',
                ax=ax,
                linewidth=2,
                notch=True
        )

            sns.swarmplot(
                x=cat_col,
                y=num_col,
                data=sample_df,
                color='black',
                alpha=0.4,
                size=3,
                ax=ax
        )

            ax.set_title(
            f'Advanced Box Plot with Swarm: {cat_col} vs {num_col}',
            fontsize=16,
            fontweight='bold',
            pad=20
        )
            ax.tick_params(axis='x', rotation=45)
            ax.set_xlabel(cat_col, fontsize=12)
            ax.set_ylabel(num_col, fontsize=12)
            ax.grid(axis='y', linestyle='--', alpha=0.3)

            plt.tight_layout()
            filename = f'box_swarm_{timestamp}.png'
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)

            plots.append(('Box Plot with Swarm', filename))
            print(f"Generated: {filename}")

        except Exception as e:
            print(f"Error generating Box Plot with Swarm: {e}")

    




    
# 15. Strip Plot
    if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
        try:
            cat_col = categorical_cols[0]
            num_col = numeric_cols[0]
            sample_df = df.sample(n=min(500, len(df)))

            fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')

            sns.stripplot(
            x=cat_col,
            y=num_col,
            data=sample_df,
            jitter=0.3,
            size=6,
            palette='Set1',
            alpha=0.7,
            ax=ax
        )

            ax.set_title(
            f'Strip Plot: {cat_col} vs {num_col}',
            fontsize=16,
            fontweight='bold',
            pad=20
        )
            ax.set_xlabel(cat_col, fontsize=12)
            ax.set_ylabel(num_col, fontsize=12)
            ax.tick_params(axis='x', rotation=45)
            ax.grid(axis='y', linestyle='--', alpha=0.3)

            plt.tight_layout()
            filename = f'strip_{timestamp}.png'
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)

            plots.append(('Strip Plot', filename))
            print(f"Generated: {filename}")

        except Exception as e:
            print(f"Error generating Strip Plot: {e}")


    


    # 18. Count Plot
    if len(categorical_cols) >= 1:
        try:
            cat_col = categorical_cols[0]

            fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')

        # Get top 10 categories
            order = df[cat_col].value_counts().head(10).index

            sns.countplot(
            y=cat_col,
            data=df,
            palette='viridis',
            ax=ax,
            order=order
        )

        # Annotate counts
            for p in ax.patches:
                width = p.get_width()
                ax.text(
                width + 0.5,
                p.get_y() + p.get_height()/2,
                int(width),
                ha='left',
                va='center',
                fontsize=10,
                fontweight='bold',
                color='black'
            )

            ax.set_title(
            f'Count Plot: {cat_col}',
            fontsize=16,
            fontweight='bold',
            pad=20
        )
            ax.set_xlabel('Count', fontsize=12)
            ax.set_ylabel(cat_col, fontsize=12)
            ax.grid(axis='x', linestyle='--', alpha=0.3)

            plt.tight_layout()
            filename = f'count_{timestamp}.png'
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)

            plots.append(('Count Plot', filename))
            print(f"Generated: {filename}")

        except Exception as e:
            print(f"Error generating Count Plot: {e}")

# 19. Area Plot
    if len(numeric_cols) >= 1:
        try:
            fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')

        # Plot top 3 numeric columns
            for col in numeric_cols[:3]:
                ax.fill_between(df.index, df[col], alpha=0.5, label=col)
                ax.plot(df.index, df[col], linewidth=2)

            ax.set_title(
            'Area Plot - Trends',
            fontsize=16,
            fontweight='bold',
            pad=20
        )
            ax.set_xlabel('Index', fontsize=12)
            ax.set_ylabel('Values', fontsize=12)
            ax.legend()
            ax.grid(True, linestyle='--', alpha=0.3)

            plt.tight_layout()
            filename = f'area_{timestamp}.png'
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)

            plots.append(('Area Plot', filename))
            print(f"Generated: {filename}")

        except Exception as e:
            print(f"Error generating Area Plot: {e}")

    




# 24. KDE Plot 2D
    if len(numeric_cols) >= 2:
        try:
            fig, ax = plt.subplots(figsize=(10, 8), facecolor='white')

            sns.kdeplot(
            x=df[numeric_cols[0]],
            y=df[numeric_cols[1]],
            fill=True,
            cmap='viridis',
            levels=15,
            thresh=0.05,
            ax=ax
        )

            ax.set_title(
            f'2D KDE Plot: {numeric_cols[0]} vs {numeric_cols[1]}',
            fontsize=16,
            fontweight='bold',
            pad=20
        )
            ax.set_xlabel(numeric_cols[0], fontsize=12)
            ax.set_ylabel(numeric_cols[1], fontsize=12)
            ax.grid(True, linestyle='--', alpha=0.3)

            plt.tight_layout()
            filename = f'kde2d_{timestamp}.png'
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)

            plots.append(('KDE Plot 2D', filename))
            print(f"Generated: {filename}")

        except Exception as e:
            print(f"Error generating KDE Plot 2D: {e}")






    
    return plots


def apply_imputation(df, method):
    """Impute missing values using the specified method."""
    working_df = df.copy()
    numeric_cols = working_df.select_dtypes(include=[np.number]).columns
    categorical_cols = working_df.select_dtypes(include=['object', 'category']).columns

    if method == 'drop_rows':
        return working_df.dropna()

    if method in {'ffill', 'bfill'}:
        # pandas 2.x: fillna(method=...) removed; use ffill()/bfill()
        if method == 'ffill':
            working_df = working_df.ffill().bfill()
        else:
            working_df = working_df.bfill().ffill()
    else:
        if method == 'mean':
            working_df[numeric_cols] = working_df[numeric_cols].fillna(working_df[numeric_cols].mean())
        elif method == 'median':
            working_df[numeric_cols] = working_df[numeric_cols].fillna(working_df[numeric_cols].median())
        elif method == 'mode':
            mode_values = working_df[numeric_cols].mode().iloc[0] if not working_df[numeric_cols].mode().empty else {}
            working_df[numeric_cols] = working_df[numeric_cols].fillna(mode_values)

        # For categorical/text columns, default to mode; fallback to 'Unknown' if no mode
        for col in categorical_cols:
            if working_df[col].isnull().any():
                mode_series = working_df[col].mode()
                fill_value = mode_series.iloc[0] if not mode_series.empty else 'Unknown'
                working_df[col] = working_df[col].fillna(fill_value)

    return working_df


def handle_missing_values(df, strategy='auto'):
    """Handle missing values based on a chosen strategy with correlation awareness."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    baseline_missing = int(df.isnull().sum().sum())

    # If no missing values, return early
    if baseline_missing == 0:
        return df, {
            'strategy_requested': strategy,
            'strategy_used': 'none',
            'reason': 'No missing values detected',
            'baseline_missing': baseline_missing,
            'post_missing': 0,
            'per_column': {}
        }

    per_column_missing = {
        col: int(df[col].isnull().sum())
        for col in df.columns
        if df[col].isnull().any()
    }

    # If no numeric columns, fall back to mode for categorical data
    if not numeric_cols:
        filled = apply_imputation(df, 'mode')
        return filled, {
            'strategy_requested': strategy,
            'strategy_used': 'mode',
            'reason': 'No numeric columns found; mode imputation applied to categorical data',
            'baseline_missing': baseline_missing,
            'post_missing': int(filled.isnull().sum().sum()),
            'per_column': per_column_missing
        }

    # Baseline correlation for comparison
    baseline_corr = df[numeric_cols].corr()

    if strategy != 'auto':
        filled = apply_imputation(df, strategy)
        return filled, {
            'strategy_requested': strategy,
            'strategy_used': strategy,
            'reason': 'User-selected strategy applied',
            'baseline_missing': baseline_missing,
            'post_missing': int(filled.isnull().sum().sum()),
            'per_column': per_column_missing
        }

    candidate_methods = ['mean', 'median', 'mode', 'ffill', 'bfill']
    best_method = None
    best_score = float('inf')

    def corr_score(corr):
        return np.nanmean(np.abs(corr - baseline_corr))

    for method in candidate_methods:
        filled_candidate = apply_imputation(df, method)
        candidate_corr = filled_candidate[numeric_cols].corr()
        score = corr_score(candidate_corr)
        if score < best_score:
            best_score = score
            best_method = method

    filled = apply_imputation(df, best_method)

    reason = (
        f"Auto-selected '{best_method}' imputation to preserve correlations "
        f"(avg correlation shift: {best_score:.4f})."
    )

    return filled, {
        'strategy_requested': strategy,
        'strategy_used': best_method,
        'reason': reason,
        'baseline_missing': baseline_missing,
        'post_missing': int(filled.isnull().sum().sum()),
        'per_column': per_column_missing
    }


def compute_correlation_insights(df, top_n=5, threshold=0.3):
    """Return top correlated column pairs with brief insights."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) < 2:
        return []

    corr = df[numeric_cols].corr()
    pairs = []
    for col_a, col_b in combinations(numeric_cols, 2):
        value = corr.loc[col_a, col_b]
        if pd.isna(value):
            continue
        if abs(value) >= threshold:
            direction = 'positive' if value > 0 else 'negative'
            pairs.append({
                'pair': f'{col_a} vs {col_b}',
                'value': float(round(value, 3)),
                'direction': direction,
                'strength': 'strong' if abs(value) >= 0.7 else 'moderate'
            })

    pairs.sort(key=lambda x: abs(x['value']), reverse=True)
    return pairs[:top_n]


def generate_ai_explanation(df, null_report, correlation_insights):
    """Generate a local, free-of-cost AI-style explanation of the data.

    This implementation is fully offline and does NOT call any external APIs.
    """
    try:
        rows = len(df)
        cols = len(df.columns)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

        # Missing value info
        baseline_missing = null_report.get('baseline_missing', int(df.isnull().sum().sum()))
        post_missing = null_report.get('post_missing', int(df.isnull().sum().sum()))
        strategy_used = null_report.get('strategy_used', 'none')
        reason = null_report.get('reason', '')

        # Correlation summary
        corr_summary_lines = []
        if correlation_insights:
            for item in correlation_insights:
                corr_summary_lines.append(
                    f"- {item['pair']}: {item['direction']} ({item['strength']}), r = {item['value']}"
                )
        else:
            corr_summary_lines.append(
                "- Not enough numeric columns to compute meaningful correlations."
            )

        corr_block = "\n".join(corr_summary_lines)

        explanation = f"""AI Analysis Summary (Local, Free)

Data Overview
- Total rows: {rows:,}
- Total columns: {cols}
- Numeric columns: {len(numeric_cols)} ({', '.join(numeric_cols) if numeric_cols else 'none'})
- Categorical columns: {len(categorical_cols)} ({', '.join(categorical_cols) if categorical_cols else 'none'})

Missing Value Handling
- Strategy used: **{strategy_used}**
- Reason: {reason}
- Missing values before processing: {baseline_missing}
- Missing values after processing: {post_missing}

Correlation Highlights
{corr_block}

Practical Suggestions
- Use the correlation heatmap and matrix to visually confirm the strongest relationships.
- Pay special attention to highly correlated numeric pairs when building KPIs or forecasting models.
- Columns with many missing values or weak correlations are often better candidates for basic reporting, not predictive modelling.
- If the dataset represents time or sequence data, try line plots on key numeric columns to see trends or seasonality.

Note
This explanation is generated locally using simple heuristics on your data. It is completely free to run and does not require any API keys or internet access.
"""

        return {
            'success': True,
            'error': None,
            'explanation': explanation
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Local AI explanation failed: {str(e)}',
            'explanation': None
        }

def get_imputation_recommendations(df, baseline_corr):
    """Get local, heuristic recommendations for imputation strategy (no external AI)."""
    try:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Get missing value info
        missing_info = {}
        for col in df.columns:
            null_count = int(df[col].isnull().sum())
            if null_count > 0:
                null_pct = round(null_count / len(df) * 100, 2)
                missing_info[col] = {
                    'count': null_count,
                    'percentage': null_pct,
                    'dtype': str(df[col].dtype)
                }
        
        if not missing_info:
            return "No missing values detected. Imputation is not required for this dataset."
        
        # Get correlation matrix info
        corr_info = {}
        if len(numeric_cols) >= 2:
            corr_matrix = df[numeric_cols].corr()
            for col in missing_info:
                if col in numeric_cols:
                    col_corrs = corr_matrix[col].dropna().drop(col, errors='ignore')
                    if len(col_corrs) > 0:
                        top_corrs = col_corrs.abs().nlargest(3).to_dict()
                        corr_info[col] = {k: round(v, 3) for k, v in top_corrs.items()}
        # Basic heuristic recommendation
        total_missing = int(df.isnull().sum().sum())
        high_missing_cols = {
            col: info for col, info in missing_info.items() if info['percentage'] >= 20
        }

        recommended = "auto"
        reasoning = []

        if any(info['percentage'] > 40 for info in missing_info.values()):
            recommended = "drop_rows"
            reasoning.append(
                "- Some columns have more than 40% missing values. Dropping rows is often safer than heavy imputation."
            )
        elif len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
            recommended = "mean"
            reasoning.append(
                "- Mixed numeric and categorical data detected. Mean (numeric) + mode (categorical) is a balanced default."
            )
        elif len(numeric_cols) >= 1 and not categorical_cols:
            recommended = "median"
            reasoning.append(
                "- Purely numeric dataset. Median is robust to outliers and preserves central tendency."
            )

        if corr_info:
            reasoning.append(
                "- Several numeric columns show meaningful correlations. Prefer imputation strategies that preserve relative differences (mean/median/auto)."
            )

        if not reasoning:
            reasoning.append(
                "- Missing values are relatively small and spread out; any standard strategy will likely work."
            )

        recommendation_text = f"""Local Imputation Recommendations (No External AI)

Quick Summary
- Total rows: {len(df)}
- Total missing values: {total_missing}
- Columns with missing values: {len(missing_info)}
- Recommended strategy: **{recommended}**

Details by Column
{json.dumps(missing_info, indent=2)}

Correlation Context (numeric columns)
{json.dumps(corr_info, indent=2) if corr_info else "Not enough numeric data for correlation-based guidance."}

Reasoning
{chr(10).join(reasoning)}

Notes
- These recommendations are generated locally using deterministic rules.
- You can still override the strategy in the UI if you have domain-specific preferences.
"""

        return recommendation_text
        
    except Exception as e:
        print(f"Error getting imputation recommendations: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    return jsonify({
        # Always report AI as "configured" because we now use a local,
        # free-of-cost explanation system that does not depend on API keys.
        'gemini_configured': True,
        'ai_mode': 'local'
    })

@app.route('/get-recommendations', methods=['POST'])
def get_recommendations():
    """Get AI recommendations for imputation strategy before analysis."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Only CSV files are allowed'}), 400
        
        df = read_csv_smart(file)
        df, _type_info = infer_and_cast_dataframe(df)
        
        if df.empty:
            return jsonify({'success': False, 'error': 'CSV file is empty'}), 400
        
        # Get baseline correlation
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        baseline_corr = df[numeric_cols].corr() if len(numeric_cols) >= 2 else None
        
        # Get AI recommendations
        recommendations = get_imputation_recommendations(df, baseline_corr)
        
        # Get missing value summary
        missing_summary = {}
        for col in df.columns:
            null_count = int(df[col].isnull().sum())
            if null_count > 0:
                missing_summary[col] = {
                    'count': null_count,
                    'percentage': round(null_count / len(df) * 100, 2)
                }
        
        return jsonify({
            'success': True,
            'total_missing': int(df.isnull().sum().sum()),
            'missing_by_column': missing_summary,
            'ai_recommendations': recommendations
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        print("Starting analysis...")
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Only CSV files are allowed'}), 400
        
        # Read CSV
        print("Reading CSV file...")
        df = read_csv_smart(file)
        df, type_info = infer_and_cast_dataframe(df)
        print(f"CSV loaded: {len(df)} rows, {len(df.columns)} columns")
        
        # Validate dataframe
        if df.empty:
            return jsonify({'success': False, 'error': 'CSV file is empty'}), 400
        
        # Handle missing values with correlation-aware strategy
        null_strategy = request.form.get('null_strategy', 'auto')
        print(f"Applying missing value strategy: {null_strategy}")
        processed_df, null_report = handle_missing_values(df, null_strategy)

        # Re-infer types after imputation (imputation can change dtypes)
        processed_df, processed_type_info = infer_and_cast_dataframe(processed_df)
        numeric_cols = processed_type_info['numeric']
        categorical_cols = processed_type_info['categorical']
        datetime_cols = processed_type_info['datetime']
        boolean_cols = processed_type_info['boolean']

        # Generate visualizations on processed data
        print("Generating visualizations...")
        plots = generate_visualizations(processed_df, OUTPUT_DIR)
        print(f"Generated {len(plots)} plots successfully")
        
        # Get basic stats
        stats = {
            'rows': int(len(processed_df)),
            'columns': int(len(processed_df.columns)),
            'numeric_cols': int(len(numeric_cols)),
            'categorical_cols': int(len(categorical_cols)),
            'missing_values_before': int(df.isnull().sum().sum()),
            'missing_values_after': int(processed_df.isnull().sum().sum())
        }

        # Full correlation matrix for numeric columns
        correlation_matrix = None
        if len(numeric_cols) >= 2:
            corr_df = processed_df[numeric_cols].corr().round(3)
            correlation_matrix = {
                'columns': corr_df.columns.tolist(),
                'data': corr_df.values.tolist()
            }

        correlation_insights = compute_correlation_insights(processed_df)
        
        # Generate AI explanation
        ai_result = generate_ai_explanation(processed_df, null_report, correlation_insights)
        
        print(f"Returning response with {len(plots)} plots")
        return jsonify({
            'success': True,
            'plots': plots,
            'stats': stats,
            'null_handling': null_report,
            'correlation_insights': correlation_insights,
            'correlation_matrix': correlation_matrix,
            'columns': {
                'all': processed_df.columns.tolist(),
                'numeric': numeric_cols,
                'categorical': categorical_cols,
                'datetime': datetime_cols,
                'boolean': boolean_cols
            },
            'ai_explanation': ai_result
        })
    
    except Exception as e:
        print(f"Error in analyze route: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/download/<filename>')
def download(filename):
    try:
        filepath = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/custom-plot', methods=['POST'])
def custom_plot():
    """Generate a user-selected plot from the uploaded CSV."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Only CSV files are allowed'}), 400

        # Read CSV (use same logic as main analysis)
        df = read_csv_smart(file)
        df, _type_info = infer_and_cast_dataframe(df)

        if df.empty:
            return jsonify({'success': False, 'error': 'CSV file is empty'}), 400

        # Handle missing values consistently
        null_strategy = request.form.get('null_strategy', 'auto')
        processed_df, _ = handle_missing_values(df, null_strategy)
        processed_df, _processed_type_info = infer_and_cast_dataframe(processed_df)

        plot_type = request.form.get('plot_type', 'histogram')
        x_col = request.form.get('x_col')
        y_col = request.form.get('y_col')

        if plot_type in {'histogram', 'line'} and not x_col:
            return jsonify({'success': False, 'error': 'Please select a column for the plot.'}), 400
        if plot_type in {'scatter', 'box', 'bar'} and (not x_col or not y_col):
            return jsonify({'success': False, 'error': 'Please select both X and Y columns for this plot type.'}), 400

        # Ensure columns exist
        for col in filter(None, [x_col, y_col]):
            if col not in processed_df.columns:
                return jsonify({'success': False, 'error': f'Column "{col}" not found in dataset.'}), 400

        # Create plot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'custom_{plot_type}_{timestamp}.png'
        filepath = os.path.join(OUTPUT_DIR, filename)

        plt.switch_backend('Agg')

        try:
            fig, ax = plt.subplots(figsize=(10, 6))

            if plot_type == 'histogram':
                sns.histplot(processed_df[x_col].dropna(), bins=30, kde=True, ax=ax, color='skyblue')
                ax.set_title(f'Histogram of {x_col}')
                ax.set_xlabel(x_col)
                ax.set_ylabel('Frequency')

            elif plot_type == 'scatter':
                ax.scatter(processed_df[x_col], processed_df[y_col], alpha=0.6, edgecolors='black')
                ax.set_title(f'Scatter: {x_col} vs {y_col}')
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)

            elif plot_type == 'line':
                ax.plot(processed_df[x_col].index, processed_df[x_col].values, marker='o', linewidth=2)
                ax.set_title(f'Line Plot of {x_col}')
                ax.set_xlabel('Index')
                ax.set_ylabel(x_col)

            elif plot_type == 'box':
                sns.boxplot(x=processed_df[x_col], y=processed_df[y_col], ax=ax)
                ax.set_title(f'Box Plot: {y_col} by {x_col}')
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)

            elif plot_type == 'bar':
                grouped = processed_df.groupby(x_col)[y_col].mean().sort_values(ascending=False).head(20)
                grouped.plot(kind='bar', ax=ax, color='mediumpurple')
                ax.set_title(f'Bar Plot (mean {y_col} by {x_col})')
                ax.set_xlabel(x_col)
                ax.set_ylabel(f'Mean {y_col}')

            else:
                return jsonify({'success': False, 'error': f'Unsupported plot type: {plot_type}'}), 400

            plt.tight_layout()
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)

        except Exception as e:
            plt.close('all')
            return jsonify({'success': False, 'error': f'Failed to generate plot: {str(e)}'}), 500

        title_map = {
            'histogram': f'Histogram of {x_col}',
            'scatter': f'Scatter: {x_col} vs {y_col}',
            'line': f'Line Plot of {x_col}',
            'box': f'Box Plot: {y_col} by {x_col}',
            'bar': f'Bar Plot (mean {y_col} by {x_col})',
        }

        return jsonify({
            'success': True,
            'filename': filename,
            'title': title_map.get(plot_type, 'Custom Plot'),
            'plot_type': plot_type
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500


@app.route('/focus-analysis', methods=['POST'])
def focus_analysis():
    """
    Given a focus column, compute how it relates to other columns:
    - numeric focus -> correlations vs all other numeric columns
    - categorical focus -> mean of each numeric column per category
    """
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Only CSV files are allowed'}), 400

        df = read_csv_smart(file)
        df, _type_info = infer_and_cast_dataframe(df)
        if df.empty:
            return jsonify({'success': False, 'error': 'CSV file is empty'}), 400

        null_strategy = request.form.get('null_strategy', 'auto')
        focus_col = request.form.get('focus_col')
        if not focus_col:
            return jsonify({'success': False, 'error': 'No focus column provided'}), 400

        if focus_col not in df.columns:
            return jsonify({'success': False, 'error': f'Column \"{focus_col}\" not found in dataset.'}), 400

        processed_df, _ = handle_missing_values(df, null_strategy)
        processed_df, _processed_type_info = infer_and_cast_dataframe(processed_df)

        col_dtype = processed_df[focus_col].dtype
        is_numeric = pd.api.types.is_numeric_dtype(col_dtype)

        relationships = []

        if is_numeric:
            # Correlations vs all other numeric columns
            numeric_cols = processed_df.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) <= 1:
                return jsonify({
                    'success': True,
                    'focus_col': focus_col,
                    'focus_type': 'numeric',
                    'relationships': [],
                    'summary': 'Only one numeric column present; no correlations to compute.'
                })

            corr = processed_df[numeric_cols].corr()
            if focus_col not in corr.columns:
                return jsonify({
                    'success': True,
                    'focus_col': focus_col,
                    'focus_type': 'numeric',
                    'relationships': [],
                    'summary': 'Could not compute correlations for the selected column.'
                })

            series = corr[focus_col].drop(labels=[focus_col], errors='ignore').dropna()
            for other, value in series.items():
                relationships.append({
                    'other_column': other,
                    'metric': 'correlation',
                    'value': float(round(value, 3))
                })

            relationships.sort(key=lambda x: abs(x['value']), reverse=True)

            summary = (
                f'Numeric focus column \"{focus_col}\" has strongest relationships (by correlation) '
                f'with the columns listed below. Values close to 1/-1 mean strong positive/negative relationships.'
            )

            return jsonify({
                'success': True,
                'focus_col': focus_col,
                'focus_type': 'numeric',
                'relationships': relationships,
                'summary': summary
            })

        else:
            # Categorical focus -> group means for each numeric column
            numeric_cols = processed_df.select_dtypes(include=[np.number]).columns.tolist()
            if not numeric_cols:
                return jsonify({
                    'success': True,
                    'focus_col': focus_col,
                    'focus_type': 'categorical',
                    'relationships': [],
                    'summary': 'No numeric columns found to summarize per category.'
                })

            # Limit to top categories (otherwise UI/JSON can explode on large datasets)
            # Top by frequency, up to 25 categories.
            top_categories = (
                processed_df[focus_col]
                .astype(str)
                .value_counts()
                .head(25)
                .index
                .tolist()
            )

            filtered = processed_df[processed_df[focus_col].astype(str).isin(top_categories)].copy()
            grouped = filtered.groupby(filtered[focus_col].astype(str))[numeric_cols].mean().reset_index()
            grouped = grouped.rename(columns={grouped.columns[0]: focus_col})

            # Build a tidy structure: for each numeric col, list category -> mean
            for num_col in numeric_cols:
                values = []
                for _, row in grouped.iterrows():
                    values.append({
                        'category': str(row[focus_col]),
                        'mean_value': float(round(row[num_col], 3))
                    })
                relationships.append({
                    'other_column': num_col,
                    'metric': 'mean_by_category',
                    'values': values
                })

            summary = (
                f'Categorical focus column \"{focus_col}\" is used to group the data. '
                f'For each numeric column, you can see the average value per category (top 25 categories by frequency).'
            )

            return jsonify({
                'success': True,
                'focus_col': focus_col,
                'focus_type': 'categorical',
                'relationships': relationships,
                'summary': summary
            })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    print("="*60)
    print("DaVita - AI Data Analyzer - Starting Server")
    print("="*60)
    print(f"Python version: {sys.version}")
    print(f"Matplotlib backend: {matplotlib.get_backend()}")
    print(f"Base directory: {BASE_DIR}")
    print(f"Static directory: {STATIC_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Temp directory: {TEMP_DIR}")
    print("="*60)
    
    # Verify directories exist and are writable
    for dir_name, dir_path in [("Static", STATIC_DIR), ("Output", OUTPUT_DIR), ("Temp", TEMP_DIR)]:
        if os.path.exists(dir_path):
            print(f"[OK] {dir_name} directory exists: {dir_path}")
            if os.access(dir_path, os.W_OK):
                print(f"[OK] {dir_name} directory is writable")
            else:
                print(f"[WARN] {dir_name} directory is NOT writable")
        else:
            print(f"[WARN] {dir_name} directory does NOT exist")
    
    print("="*60)
    
    # Start Flask server in background thread
    def run_flask():
        app.run(debug=False, port=5000, host='127.0.0.1', use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Wait for server to be ready, then open browser
    time.sleep(2)
    
    url = 'http://127.0.0.1:5000'
    print("\n[INFO] Starting DaVita server...")
    print(f"[INFO] Opening browser at {url}...")
    print("="*60)
    
    # Open browser automatically
    webbrowser.open(url)
    
    # Keep Flask running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down DaVita...")
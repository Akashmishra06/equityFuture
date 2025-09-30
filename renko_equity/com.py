import os
import pandas as pd

def combine_close_csvs(parent_dir, output_file="another.csv"):
    all_dfs = []
    
    # Sort subdirs numerically if they are like 1,2,3...
    subdirs = sorted([d for d in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, d))],
                     key=lambda x: int(x) if x.isdigit() else x)
    
    for subdir in subdirs:
        subdir_path = os.path.join(parent_dir, subdir)
        
        # Find file starting with "close"
        for file in os.listdir(subdir_path):
            if file.startswith("close") and file.endswith(".csv"):
                file_path = os.path.join(subdir_path, file)
                df = pd.read_csv(file_path)
                all_dfs.append(df)
                break  # Only one file per subdir
    
    # Concatenate all and write to output
    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        final_df.to_csv(output_file, index=False)
        print(f"Combined CSV written to: {output_file}")
    else:
        print("No matching CSV files found.")

# Example usage:
combine_close_csvs("/root/equityFuture/renko_equity/BacktestResults/AM_Renko_v1", "another.csv")

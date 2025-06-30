import arcpy
import os
import csv
import numpy as np
from arcpy.sa import Raster
import matplotlib.pyplot as plt
import pandas as pd

arcpy.env.overwriteOutput = True

basins = ["WestDelaware", "ElkCreek", "TownBrooke"]
years = [1996, 2001, 2006, 2010, 2016, 2021]
input_dir = r"D:\Ashok\Catskills_Project\Outputs"
output_dir = input_dir
nodata_val = -999  # Buffwidmax NoData value

def width_freq():
    for basin in basins:
        result_dict = {}  # {BufferWidth: {Year: Count}}

        for year in years:
            raster_path = os.path.join(input_dir, basin, f"Buffer_{basin}_{year}__buffwidmax.tif")
            if not arcpy.Exists(raster_path):
                print(f"Missing raster for {basin}-{year}")
                continue

            arr = arcpy.RasterToNumPyArray(raster_path)
            arr = arr[arr != nodata_val]  # Filter NoData

            values, counts = np.unique(arr, return_counts=True)

            for val, count in zip(values, counts):
                if val not in result_dict:
                    result_dict[val] = {}
                result_dict[val][year] = count

        # Write output CSV
        csv_path = os.path.join(input_dir, f"{basin}_buffwidmax_counts_wide.csv")
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            header = ['BufferWidth'] + years
            writer.writerow(header)

            for val in sorted(result_dict.keys()):
                row = [val]
                for year in years:
                    row.append(result_dict[val].get(year, 0))
                writer.writerow(row)

        print(f"Saved: {csv_path}")

def maxwidthchange_plot():
    base_year = "1996"
    # Use a nicer color palette
    colors = plt.get_cmap("Set2").colors  # Up to 8 distinct colors

    for basin in basins:
        csv_path = os.path.join(input_dir, f"{basin}_buffwidmax_counts_wide.csv")
        df = pd.read_csv(csv_path)

        # Remove -999 (NoData)
        df = df[df["BufferWidth"] != -999]

        # Set BufferWidth as index
        df.set_index("BufferWidth", inplace=True)

        # Compute % change from base year
        base_counts = df[base_year]
        pct_change = df.subtract(base_counts, axis=0).divide(base_counts.replace(0, pd.NA), axis=0) * 100

        # Plot
        ax = pct_change.plot(
            kind='bar',
            figsize=(12, 6),
            width=0.8,
            color=colors[:len(pct_change.columns)]
        )
        ax.set_title(f"Percent Change in Buffer Width Class Count (from {base_year}) - {basin}", fontsize=14)
        ax.set_ylabel("Percent Change (%)", fontsize=12)
        ax.set_xlabel("Buffer Width (pixels)", fontsize=12)
        ax.axhline(0, color='black', linewidth=0.8)
        ax.legend(title="Year")
        plt.xticks(rotation=0)
        plt.tight_layout()

        # Save the figure
        fig_path = os.path.join(input_dir, f"{basin}_BufferWidth_PctChange.png")
        plt.savefig(fig_path, dpi=300)
        print(f"Saved: {fig_path}")
        plt.close()


def buildup_count():

    for basin in basins:
        data = []
        for year in years:
            # Buffered path
            buffer_raster = os.path.join(input_dir, basin, f"Buffer_{basin}_{year}__buildup_ag_and_urban.tif")
            nobuffer_raster = os.path.join(input_dir, basin, f"NoBuffer_{basin}_{year}__buildup_ag_and_urban.tif")

            # Initialize counts
            buffer_count = None
            nobuffer_count = None

            for label, path in [("Buffered", buffer_raster), ("NoBuffer", nobuffer_raster)]:
                if not arcpy.Exists(path):
                    print(f"Missing: {path}")
                    continue

                arr = arcpy.RasterToNumPyArray(path).astype(np.float32)
                arr[arr == 999] = np.nan
                valid = arr[~np.isnan(arr)]

                if valid.size == 0:
                    count = 0
                else:
                    threshold = np.percentile(valid, 75)
                    count = int(np.sum(valid > threshold))

                if label == "Buffered":
                    buffer_count = count
                else:
                    nobuffer_count = count

            data.append({
                "Year": year,
                "HighBuildupCount_Buffered": buffer_count,
                "HighBuildupCount_NoBuffer": nobuffer_count
            })

        # Save to CSV
        df = pd.DataFrame(data)
        out_csv = os.path.join(output_dir, f"{basin}_HighBuildup_Trend_Compare.csv")
        df.to_csv(out_csv, index=False)
        print(f"Saved: {out_csv}")

def buffer_plot():

    # Initialize DataFrames
    buffered_df = pd.DataFrame(index=years)
    nobuffer_df = pd.DataFrame(index=years)

    # Load data
    for basin in basins:
        csv_path = os.path.join(input_dir, f"{basin}_HighBuildup_Trend_Compare.csv")
        df = pd.read_csv(csv_path)
        df = df.set_index("Year")
        buffered_df[basin] = df["HighBuildupCount_Buffered"]
        nobuffer_df[basin] = df["HighBuildupCount_NoBuffer"]

    # Plotting
    plt.figure(figsize=(12, 6))

    # Plot Buffered with solid lines
    for basin in basins:
        plt.plot(buffered_df.index, buffered_df[basin], label=f"{basin} - Buffered", marker='o', linewidth=2)

    # Plot NoBuffer with dashed lines
    for basin in basins:
        plt.plot(nobuffer_df.index, nobuffer_df[basin], label=f"{basin} - NoBuffer", linestyle='--', marker='x', linewidth=2)

    plt.title("High Buildup Counts (>75th Percentile): Buffered vs NoBuffer")
    plt.xlabel("Year")
    plt.ylabel("High Buildup Cell Count")
    plt.grid(True, linestyle=':')
    plt.legend(title="Scenario", fontsize=9)
    plt.tight_layout()

    # Save the figure
    out_path = os.path.join(input_dir, "HighBuildup_Trends_Buffer_vs_NoBuffer.png")
    plt.savefig(out_path, dpi=300)
    plt.show()

def main():
    width_freq()
    maxwidthchange_plot()
    buildup_count()
    buffer_plot()

if __name__=='__main__':
    main()
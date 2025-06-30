import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

result_log=fr"D:\Ashok\Catskills_Project\Inputs\Landuse\Subbasin_Results_Log.xlsx"
basins = ["WestDelaware", "ElkCreek", "TownBrooke"]
years = [1996, 2001, 2006, 2010, 2016, 2021]
# Reclassification groups
ag = [6, 7]
urban = [2, 3, 4, 5, 20]
good = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
forest = [9, 10, 11]
water_values = [19, 21, 22, 23]

for basin in basins:
    # Read and reclassify
    df = pd.read_excel(result_log, sheet_name=basin)
    df['reclassified'] = "Other"
    df.loc[df['Class_Code'].isin(ag), 'reclassified'] = "Agriculture"
    df.loc[df['Class_Code'].isin(urban), 'reclassified'] = "Urban"
    df.loc[df['Class_Code'].isin(good), 'reclassified'] = "Conservation Value"
    df.loc[df['Class_Code'].isin(forest), 'reclassified'] = "Forest"
    df.loc[df['Class_Code'].isin(water_values), 'reclassified'] = "Water"

    # Process data
    base_year = 1996
    year_columns = [col for col in df.columns if col not in ['Class_Code', 'reclassified', "LandUseClass"]]
    df_reclassified = df.groupby('reclassified')[year_columns].sum()
    df_change = df_reclassified.copy()
    for year in year_columns:
        if year != base_year:
            mask = df_reclassified[base_year] != 0
            df_change.loc[mask, year] = ((df_reclassified.loc[mask, year] - df_reclassified.loc[mask, base_year]) / df_reclassified.loc[mask, base_year]) * 100
            df_change.loc[~mask, year] = 0
    change_years = [col for col in year_columns if col != base_year]
    df_change_subset = df_change[change_years]

    output_dir = r"D:\Ashok\Catskills_Project\Outputs"

    # 1. Absolute Line Plot
    plt.figure(figsize=(10, 6))
    for category in df_reclassified.index:
        plt.plot(year_columns, df_reclassified.loc[category], marker='o', linewidth=2, label=category)
    plt.title('Land Use Area Over Time (ha)', fontsize=14, fontweight='bold')
    plt.xlabel('Year')
    plt.ylabel('Area (ha)')
    plt.grid(True)
    plt.legend(loc='best')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/{basin}_Area_LinePlot.png", dpi=300)
    plt.show()

    # 2. Percentage Change Line Plot
    plt.figure(figsize=(10, 6))
    for category in df_change.index:
        plt.plot(change_years, df_change.loc[category, change_years], marker='s', linewidth=2, label=category)
    plt.title(f'Percentage Change from {base_year}', fontsize=14, fontweight='bold')
    plt.xlabel('Year')
    plt.ylabel('Change (%)')
    plt.grid(True)
    plt.axhline(y=0, color='black', linestyle='--', linewidth=1)
    plt.legend(loc='best')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/{basin}_PercentChange_LinePlot.png", dpi=300)
    plt.show()

    # 3. Absolute Heatmap
    plt.figure(figsize=(10, 6))
    sns.heatmap(df_reclassified, annot=True, fmt='.0f', cmap='YlOrRd',
                cbar_kws={'label': 'Area (ha)'})
    plt.title('Land Use Area Heatmap (Absolute)', fontsize=14, fontweight='bold')
    plt.xlabel('Year')
    plt.ylabel('Land Use Category')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/{basin}_Area_Heatmap.png", dpi=300)
    plt.show()

    # 4. Percentage Change Heatmap
    plt.figure(figsize=(10, 6))
    sns.heatmap(df_change_subset, annot=True, fmt='.1f', cmap='RdBu_r', center=0,
                cbar_kws={'label': 'Change (%)'})
    plt.title(f'Percentage Change from {base_year} Heatmap', fontsize=14, fontweight='bold')
    plt.xlabel('Year')
    plt.ylabel('Land Use Category')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/{basin}_PercentChange_Heatmap.png", dpi=300)
    plt.show()

import arcpy
from pathlib import Path
import numpy as np
import pandas as pd
import itertools

arcpy.env.workspace=r"D:\Ashok\Catskills_Project\Inputs\Landuse"
arcpy.env.overwriteOutput=True

basins = ["WestDelaware", "ElkCreek", "TownBrooke"]
years = [1996, 2001, 2006, 2010, 2016, 2021]

class_names = {
    1: "Unclassified",
    2: "High Intensity Developed",
    3: "Medium Intensity Developed",
    4: "Low Intensity Developed",
    5: "Developed Open Space",
    6: "Cultivated",
    7: "Pasture/Hay",
    8: "Grassland",
    9: "Deciduous Forest",
    10: "Evergreen Forest",
    11: "Mixed Forest",
    12: "Scrub/Shrub",
    13: "Palustrine Forested Wetland",
    14: "Palustrine Scrub/Shrub Wetland",
    15: "Palustrine Emergent Wetland",
    16: "Estuarine Forested Wetland",
    17: "Estuarine Scrub/Shrub Wetland",
    18: "Estuarine Emergent Wetland",
    19: "Unconsolidated Shore",
    20: "Barren Land",
    21: "Open Water",
    22: "Palustrine Aquatic Bed",
    23: "Estuarine Aquatic Bed",
    24: "Tundra",
    25: "Perennial Ice/Snow"
}


result_log=fr"D:\Ashok\Catskills_Project\Inputs\Landuse\Subbasin_Results_Log.xlsx"
pixel_area_ha = 0.01
name_to_code = {name: code for code, name in class_names.items()}

with pd.ExcelWriter(result_log) as writer:
    
    for basin in basins:
        summary_df=pd.DataFrame()

        for year in years:            

            raster1=arcpy.Raster(fr"{basin}\{basin}_{year}_ccap_LC_Resampled10m.tif")
            

            raster = arcpy.Raster(str(raster1))
            arr = arcpy.RasterToNumPyArray(raster)
            arr = arr[arr != 999]
            

            classes, counts = np.unique(arr, return_counts=True)
            area_ha = counts * pixel_area_ha

            class_labels = [class_names.get(c, f"Class {c}") for c in classes]
            summary_df[year] = pd.Series(area_ha, index=class_labels)
        
        summary_df['Class_Code'] = summary_df.index.map(name_to_code)
        summary_df = summary_df.sort_values('Class_Code')
        summary_df.index.name = "LandUseClass"
        
        summary_df.to_excel(writer, sheet_name=basin)
        print(f" Wrote area summary for {basin}")
    
print(f"\n Summary saved to: {result_log}")    

        

        

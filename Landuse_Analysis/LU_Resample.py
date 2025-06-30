import arcpy
import os
from pathlib import Path
import itertools

arcpy.env.workspace=r"D:\Ashok\Catskills_Project\Inputs\Landuse"
arcpy.env.overwriteOutput=True

years=[1996, 2001, 2006, 2010, 2016, 2021]
basins=["Cannonsville"]
in_crs='PROJCS["NAD_1983_Contiguous_USA_Albers",GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Albers"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-96.0],PARAMETER["Standard_Parallel_1",29.5],PARAMETER["Standard_Parallel_2",45.5],PARAMETER["Latitude_Of_Origin",23.0],UNIT["Meter",1.0]]'
out_crs='PROJCS["WGS_1984_UTM_Zone_18N",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-75.0],PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'
for year,basin in itertools.product(years,basins):
    in_raster=fr"D:\Ashok\Catskills_Project\Inputs\Landuse\{basin}_{year}_ccap_landcover30m.tif"
    dir=fr"D:\Ashok\Catskills_Project\Inputs\Landuse\{basin}"
    os.makedirs(dir,exist_ok=True)
    out_raster=fr"D:\Ashok\Catskills_Project\Inputs\Landuse\{basin}\{basin}_{year}_ccap_LC_Resampled10m.tif"
    if not arcpy.Exists(in_raster):
        print(f"[!] Raster does not exist: {in_raster}")
        continue
    desc = arcpy.Describe(in_raster)
    print(f"Spatial Reference of {in_raster}: {desc.spatialReference.name}")    
    with arcpy.EnvManager(outputCoordinateSystem='PROJCS["WGS_1984_UTM_Zone_18N",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-75.0],PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'):
        arcpy.management.ProjectRaster(in_raster=in_raster,out_raster=out_raster,
                                    out_coor_system=out_crs,resampling_type="NEAREST",
                                    cell_size="10 10",
                                    geographic_transform="WGS_1984_(ITRF00)_To_NAD_1983",
                                    in_coor_system=in_crs)
    print(f"Resampled raster {basin}_{year}")
    
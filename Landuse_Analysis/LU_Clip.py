import arcpy
from pathlib import Path
import itertools

arcpy.env.workspace=r"D:\Ashok\Catskills_Project\Inputs\Landuse"
arcpy.env.overwriteOutput=True

years=[1996, 2001, 2006, 2010, 2016, 2021]
basins=["Cannonsville"]

for year,basin in itertools.product(years,basins):

    landuse_raster=fr"D:\Ashok\Catskills_Project\Inputs\Landuse\CONUS\conus_{year}_ccap_landcover_20200311.tif"
    wshed_shp=fr"D:\Ashok\Catskills_Project\Inputs\Subbasin_Boundaries\{basin}_boundary.shp"
    clipped_raster=fr"D:\Ashok\Catskills_Project\Inputs\Landuse\{basin}_{year}_ccap_landcover30m.tif"

    utm18N=arcpy.SpatialReference(32618)

    arcpy.management.Clip(landuse_raster,rectangle="",out_raster=clipped_raster,in_template_dataset=wshed_shp,
                        nodata_value="999",clipping_geometry="ClippingGeometry",maintain_clipping_extent="NO_MAINTAIN_EXTENT"
                        )


    print(f"Clipped raster saved to :{clipped_raster}")



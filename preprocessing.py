import arcpy
from osgeo import gdal
import itertools
import os
gdal.UseExceptions()

from arcpy.ia import Raster, RasterCalculator
from arcpy.sa import Raster, Con, IsNull
arcpy.env.overwriteOutput = True

#Path definitions
output_CRS=r'PROJCS["WGS_1984_UTM_Zone_18N",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-75.0],PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def get_shape(path):
    ds = gdal.Open(path)
    return ds.RasterYSize, ds.RasterXSize

def landuse_processing(basin,year):
    #Landuse
    
    clipped_LULC=fr"D:\Ashok\Catskills_Project\Inputs\Landuse\{basin}\{basin}_{year}_ccap_LC_Resampled10m.tif"
    lulc_raster = Raster(clipped_LULC)
    extent_lulc = arcpy.Describe(lulc_raster).extent

    #1.Clipping flowlines to boundary

    catskills_flowline=r"D:\Ashok\Catskills_Project\Inputs\Flowlines\NHPFlowline-UTM18N.shp"
    clipped_flowline=fr"D:\Ashok\Catskills_Project\Inputs\Flowlines\NHPFlowline_{basin}_{year}.shp"
    basin_boundary=fr"D:\Ashok\Catskills_Project\Inputs\Subbasin_Boundaries\{basin}_boundary.shp"

    with arcpy.EnvManager(outputCoordinateSystem=output_CRS):
        arcpy.analysis.Clip(
            in_features=catskills_flowline,
            clip_features=basin_boundary,
            out_feature_class=clipped_flowline,
            cluster_tolerance=None
        )
    print("1/8: Clipped Flowlines")

    #2. Converting streamline to raster of 10m size (if stream polygon is available, that will be better)
    raster_flowline=fr"D:\Ashok\Catskills_Project\Inputs\Flowlines\FTR_{basin}_{year}.tif"

    with arcpy.EnvManager(snapRaster=lulc_raster, cellSize=lulc_raster, extent=extent_lulc):
        arcpy.conversion.PolylineToRaster(
            in_features=clipped_flowline,
            value_field="reachcode",
            out_rasterdataset=raster_flowline,
            cell_assignment="MAXIMUM_LENGTH",
            priority_field="NONE",
            cellsize=10,
            build_rat="BUILD"
        )
    print("2/8: Converted flowlines to raster")

    #3. Burning in stream raster
    stream_raster = Raster(raster_flowline)
    LULC_burntin=fr"D:\Ashok\Catskills_Project\Inputs\{basin}\{basin}_LULC_10m_{year}.tif"

    with arcpy.EnvManager(snapRaster=lulc_raster, cellSize=lulc_raster, extent=extent_lulc):
        out_raster = Con(IsNull(stream_raster), lulc_raster, 21)
        out_raster.save(LULC_burntin)
        arcpy.management.SetRasterProperties(
        in_raster=LULC_burntin,
        nodata="1 999"
    )

    print("3/8: Burned streamlines into land cover raster")

def flow_mask_processing(basin,year):
    
    clipped_LULC=fr"D:\Ashok\Catskills_Project\Inputs\Landuse\{basin}\{basin}_{year}_ccap_LC_Resampled10m.tif"
    lulc_raster = Raster(clipped_LULC)
    extent_lulc = arcpy.Describe(lulc_raster).extent
    
    clipped_flowline=fr"D:\Ashok\Catskills_Project\Inputs\Flowlines\NHPFlowline_{basin}_{year}.shp"
    euclid_dist=fr"D:\Ashok\Catskills_Project\Inputs\Flowlines\EuclideanDistance-{basin}_{year}.tif"
    buffer_mask=fr"D:\Ashok\Catskills_Project\Inputs\{basin}\{basin}_{year}_Flow_Mask_200m.tif"

    #4. Euclidean Distance calculation
    with arcpy.EnvManager(outputCoordinateSystem=output_CRS, snapRaster=lulc_raster, cellSize=lulc_raster, extent=extent_lulc):
        out_distance_raster = arcpy.sa.EucDistance(
            in_source_data=clipped_flowline,
            maximum_distance=None,
            cell_size=10,
            out_direction_raster=None,
            distance_method="PLANAR",
            in_barrier_data=None,
            out_back_direction_raster=None
        )
        out_distance_raster.save(euclid_dist)
    print("4/8: Calculated Euclidean distance from flowlines")
    
    #5. Creating mask of 200m width
    distance_raster = Raster(euclid_dist)
    with arcpy.EnvManager(outputCoordinateSystem=output_CRS, snapRaster=lulc_raster, cellSize=lulc_raster):
        mask_raster = Con(distance_raster <= 200, 1, 999)
        mask_raster.save(buffer_mask)
        arcpy.management.SetRasterProperties(
        in_raster=buffer_mask,
        nodata="1 999"
    )
    print("5/8: Created 200m stream buffer mask")    

def flow_direction_processing(basin,year):

    clipped_LULC=fr"D:\Ashok\Catskills_Project\Inputs\Landuse\{basin}\{basin}_{year}_ccap_LC_Resampled10m.tif"
    lulc_raster = Raster(clipped_LULC)
    extent_lulc = arcpy.Describe(lulc_raster).extent

    input_dem=r"D:\Ashok\Catskills_Project\Inputs\DEM\Mosaiced_Raster.tif"
    clipped_dem=fr"D:\Ashok\Catskills_Project\Inputs\DEM\Clipped_DEM_{basin}.tif"
    filled_dem=fr"D:\Ashok\Catskills_Project\Inputs\DEM\Filled_DEM_{basin}.tif"
    flow_direction_raster=fr"D:\Ashok\Catskills_Project\Inputs\{basin}\FDR_10m.tif"


    #6. Clipping DEM to subbasin boundary
    with arcpy.EnvManager(outputCoordinateSystem=output_CRS, snapRaster=lulc_raster, cellSize=lulc_raster, extent=extent_lulc):
        out_raster = arcpy.sa.ExtractByMask(
            in_raster=input_dem,
            in_mask_data=lulc_raster,
            extraction_area="INSIDE"        
        )
        out_raster.save(clipped_dem)

    print("6/8: Clipped the DEM to basin boundary")

    #7. filling sinks
    with arcpy.EnvManager(outputCoordinateSystem=output_CRS, snapRaster=lulc_raster, cellSize=lulc_raster, extent=extent_lulc):
        out_surface_raster = arcpy.sa.Fill(
            in_surface_raster=clipped_dem,
            z_limit=None
        )
        out_surface_raster.save(filled_dem)

    print("7/8: Filled the sinks of DEM")

    #8. Flow direction calculation (D-8 Algorithm)
    with arcpy.EnvManager(outputCoordinateSystem=output_CRS, snapRaster=lulc_raster, cellSize=lulc_raster, extent=extent_lulc):
        out_flow_direction_raster = arcpy.sa.FlowDirection(
            in_surface_raster=filled_dem,
            force_flow="NORMAL",
            out_drop_raster=None,
            flow_direction_type="D8"
        )
        out_flow_direction_raster.save(flow_direction_raster)
        arcpy.management.SetRasterProperties(
        in_raster=flow_direction_raster,
        nodata="1 999"
    )

    print("8/8: Created flow direction raster")

def alignment_check(basin,year):
    LULC_burntin=fr"D:\Ashok\Catskills_Project\Inputs\{basin}\{basin}_LULC_10m_{year}.tif"
    flow_direction_raster=fr"D:\Ashok\Catskills_Project\Inputs\{basin}\FDR_10m.tif"
    buffer_mask=fr"D:\Ashok\Catskills_Project\Inputs\{basin}\{basin}_{year}_Flow_Mask_200m.tif"
    shape_lulc = get_shape(LULC_burntin)
    shape_fdr = get_shape(flow_direction_raster)
    shape_mask = get_shape(buffer_mask)

    print("LULC:", shape_lulc)
    print("FDR:", shape_fdr)
    print("Mask:", shape_mask)
    assert shape_lulc == shape_fdr == shape_mask, f"Raster shape mismatch for {basin}-{year}"

def main():
    basins = ["Cannonsville"]
    years = [1996, 2001, 2006, 2010, 2016, 2021]
    total = len(basins) * len(years)
    count = 0

    for basin, year in itertools.product(basins, years):
        count += 1
        print(f"\nProcessing {count}/{total}: {basin}-{year}\n")
        try:
            basin_path = fr"D:\Ashok\Catskills_Project\Inputs\{basin}"
            ensure_dir(basin_path)

            landuse_processing(basin, year)
            flow_mask_processing(basin, year)
            flow_direction_processing(basin, year)
            alignment_check(basin, year)

        except AssertionError as e:
            print(f"Alignment error: {e}")
        except Exception as e:
            print(f"Unexpected error during {basin}-{year}: {e}")
        

if __name__=='__main__':
    main()
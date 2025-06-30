# Traversability script
# Mike Billmire, Michigan Tech Research Institute, mgbillmi@mtu.edu
#
# Tracks the hydrologic path of a water droplet starting at each cell using a flow direction grid.
# Although could be used to track progress through a variety of input grids, it is configured at
# the moment (11-08) to track the path through a C-CAP land cover layer, and report FOUR outputs in grid format:
#

# This numpy version (as opposed to the ascii/string parsing version) is much more efficient
# with larger files

#
# Output 1: "trav/sample output"
#   Reports a score based on effectiveness of a natural buffer. Everytime the path crosses into agriculture (or other 'bad' landcover types),
#   it is reset to zero. It then recieves a negative point for each 'bad' landcover type it passes through. Each 'good' landcover type will yield
#   a single positive point. Should be modified if we can find any literature that provides information on the rate of build-up/filtering of nutrients as
#   water passes through ag/wetland/etc. Output values are anywhere from -333 to 333.
#
#   An alternative scoring method resets the score to 0 if a path crosses from a 'bad' landcover type to a 'good' type.
#
# Output 2: "hydist" - hydrologic distance
#   Reports the number of cells a water droplet will pass through before reaching a body of surface water. Output values range from 0 to 333
#
# Output 3: "buffwid" - natural buffer width
#   Reports the number of natural landcover cells that buffer the body of surface water that the cell flows into.
#   Similar to the traversability score in Output 1, except that a cell does not recieve a negative point for each 'bad' landcover
#   That is passed through. Output values range from 0 to 333.
#
# Output 4: "Build-up Index"
#   Reports a score that indicates the degree of agricultural buildup carried by the cell that enters a waterbody
#   Unlike the other outputs in that it tracks how much ag build up enters the stream by the LOCATION ALONG THE STREAM/WATERBODY
#   that each cell dumps into. The amount of buildup is calculated by an algorithm that subtracts 30 for each ag cell passed through
#   and reduces that figure for each natural cell passed through by a percentage determined by the buffer effectiveness width (calculated separately)
#   at each particular natural cell. If BEW is 30 or less, meaning that an effectiveness equivalent to first degree water treatment is achieved
#   with 30 meters or less of natural buffer, the buildup figure is reset to 0. If the BEW is greater than 30, the buildup figure is proportionally reduced based on the
#   length greater than 30 meters. Output values range from -infinity to 0, with lower values indicating greater degree of agricultural build-up.
#
#   The final build-up figure is assigned to the cell immediately adjacent to the waterbody, and all cells that dump through this same adjacent location are
#   added together. The output raster consists of all locations adjacent to streams and the build-up values associated with them
#
#
#
# Miscellaneous/error codes:
#    999: No Data
#   1000: Water
#   2000: Length to water > 1 km, a.k.a hydrologically inactive zone
#   3000: Invalid flow direction value encountered...sometimes this happens b/c multiple flow dir's are valid (basically considered a sink)
#   4000: Cyclic hydrologic flow...I'm not sure this ever actually happens, so could remove
#   5000: Flows off edge of map
#   6000: Stop code other than water (unconnected water, edge, blank, etc)
#
#
# Flow direction values:
#   32 |  64  | 128
#   16 | CELL |  1
#    8 |   4  |  2
#


import sys, os, string, fnmatch
from datetime import datetime as dt
import numpy as np
from osgeo import gdal
from osgeo.gdalconst import *
import itertools
gdal.UseExceptions()

# SET GLOBAL VARIABLES #

wd = r"D:\Ashok\Catskills_Project"

def traversibility_algorithm(basin,year):
    # Input files
    # # These files MUST BE FULLY ALIGNED; exact same dimensions, pixel size, etc
    # cd = "/net/nas3/data/gis_lab/project/MDNR_Phragmites/landscape_modeling/code/traversability/inputs/"
    # fdr_file = os.path.join(cd,"fdr10m_clipped.tif")  # flow direction
    # lc_file = os.path.join(cd,"lc_laura_resample2_clipped.tif")  # land cover, ccap, original classification
    # dist_mask_file = os.path.join(cd, 'nhd_linear_cleaned_200m_dist_mask_resample_clipped.tif')
    #"D:\Ashok\Catskills_Project\Inputs\West_Delaware\LULC_10m_2021.tif"

    LULC=fr"D:\Ashok\Catskills_Project\Inputs\{basin}\{basin}_LULC_10m_{year}.tif"
    FDR=fr"D:\Ashok\Catskills_Project\Inputs\{basin}\FDR_10m.tif"
    buffer_mask=fr"D:\Ashok\Catskills_Project\Inputs\{basin}\{basin}_{year}_Flow_Mask_200m.tif"

    fdr_file = FDR
    lc_file = LULC
    dist_mask_file = buffer_mask
    output_prefix = f'NoBuffer_{basin}_{year}_'

    removalrate_forest = 0.0  #0.9 #.6#0.9 #0.58 #0.9
    removalrate_nonforest = 0.0 #0.7 #0.55#0.7 #0.20 #0.7

    '''
    # Checklists
    # 'bad' landcover classes- including urban, and ag classes
    #ag = [6, 7]
    #urban = [0, 2, 3, 4, 5, 20]
    ag = [5]#, 6, 7]
    urban = [1, 2, 4, 11, 12]

    # 'good' landcover classes- forest, grass/shrub, and wetland
    #good = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 22]
    good = [3, 8, 9, 10, 14, 15, 16, 17, 18, 20, 21, 22, 23, 24]
    forest = [8,9,22,24]

    #water_values = [21]
    water_values = [25] # note that there's also a 13 water code, but this is not modified NHD-specific
    '''
    #CCAP LULC values- Modified based on https://coast.noaa.gov/data/digitalcoast/pdf/ccap-class-scheme-regional.pdf

    ag=[6,7]
    urban=[2,3,4,5,20]
    good=[8,9,10,11,12,13,14,15,16,17,18]
    forest=[9,10,11]
    water_values=[19,21,22,23]


    # landcover values that indicate to stop sequencing: water, background, blank, newline
    #stop = water_values[:] + [13]
    stop = water_values[:] 
    # valid flow direction values
    directions = [1, 2, 4, 8, 16, 32, 64, 128]

    # max_flow_length (units: number of pixels)
    # ~100m (300 feet) is a commonly used max value according to this:
    # http://www.wcc.nrcs.usda.gov/ftpref/wntsc/H&H/WinTR55/SheetFlowReferences.doc
    max_flow_length = 10

    # Dict to create buildup scores
    # [coord]: {'ag':0,'urban':0}
    buildup = {}

    # DEFINE FUNCTIONS #

    # Sequencer function: takes the flow direction data from the targeted cell and moves in the appropriate direction to the next cell
    def sequencer(k, seq_list, bew_list, v, h, history):
        if k == 1:
            h += 1

        if k == 2:
            v += 1
            h += 1

        if k == 4:
            v += 1

        if k == 8:
            v += 1
            h -= 1

        if k == 16:
            h -= 1

        if k == 32:
            h -= 1
            v -= 1

        if k == 64:
            v -= 1

        if k == 128:
            h += 1
            v -= 1

        # if k not in directions:
        #     print 'hold up: {}'.format(k)

        move_on(k, seq_list, bew_list, v, h, history)


    # Move on function: scans the target cell, writes to output files if it's a terminal cell (such as water), or applies scoring and re-runs the sequencer function otherwise
    def move_on(kk, seq_list, bew_list, v, h, history):
        # set the 'coordinates' of the raster for tracking purposes
        coordinates = (v,h)
        start_coords = history[0]
        k = kk

        # if the coordinates have already been used, we have a cyclic situation that could break the code, so input this error
        if coordinates in history:
            hydist[start_coords] = len(seq_list)
            buffwid[start_coords] = 4000

        # if a coordinate is out of bounds, input that out-of-bounds code
        elif v >= length or h >= width or h < 0:
            for o in [hydist, buffwid]:
                o[start_coords] = 5000

        # if the sequence length exceeds max flow length items (100m), assume it is hydrologically inactive and input the appropriate code
        elif len(seq_list) > max_flow_length:
            for o in [hydist, buffwid]:
                o[start_coords] = 2000

        elif k not in directions:
            hydist[start_coords] = len(seq_list)
            buffwid[start_coords] = 3000
            # print "BAD DIRECTION: {}".format(k)

        else:

            # set the landcover variable to the corresponding fdr coordinates
            c = lc[v,h]

            # if landcover is a value that indicates the sequencing should be stopped, do some stuff
            if c in stop:
                # if a water value has been reached- which is the goal- write the appropriate values to the output file
                if c in water_values:
                    # write the length of the sequence to the hydrologic distance file
                    hydist[start_coords] = len(seq_list)

                    # reset the scoring variables
                    wid = agnum = urbnum = 0.0

                    # loop through the sequence list
                    for i,lc_val in enumerate(seq_list):
                        # if a bad landcover is encountered, reset the buffer width to zero
                        if lc_val in ag:
                            wid = 0.0
                            agnum += 1.0

                        if lc_val in urban:
                            wid = 0.0
                            urbnum += 1.0

                        # increase width by one every time a good landcover value is encoutnered
                        if lc_val in good:
                            wid += 1.0
                            if lc_val in forest: # assume 90% removal efficiency for forests (Zhang et al. 2010)
                                agnum *= (1-removalrate_forest)
                                urbnum *= (1-removalrate_forest)
                            else:                # assume 70% removal efficiency for other natural types
                                agnum *= (1-removalrate_nonforest)
                                urbnum *= (1-removalrate_nonforest)

                    last_coords = history[-1]
                    if last_coords not in buildup:
                        buildup[last_coords] = {'ag':0,'urban':0}

                    if agnum+urbnum > 0:
                        buildup[last_coords]['ag'] += agnum
                        buildup[last_coords]['urban'] += urbnum

                    buffwid[start_coords] = wid # and write that value to file
                    buffwidmax[last_coords]=max(buffwidmax[last_coords],wid)


                else:  # if not a linear water value, indicate either edge OR non-linear water
                    for o in [hydist, buffwid]:
                        o[start_coords] = 6000


            else:  # if landcover value is a normal value...
                # VERY IMPORTANT: reset the flow-direction value to that of the cell at the end of the line
                k = fdr[v,h]#.split(' ')[h]

                # store the coordinates in the history list
                history.append(coordinates)

                # append the landcover value to the sequence list
                seq_list.append(c)
                #bew_list.append(bew[v,h])#.split(' ')[h])


                # and re-run the sequencer program to get the next landcover value
                sequencer(k, seq_list, bew_list, v, h, history)


    ########################################################
    ##################### MAIN PROGRAM #####################
    ########################################################

    

    ### Open each input file - flow direction and land cover, and read those lines
    lc_ds = gdal.Open(lc_file, 0)
    no_data = 999 #lc_ds.GetRasterBand(1).GetNoDataValue()
    stop.append(no_data)
    driver = lc_ds.GetDriver()
    geotransform = lc_ds.GetGeoTransform()
    projection = lc_ds.GetProjection()
    lc = lc_ds.ReadAsArray()
    del lc_ds

    fdr_ds = gdal.Open(fdr_file, 0)
    fdr = fdr_ds.ReadAsArray()
    fdr_no_data = fdr_ds.GetRasterBand(1).GetNoDataValue()
    del fdr_ds

    #bew = gdal.Open(bew_file, 0).ReadAsArray()

    # open distance mask
    dist_mask_ds = gdal.Open(dist_mask_file,0)
    dist_mask = dist_mask_ds.ReadAsArray()
    del dist_mask_ds

    shape = lc.shape
    length = shape[0]
    width = shape[1]

    print ('length: {}, width: {}'.format(length, width))

    print(f"Land cover shape: {lc.shape}")
    print(f"Flow direction shape: {fdr.shape}")
    print(f"Distance mask shape: {dist_mask.shape}")

    # Open each output file, write the header rows, change the NODATA value (change it from '-9999' to '999' just to save space...), and close
    hydist = np.full(lc.shape, no_data)
    buffwid = np.full(lc.shape, no_data)
    buffwidmax = np.full(lc.shape, -999)
    bu_ag = np.full(lc.shape, no_data)
    bu_urban = np.full(lc.shape, no_data)
    bu_both = np.full(lc.shape, no_data)

    start = dt.now()
    for (i,j) in np.ndindex(lc.shape):
        if i % 250 == 0 and j==0:   # Print every 250 rows
            print(f"Processing row {i} of {length} ({100 * i / length:.1f}%)")
        if fdr[i,j] in (fdr_no_data,0)  or lc[i,j] == no_data:  # if a background value is encountered, write that to the output files
            for o in [hydist, buffwid]:
                o[i,j] = no_data

        elif lc[i,j] in water_values:  # if a water value is encountered, write '0'
            for o in [hydist, buffwid]:
                o[i,j] = no_data

        elif not dist_mask[i,j]:
            for o in [hydist, buffwid]:
                o[i,j] = no_data

        # otherwise, reset tracking variables and run the sequencer program to acquire the hydrologic traversability sequence
        else:
            seq_list = [lc[i,j]]
            bew_list = []#[bew[i,j]]
            history = [(i,j)]
            sequencer(fdr[i,j], seq_list, bew_list, i, j, history)

    print('Processing time: {}'.format(dt.now() - start))

    # Build buildup arrays
    for b in buildup:
        if buildup[b]['ag'] >= 0:
            bu_ag[b] = buildup[b]['ag']
        if buildup[b]['urban'] >= 0:
            bu_urban[b] = buildup[b]['urban']
        bu_both[b] = buildup[b]['ag'] + buildup[b]['urban']

    # Write output files
    for o,v in {
            'hydist': hydist,
            'buffwid' : buffwid,
            'buffwidmax': buffwidmax,
            'buildup_ag': bu_ag,
            'buildup_urban': bu_urban,
            'buildup_ag_and_urban': bu_both
            }.items():

        # ensure the Outputs directory exists
        out_dir = os.path.join(wd, "Outputs",basin)
        os.makedirs(out_dir, exist_ok=True)

        outfl = os.path.join(out_dir, f"{output_prefix}_{o}.tif")
        print(outfl)

        
        outDs = driver.Create(
            outfl,
            lc.shape[1],
            lc.shape[0], 1, GDT_Int32,
            options=['COMPRESS=LZW']
        )
        if outDs is None:
            print('Could not create output file - bad path?')
            sys.exit(1)

        outBand = outDs.GetRasterBand(1)

        # write the data
        outBand.WriteArray(v, 0, 0)

        # flush data to disk, set the NoData value and calculate stats
        outBand.FlushCache()
        if o == 'buffwidmax':
            outBand.SetNoDataValue(-999)  
        else:
            outBand.SetNoDataValue(no_data)

        # georeference the image and set the projection
        outDs.SetGeoTransform(geotransform)
        outDs.SetProjection(projection)
        print(f"Created {outfl}")


def main():
    basins = ["Cannonsville"]#["WestDelaware", "ElkCreek", "TownBrooke"]#["WestDelaware", "ElkCreek", "TownBrooke"]
    years = [1996, 2001, 2006, 2010, 2016, 2021]#[1996, 2001, 2006, 2010, 2016, 2021]
    total = len(basins) * len(years)
    count = 0
    start_time=dt.now()
    for basin, year in itertools.product(basins, years):
        count += 1
        print(f"\nProcessing {count}/{total}: {basin}-{year}\n")
        try:
            traversibility_algorithm(basin,year)        
        except Exception as e:
            print(f"Unexpected error during {basin}-{year}: {e}")
    end_time=dt.now()
    print(f"Total time taken : {end_time-start_time}")
        

if __name__=='__main__':
    main()

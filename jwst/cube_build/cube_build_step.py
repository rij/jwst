 #! /usr/bin/env python

import sys
import time
import json
import numpy as np
from jwst.stpipe import Step, cmdline
from jwst import datamodels
from . import cube_build
from . import cube
from . import CubeD2C
from . import CubeCloud
from . import instrument
1
class CubeBuildStep (Step):
    """
    CubeBuildStep: Creates a 3-D spectral cube from a given list of input files 
    """

    spec = """
         channel = string(default='')
         scale1 = float(default=0.0)
         scale2 = float(default =0.0)
         scalew = float(default = 0.0)
         interpolation = string(default='pointcloud')
         wcs_method = string(default='assign_wcs')
         coord_system = string(default='v2-v3')
         power_x = float(default=1.0)
         power_y = float(default=1.0)
         power_z = float(default=1.0)
         offset_list = string(default='NA')
       """

    def process (self, input): 

        self.log.info('Starting IFU Cube Building Step...')

        if(not self.wcs_method.islower()):self.wcs_method = self.wcs_method.lower()
        if(not self.coord_system.islower()):self.coord_system= self.coord_system.lower()
        if(not self.interpolation.islower()):self.interpolation= self.interpolation.lower()

        # input parameters
        if(self.channel !=''):self.log.info('Input Channel %s',self.channel)
        if(self.scale1 !=0.0):self.log.info('Input Scale of axis 1 %f',self.scale1)
        if(self.scale2 !=0.0):self.log.info('Input Scale of axis 2 %f',self.scale2)
        if(self.scalew != 0.0):self.log.info('Input wavelength scale %f  ',self.scalew)
        if(self.offset_list !='NA'): self.log.info('Offset Dither list %s',self.offset_list)

        # valid coord_system: 
        # 1. alpha-beta (only valid for Single Cubes)
        # 2. v2-v3
        # 3. ra-dec

        # valid wcs_method
        # 1. assign_wcs
        # 2. distortion - only valid for MIRI, reads in distortion polynomials only used in testing


        if (self.interpolation == 'area'):
            self.coord_system = 'alpha-beta'      


        if (self.coord_system == 'v2-v3'):
            self.interpolation = 'pointcloud'  # can not be area


        self.log.info('Input interpolation %s', self.interpolation)
        self.log.info('WCS methods to use %s', self.wcs_method)
        self.log.info('Coordinate system to use %s', self.coord_system)
        
#_________________________________________________________________________________________________
        #Read in the input data - either in form of ASSOCIATION table or single filename 
        # If a single file - then assocation table format is filled in 

        input_table = cube_build.IFUCubeInput(input)

        self.input_table_type = 'Association'
        if(input_table.asn_table['asn_type'] == 'singleton'):
            self.offset_list = 'NA'
            self.input_table_type = 'singleton'

#_________________________________________________________________________________________________
# Loop over every Output Product Base name and set of member files
#_________________________________________________________________________________________________
# for each product name in the association table loop over the main cube building code

        num_products = len(input_table.asn_table['products'])
        self.log.debug('Number of products %d',num_products)
        for iproduct  in range(num_products):
            self.log.debug( 'Output Base %s ',input_table.asn_table['products'][iproduct]['name'])
#_________________________________________________________________________________________________
            self.metadata = {}
            self.metadata['Detector'] = ''
            self.metadata['channel'] = list()     # filled in by association table in FilesinCube
            self.metadata['subchannel'] = list()  # figured out from the members in the association

            self.metadata['filter'] = list()   #figured out from the members in the association
            self.metadata['grating'] = list()  #figured out from the memebers in the assoication
            self.metadata['output_name'] = ''
            self.metadata['number_files'] = 0 


        # Check if there is an offset list 
            self.v2offset = list()
            self.v3offset = list()
            if( self.offset_list != 'NA'):
                print('Going to read in dither offset list')
                cube_build.ReadOffSetFile(self)

        # Read in the input data (association table or single file) 
        # Fill in MasterTable   based on Channel/Subchannel  or filter/grating
        # Also if there is an Offset list - fill in MasterTable.FileOffset
            MasterTable= cube.FileTable()

            num,detector=cube_build.FilesinCube(self,input_table,iproduct,MasterTable)
            self.metadata['number_files'] = num
            self.metadata['Detector'] = detector
        # Determine which channels/subchannels or filter/grating cubes will be constructed from.
        # returns self.metadata['subchannel'] and self.metadata['channel']
        # or self.metadata['filter'], self.metadata['grating']
        
            cube_build.DetermineCubeCoverage(self,MasterTable)

            cube_build.CheckCubeType(self)

            self.output_name =  input_table.asn_table['products'][iproduct]['name']
            if(self.input_table_type == 'singleton'):
                self.output_name  = cube_build.UpdateOutPutName(self)
             
#            print('Output name',self.output_name)
#________________________________________________________________________________                
                
# Cube is an instance of CubeInfo - which holds basic information on Cube
            if(detector == 'MIRI'):
                Cube = cube.CubeInfo('MIRI',self.metadata['channel'], self.metadata['subchannel'],self.output_name)

            if(detector == 'NIRSPEC'):
                Cube = cube.CubeInfo('NIRSPEC',self.metadata['filter'], self.metadata['grating'],self.output_name)

            InstrumentInfo = instrument.Info()
            self.log.info( ' Building Cube %s ' ,Cube.output_name)

            scale = cube_build.DetermineScale(Cube,InstrumentInfo)

            a_scale = scale[0]
            if self.scale1 !=0:
                a_scale = self.scale1
                
            b_scale = scale[1]
            if self.scale2 !=0:
                b_scale = self.scale2

            wscale = scale[2]
            if self.scalew !=0:
                wscale = self.scalew

            Cube.SetScale(a_scale,b_scale,wscale)

            # WCS method - 
            # 1. Use the DISTORTION files that miri_cube uses (only valid for Testing `<MIRI)

            # 2. Use the assign_wcs step to determine the transformation between coordinates systems                
            self.wcs = {}
            self.wcs['Method'] = self.wcs_method

                # find the min & max final coordinates of cube: map each slice to cube 
                # add any dither offsets, then find the min & max value in each dimension
            t0 = time.time()

            CubeFootPrint = cube_build.DetermineCubeSize(self,Cube,MasterTable,InstrumentInfo)
            t1 = time.time()
            print ("Time to determine size of cube = %.1f.s" % (t1-t0,))

                # Based on Scaling and Min and Max values determine naxis1, naxis2, naxis3
                # set cube CRVALs, CRPIXs and xyz coords (center  x,y,z vector spaxel centers)
            Cube.SetGeometry(self.coord_system, CubeFootPrint)                    
            Cube.PrintCubeGeometry(detector)


            self.radius_x = Cube.Cdelt1*1.0
            self.radius_y = Cube.Cdelt2*1.0/2.0
            self.radius_z = Cube.Cdelt3*1.0

            if(self.interpolation =='pointcloud') :
                   self.log.info( 'Region of interest %f %f %f',self.radius_x,self.radius_y,self.radius_z)
                   self.log.info( 'Power parameters for weighting %5.1f %5.1f %5.1f',self.power_x, self.power_y,self.power_z)

            # now you have the size of cube - create an instance for each spaxel
            # create an empty spaxel list - this will become a list of Spaxel classses
            spaxel = []

            # set up center of the corner cube spaxel
            t0 = time.time()
            for z in range(Cube.naxis3):
                for y in range(Cube.naxis2):
                    for x in range(Cube.naxis1):
                        spaxel.append(cube.Spaxel(Cube.xcoord[x],Cube.ycoord[y],Cube.zcoord[z]))

                        
            t1 = time.time()
            print ("Time to create list of spaxel classes = %.1f.s" % (t1-t0,))


            # create an empty Pixel Cloud array of 8 columns
            # if doing interpolation on point cloud this will become a matrix of  Pixel Point cloud values
            # each row holds information for a single pixel

            # Initialize the PixelCloud to 8   columns of zeros (1 row) 
            PixelCloud = np.zeros(shape=(10,1))
            t0 = time.time()
            # now need to loop over every file that covers this channel/subchannel and
            # map the detector pixels to the cube spaxel.
            if(detector == 'MIRI'): 
                parameter1 = Cube.channel
                parameter2 = Cube.subchannel
            elif(detector == 'NIRSPEC'):
                parameter1 = Cube.grating
                parameter2 = Cube.filter
                
            number1 = len(parameter1)
            number2 = len(parameter2)
            for i in range(number1):
                this_par1 = parameter1[i]
                for j in range(number2):
                    this_par2 = parameter2[j]

                    PixelCloud = cube_build.MapDetectorToCube(self,this_par1,this_par2,Cube,spaxel,PixelCloud,\
                                                                      MasterTable,InstrumentInfo)

            t1 = time.time()
            self.log.info ("Time Map All slices on Detector to Cube = %.1f.s" % (t1-t0,))

#_______________________________________________________________________
# Mapped all data to cube or Point Cloud
# now determine Cube Spaxel flux

            t0 = time.time()
            if self.interpolation =='pointcloud' :
                CubeCloud.FindROI(self,Cube,spaxel,PixelCloud)
            t1 = time.time()
            self.log.info ("Time to Match Pt to cube = %.1f.s" % (t1-t0,))


            t0 = time.time() 
            cube_build.FindCubeFlux(self,Cube,spaxel,PixelCloud)

            t1 = time.time()
            self.log.info ("Time find Cube Flux= %.1f.s" % (t1-t0,))
# write out the IFU cube 
            cube_build.WriteCube(self,Cube,spaxel)

#        sys.exit('Stop')


                
if __name__ == '__main__':  
    cmdline.step_script( cube_build_step ) 



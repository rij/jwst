#! /usr/bin/env python

from jwst.stpipe import Step, cmdline
from . import photom
from jwst import datamodels


class PhotomStep(Step):
    """
    PhotomStep: Module for extraction photom conversion factor(s)
        and writing them to input header
    """

    reference_file_types = ['photom', 'area']

    def process(self, input_file):

        try:
            dm = models.open(input_file)
        except IOError:
            self.log.error('Input can not be opened as a Model.')

        # Open input as correct type
        if isinstance( dm, models.CubeModel ): # _integ.fits product: 3D array
            self.log.debug('Input is a CubeModel for a multiple integ file.')
        elif isinstance( dm, models.ImageModel ):  # standard product: 2D array
            self.log.debug('Input is an ImageModel.')
        elif isinstance( dm, models.DataModel ): # multi 2D arrays
            self.log.debug('Input is a MultiSlitModel.')
            dm.close()
            dm = models.MultiSlitModel( input_file )
        else:
            self.log.warning('Input is not a CubeModel, ImageModel or MultiSlitModel.')

        # Get the reference file names
        phot_filename = self.get_reference_file(dm, 'photom')
        self.log.info('Using photom reference file: %s', phot_filename)
        area_filename = self.get_reference_file(dm, 'area')
        self.log.info('Using area reference file: %s', area_filename)

        # Do the correction
        ff_a = photom.DataSet( dm, phot_filename, area_filename )

        output_obj = ff_a.do_all()
        output_obj.meta.cal_step.photom = 'COMPLETE'

        return output_obj

if __name__ == '__main__':
    cmdline.step_script(photom_step)


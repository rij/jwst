from __future__ import absolute_import, division

#
#  Module for applying the LG algorithm to an AMI exposure
#

import logging
import warnings
import numpy as np
from jwst import datamodels

from .NRM_Model import NRM_Model  
from . import webb_psf 
from . import leastsqnrm 

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def apply_LG (input_model, filter_model, oversample, rotation):
    """
    Short Summary
    -------------
    Applies the LG fringe detection algorithm to an AMI image

    Parameters
    ----------
    input_model: data model object
        AMI science image to be analyzed

    filter_model: filter model object
        filter throughput reference data

    oversample: integer
        Oversampling factor

    rotation: float (degrees)
        Initial guess at rotation of science image relative to model

    Returns
    -------
    output_model: Fringe model object
        Fringe analysis data

    """
 
    # Supress harmless arithmetic warnings for now
    warnings.filterwarnings("ignore", ".*invalid value.*", RuntimeWarning)
    warnings.filterwarnings("ignore", ".*divide by zero.*", RuntimeWarning)

    # Report the FILTER value for this image
    log.info ('Filter: %s', input_model.meta.instrument.filter)

    # Load the filter throughput data from the reference file
    bindown = 6
    band = webb_psf.get_webbpsf_filter(filter_model, specbin=bindown)

    # Set up some params that are needed as input to the LG algorithm:
    #  Search window for rotation fine-tuning
    rots_deg = np.array(( -0.5, -0.25, 0.0, 0.25, 0.5))
    #  Search range for relative pixel scales
    relpixscales = np.array((63.0, 63.25, 63.75, 64.0, 64.25)) / 63.75

    # Convert initial rotation guess from degrees to radians
    rotation = rotation * np.pi / 180.0

    # Instantiate the NRM model object
    jwnrm = NRM_Model( mask='JWST', holeshape='hex',
                       pixscale=leastsqnrm.mas2rad(63.52554816773347),
                       rotate=rotation, rotlist_deg=rots_deg,
                       scallist=relpixscales)  

    # Load the filter bandpass data into the NRM model
    jwnrm.bandpass = band
    # Set the oversampling factor in the NRM model
    jwnrm.over = oversample

    # Now fit the data in the science exposure
    # (pixguess is a guess at the pixel scale of the data)
    #  produces a 19x19 image of the fit
    jwnrm.fit_image( input_model.data, pixguess=jwnrm.pixel )
    
    # Construct model image from fitted PSF
    jwnrm.create_modelpsf()

    # Reset the warnings filter to its original state
    warnings.resetwarnings()

    # Store fit results in output model
    output_model = models.AmiLgModel (fit_image=jwnrm.modelpsf,
                  resid_image=jwnrm.residual,
                  closure_amp_table=np.asarray(jwnrm.redundant_cas),
                  closure_phase_table=np.asarray(jwnrm.redundant_cps),
                  fringe_amp_table=np.asarray(jwnrm.fringeamp),
                  fringe_phase_table=np.asarray(jwnrm.fringephase),
                  pupil_phase_table=np.asarray(jwnrm.piston),
                  solns_table=np.asarray(jwnrm.soln))

    # Copy header keywords from input to output
    output_model.update (input_model)

    return output_model

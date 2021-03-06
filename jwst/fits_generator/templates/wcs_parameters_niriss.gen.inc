
/ WCS parameters

WCSAXES  = 2       /      number of World Coordinate System axes
CRPIX1   = 0.5*input('NAXIS1')  /      x-coordinate of the reference pixel
CRPIX2   = 0.5*input('NAXIS2')  /      y-coordinate of the reference pixel
CRVAL1   = 5.63056810618  /      RA at the reference pixel (degrees)
CRVAL2   = -72.0545718428  /      Dec at the reference pixel (degrees)
CTYPE1   = 'RA---TAN'  /  first axis coordinate type
CTYPE2   = 'DEC--TAN'  /  second axis coordinate type
CUNIT1   = 'deg'       /  first axis units
CUNIT2   = 'deg'       /  second axis units
CDELT1   =  0.0656
CDELT2   =  0.0656
PC1_1    = 1.0     /      linear transformation matrix element
PC1_2    = 0.0     /      linear transformation matrix element
PC2_1    = 0.0     /      linear transformation matrix element
PC2_2    = 1.0     /      linear transformation matrix element
S_REGION = 'N/A' /      spatial extent of the observation

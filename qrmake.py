import segno

def qr_matrix(otp):
    """
    Generate QR matrix for OTP with error-correction H matching original cards.
    Original cards used mode='byte', error='h', version=1 (21x21 modules).
    Returns 21x21 list of rows (1 for black module, 0 for white).
    """
    qr = segno.make(str(otp), error="h", mode="byte", boost_error=False)
    return [[int(cell) for cell in row] for row in qr.matrix]

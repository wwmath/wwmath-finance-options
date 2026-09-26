C     andreasen2011/sabr-x-integral-form-against
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = epsilon
C       X(2) = rho
C       X(3) = y
      PROGRAM WWMAIN
      INTEGER NIN
      PARAMETER (NIN = 3)
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION WWEVAL, RES
      EXTERNAL WWEVAL
      INTEGER I
      READ (*,*) (X(I), I = 1, NIN)
      RES = WWEVAL()
      WRITE (*,'(1X,E25.17)') RES
      END
      DOUBLE PRECISION FUNCTION WWEVAL()
      INTEGER NIN
      PARAMETER (NIN = 3)
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION R001, R002
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      R001 = X(3)
C     J(R001)
      R002=SQRT(((1.0D0+((X(1)**2)*(R001**2)))-(2.0D0*X(2)*X(1)*R001)))
      WWEVAL=(LOG((((R002-X(2))+(X(1)*X(3)))/(1.0D0-X(2))))/X(1))
      RETURN
      END

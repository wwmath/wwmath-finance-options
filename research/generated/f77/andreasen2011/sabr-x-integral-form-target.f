C     andreasen2011/sabr-x-integral-form-target
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
      DOUBLE PRECISION R003
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      DOUBLE PRECISION WF001
      EXTERNAL WF001
C     integral over u
      R003 = WWQUAD(WF001, 0.0D0, X(3), 0)
      WWEVAL = R003
      RETURN
      END
      DOUBLE PRECISION FUNCTION WF001(XV)
      INTEGER NIN
      PARAMETER (NIN = 3)
      DOUBLE PRECISION XV
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION R002
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
C     J(XV)
      R002=SQRT(((1.0D0+((X(1)**2)*(XV**2)))-(2.0D0*X(2)*X(1)*XV)))
      WF001 = (1.0D0/R002)
      RETURN
      END

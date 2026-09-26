C     sidani2014/payoff-transform-Re-against
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = epsilon
C       X(2) = xi
C       X(3) = K
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
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      WWEVAL=DBLE((-(EXP((((-X(1))-((0.0D0,1.0D0)*X(2)))*X(3)))/(((-((0.
     &0D0,1.0D0)*X(1)))+X(2))**2))))
      RETURN
      END

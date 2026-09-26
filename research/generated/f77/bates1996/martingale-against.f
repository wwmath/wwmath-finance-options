C     bates1996/martingale-against
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = S
C       X(2) = b
C       X(3) = T
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
      WWEVAL = (X(1)*EXP((X(2)*X(3))))
      RETURN
      END

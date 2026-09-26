C     black1976/put-call-parity-against
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = r
C       X(2) = t
C       X(3) = F
C       X(4) = cstar
      PROGRAM WWMAIN
      INTEGER NIN
      PARAMETER (NIN = 4)
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
      PARAMETER (NIN = 4)
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      WWEVAL = (EXP(((-X(1))*X(2)))*(X(3) - X(4)))
      RETURN
      END

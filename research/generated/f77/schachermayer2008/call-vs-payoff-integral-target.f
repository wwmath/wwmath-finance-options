C     schachermayer2008/call-vs-payoff-integral-target
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = F
C       X(2) = K
C       X(3) = sigma
C       X(4) = T
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
      DOUBLE PRECISION R001
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
C     d
      R001 = ((X(1) - X(2))/(X(3)*SQRT(X(4))))
      WWEVAL=(((X(1)-X(2))*WWNCDF(R001))+(X(3)*SQRT(X(4))*WWNPDF(R001)))
      RETURN
      END

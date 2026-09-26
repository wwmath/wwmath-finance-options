C     schachermayer2008/call-vs-payoff-integral-against
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = F
C       X(2) = sigma
C       X(3) = T
C       X(4) = K
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
      DOUBLE PRECISION R002
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      DOUBLE PRECISION WF001
      EXTERNAL WF001
C     integral over z
      R002 = WWQUAD(WF001, 0.0D0, 0.0D0, 2)
      WWEVAL = R002
      RETURN
      END
      DOUBLE PRECISION FUNCTION WF001(XV)
      INTEGER NIN
      PARAMETER (NIN = 4)
      DOUBLE PRECISION XV
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      WF001=(MAX(((X(1)+(X(2)*SQRT(X(3))*XV))-X(4)),0.0D0)*WWNPDF(XV))
      RETURN
      END

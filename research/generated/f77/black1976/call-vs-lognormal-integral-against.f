C     black1976/call-vs-lognormal-integral-against
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = r
C       X(2) = t
C       X(3) = F
C       X(4) = s
C       X(5) = cstar
      PROGRAM WWMAIN
      INTEGER NIN
      PARAMETER (NIN = 5)
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
      PARAMETER (NIN = 5)
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION R002
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      DOUBLE PRECISION WF001
      EXTERNAL WF001
C     integral over y
      R002 = WWQUAD(WF001, 0.0D0, 0.0D0, 2)
      WWEVAL = (EXP(((-X(1))*X(2)))*R002)
      RETURN
      END
      DOUBLE PRECISION FUNCTION WF001(XV)
      INTEGER NIN
      PARAMETER (NIN = 5)
      DOUBLE PRECISION XV
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      WF001=(MAX(((X(3)*EXP(((-(((X(4)**2)/2.0D0)*X(2)))+(X(4)*SQRT(X(2)
     &)*XV))))-X(5)),0.0D0)*WWNPDF(XV))
      RETURN
      END

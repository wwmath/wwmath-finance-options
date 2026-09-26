C     bachelier1900/simple-option-from-density-target
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = k
C       X(2) = t
      PROGRAM WWMAIN
      INTEGER NIN
      PARAMETER (NIN = 2)
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
      PARAMETER (NIN = 2)
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION R004
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      DOUBLE PRECISION WF001
      EXTERNAL WF001
C     integral over x
      R004 = WWQUAD(WF001, 0.0D0, 0.0D0, 1)
      WWEVAL = R004
      RETURN
      END
      DOUBLE PRECISION FUNCTION WF001(XV)
      INTEGER NIN
      PARAMETER (NIN = 2)
      DOUBLE PRECISION XV
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION R002, R003
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      R002 = X(2)
C     p(XV,R002)
      R003=((1.0D0/(2.0D0*3.14159265358979324D0*X(1)*SQRT(R002)))*EXP((-
     &((XV**2)/(4.0D0*3.14159265358979324D0*(X(1)**2)*R002)))))
      WF001 = (XV*R003)
      RETURN
      END

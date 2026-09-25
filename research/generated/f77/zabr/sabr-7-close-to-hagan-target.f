C     zabr/sabr-7-close-to-hagan-target
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = s
C       X(2) = k
C       X(3) = epsilon
C       X(4) = rho
C       X(5) = z
C       X(6) = c
C       X(7) = beta
      PROGRAM WWMAIN
      INTEGER NIN
      PARAMETER (NIN = 7)
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
      PARAMETER (NIN = 7)
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION R003, R004, R005, R006
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      DOUBLE PRECISION WF001
      EXTERNAL WF001
C     integral over u
      R003 = WWQUAD(WF001, X(2), X(1), 0)
C     y_SABR
      R004 = ((1.0D0/X(5))*R003)
C     J(R004)
      R005=SQRT(((1.0D0+((X(3)**2)*(R004**2)))-(2.0D0*X(4)*X(3)*R004)))
C     x_SABR
      R006 = (LOG((((R005 - X(4)) + (X(3)*R004))/(1.0D0 - X(4))))/X(3))
      WWEVAL = (LOG((X(1)/X(2)))/R006)
      RETURN
      END
      DOUBLE PRECISION FUNCTION WF001(XV)
      INTEGER NIN
      PARAMETER (NIN = 7)
      DOUBLE PRECISION XV
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION R002
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
C     sigma(XV)
      R002 = (X(6)*(XV**X(7)))
      WF001 = (1.0D0/R002)
      RETURN
      END

C     heston1993/black-scholes-limit-against
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = r
C       X(2) = t
C       X(3) = F
C       X(4) = cstar
C       X(5) = s
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
      DOUBLE PRECISION R001, R002
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
C     d_1
      R001=((LOG((X(3)/X(4)))+(((X(5)**2)/2.0D0)*X(2)))/(X(5)*SQRT(X(2))
     &))
C     d_2
      R002 = (R001 - (X(5)*SQRT(X(2))))
      WWEVAL=(EXP(((-X(1))*X(2)))*((X(3)*WWNCDF(R001))-(X(4)*WWNCDF(R002
     &))))
      RETURN
      END

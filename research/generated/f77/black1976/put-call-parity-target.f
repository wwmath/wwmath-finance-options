C     black1976/put-call-parity-target
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
      DOUBLE PRECISION R001, R002, R003, R004
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
C     d_1
      R001=((LOG((X(3)/X(4)))+(((X(5)**2)/2.0D0)*X(2)))/(X(5)*SQRT(X(2))
     &))
C     d_2
      R002 = (R001 - (X(5)*SQRT(X(2))))
C     c
      R003=(EXP(((-X(1))*X(2)))*((X(3)*WWNCDF(R001))-(X(4)*WWNCDF(R002))
     &))
C     p
      R004=(EXP(((-X(1))*X(2)))*((X(4)*WWNCDF((-R002)))-(X(3)*WWNCDF((-R
     &001)))))
      WWEVAL = (R003 - R004)
      RETURN
      END

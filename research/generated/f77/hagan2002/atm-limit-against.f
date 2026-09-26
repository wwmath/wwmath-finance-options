C     hagan2002/atm-limit-against
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = alpha
C       X(2) = f
C       X(3) = beta
C       X(4) = rho
C       X(5) = nu
C       X(6) = t_ex
      PROGRAM WWMAIN
      INTEGER NIN
      PARAMETER (NIN = 6)
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
      PARAMETER (NIN = 6)
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      WWEVAL=((X(1)/(X(2)**(1.0D0-X(3))))*(1.0D0+((((((1.0D0-X(3))**2)/2
     &4.0D0)*((X(1)**2)/(X(2)**(2.0D0*(1.0D0-X(3))))))+((X(4)*X(3)*X(1)*
     &X(5))/(4.0D0*(X(2)**(1.0D0-X(3)))))+(((2.0D0-(3.0D0*(X(4)**2)))/24
     &.0D0)*(X(5)**2)))*X(6))))
      RETURN
      END

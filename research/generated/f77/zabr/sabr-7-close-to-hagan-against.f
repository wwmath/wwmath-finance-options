C     zabr/sabr-7-close-to-hagan-against
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = alpha
C       X(2) = f
C       X(3) = K
C       X(4) = beta
C       X(5) = nu
C       X(6) = rho
C       X(7) = t_ex
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
      DOUBLE PRECISION R001, R002
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
C     z
      R001=((X(5)/X(1))*((X(2)*X(3))**((1.0D0-X(4))/2.0D0))*LOG((X(2)/X(
     &3))))
C     x(R001)
      R002=LOG((((SQRT(((1.0D0-(2.0D0*X(6)*R001))+(R001**2)))+R001)-X(6)
     &)/(1.0D0-X(6))))
      WWEVAL=((X(1)/(((X(2)*X(3))**((1.0D0-X(4))/2.0D0))*(1.0D0+((((1.0D
     &0-X(4))**2)/24.0D0)*(LOG((X(2)/X(3)))**2))+((((1.0D0-X(4))**4)/192
     &0.0D0)*(LOG((X(2)/X(3)))**4)))))*(R001/R002)*(1.0D0+((((((1.0D0-X(
     &4))**2)/24.0D0)*((X(1)**2)/((X(2)*X(3))**(1.0D0-X(4)))))+((X(6)*X(
     &4)*X(5)*X(1))/(4.0D0*((X(2)*X(3))**((1.0D0-X(4))/2.0D0))))+(((2.0D
     &0-(3.0D0*(X(6)**2)))/24.0D0)*(X(5)**2)))*X(7))))
      RETURN
      END

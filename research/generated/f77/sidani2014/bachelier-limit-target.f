C     sidani2014/bachelier-limit-target
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = F
C       X(2) = K
C       X(3) = kappa
C       X(4) = theta
C       X(5) = T
C       X(6) = rho
C       X(7) = xi
C       X(8) = v
      PROGRAM WWMAIN
      INTEGER NIN
      PARAMETER (NIN = 8)
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
      PARAMETER (NIN = 8)
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION R007
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      DOUBLE PRECISION WF001
      EXTERNAL WF001
C     integral over u
      R007 = WWQUAD(WF001, 0.0D0, 0.0D0, 1)
      WWEVAL=(((X(1)-X(2))/2.0D0)+((1.0D0/3.14159265358979324D0)*R007))
      RETURN
      END
      DOUBLE PRECISION FUNCTION WF001(XV)
      INTEGER NIN
      PARAMETER (NIN = 8)
      DOUBLE PRECISION XV
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE COMPLEX Z002, Z003, Z004, Z005, Z006
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
C     D(XV)
      Z002=SQRT((((X(3)-((0.0D0,1.0D0)*X(6)*X(7)*XV))**2)+((X(7)**2)*(XV
     &**2))))
C     G(XV)
      Z003=(-(((X(7)**2)*(XV**2))/(((X(3)-((0.0D0,1.0D0)*X(6)*X(7)*XV))+
     &Z002)**2)))
C     A(XV)
      Z004=(X(3)*X(4)*((-(((XV**2)*X(5))/((X(3)-((0.0D0,1.0D0)*X(6)*X(7)
     &*XV))+Z002)))-((2.0D0/(X(7)**2))*LOG(((1.0D0-(Z003*EXP(((-Z002)*X(
     &5)))))/(1.0D0-Z003))))))
C     B(XV)
      Z005=(-(((XV**2)*(1.0D0-EXP(((-Z002)*X(5)))))/(((X(3)-((0.0D0,1.0D
     &0)*X(6)*X(7)*XV))+Z002)*(1.0D0-(Z003*EXP(((-Z002)*X(5))))))))
C     phi(XV)
      Z006 = EXP((Z004 + (Z005*X(8))))
      WF001=((1.0D0-DBLE((EXP(((0.0D0,1.0D0)*XV*(X(1)-X(2))))*Z006)))/(X
     &V**2))
      RETURN
      END

C     bates1996/martingale-target
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = S
C       X(2) = b
C       X(3) = lambdastar
C       X(4) = kbarstar
C       X(5) = T
C       X(6) = alpha
C       X(7) = sigma_v
C       X(8) = betastar
C       X(9) = rho
C       X(10) = V
C       X(11) = delta
      PROGRAM WWMAIN
      INTEGER NIN
      PARAMETER (NIN = 11)
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
      PARAMETER (NIN = 11)
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE COMPLEX Z001, Z002, Z003, Z004, Z005, Z006
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      Z001 = (-(0.0D0,1.0D0))
C     d(Z001)
      Z002=SQRT((((X(8)-(X(9)*X(7)*((0.0D0,1.0D0)*Z001)))**2)+((X(7)**2)
     &*(((0.0D0,1.0D0)*Z001)+(Z001**2)))))
C     g(Z001)
      Z003=(((X(8)-(X(9)*X(7)*((0.0D0,1.0D0)*Z001)))-Z002)/((X(8)-(X(9)*
     &X(7)*((0.0D0,1.0D0)*Z001)))+Z002))
C     A(Z001)
      Z004=((X(6)/(X(7)**2))*((((X(8)-(X(9)*X(7)*((0.0D0,1.0D0)*Z001)))-
     &Z002)*X(5))-(2.0D0*LOG(((1.0D0-(Z003*EXP(((-Z002)*X(5)))))/(1.0D0-
     &Z003))))))
C     B(Z001)
      Z005=((((X(8)-(X(9)*X(7)*((0.0D0,1.0D0)*Z001)))-Z002)/(X(7)**2))*(
     &(1.0D0-EXP(((-Z002)*X(5))))/(1.0D0-(Z003*EXP(((-Z002)*X(5)))))))
C     psi(Z001)
      Z006=EXP(((((0.0D0,1.0D0)*Z001)*(LOG(X(1))+((X(2)-(X(3)*X(4)))*X(5
     &))))+Z004+(Z005*X(10))+(X(3)*X(5)*((((1.0D0+X(4))**((0.0D0,1.0D0)*
     &Z001))*EXP((((X(11)**2)/2.0D0)*((0.0D0,1.0D0)*Z001)*(((0.0D0,1.0D0
     &)*Z001)-1.0D0))))-1.0D0))))
      WWEVAL = DBLE(Z006)
      RETURN
      END

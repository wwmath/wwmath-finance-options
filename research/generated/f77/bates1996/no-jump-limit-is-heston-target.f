C     bates1996/no-jump-limit-is-heston-target
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = r
C       X(2) = T
C       X(3) = S
C       X(4) = b
C       X(5) = X
C       X(6) = lambdastar
C       X(7) = kbarstar
C       X(8) = alpha
C       X(9) = sigma_v
C       X(10) = betastar
C       X(11) = rho
C       X(12) = V
C       X(13) = delta
      PROGRAM WWMAIN
      INTEGER NIN
      PARAMETER (NIN = 13)
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
      PARAMETER (NIN = 13)
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION R001, R010, R011, R018, R019
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      DOUBLE PRECISION WF002
      EXTERNAL WF002
      DOUBLE PRECISION WF012
      EXTERNAL WF012
C     F
      R001 = (X(3)*EXP((X(4)*X(2))))
C     integral over phi
      R010 = WWQUAD(WF002, 0.0D0, 0.0D0, 1)
C     P[1]
      R011 = ((1.0D0/2.0D0) + ((1.0D0/3.14159265358979324D0)*R010))
C     integral over phi
      R018 = WWQUAD(WF012, 0.0D0, 0.0D0, 1)
C     P[2]
      R019 = ((1.0D0/2.0D0) + ((1.0D0/3.14159265358979324D0)*R018))
      WWEVAL = (EXP(((-X(1))*X(2)))*((R001*R011) - (X(5)*R019)))
      RETURN
      END
      DOUBLE PRECISION FUNCTION WF002(XV)
      INTEGER NIN
      PARAMETER (NIN = 13)
      DOUBLE PRECISION XV
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION R009
      DOUBLE COMPLEX Z003, Z004, Z005, Z006, Z007, Z008
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      Z003 = (XV - (0.0D0,1.0D0))
C     d(Z003)
      Z004=SQRT((((X(10)-(X(11)*X(9)*((0.0D0,1.0D0)*Z003)))**2)+((X(9)**
     &2)*(((0.0D0,1.0D0)*Z003)+(Z003**2)))))
C     g(Z003)
      Z005=(((X(10)-(X(11)*X(9)*((0.0D0,1.0D0)*Z003)))-Z004)/((X(10)-(X(
     &11)*X(9)*((0.0D0,1.0D0)*Z003)))+Z004))
C     A(Z003)
      Z006=((X(8)/(X(9)**2))*((((X(10)-(X(11)*X(9)*((0.0D0,1.0D0)*Z003))
     &)-Z004)*X(2))-(2.0D0*LOG(((1.0D0-(Z005*EXP(((-Z004)*X(2)))))/(1.0D
     &0-Z005))))))
C     B(Z003)
      Z007=((((X(10)-(X(11)*X(9)*((0.0D0,1.0D0)*Z003)))-Z004)/(X(9)**2))
     &*((1.0D0-EXP(((-Z004)*X(2))))/(1.0D0-(Z005*EXP(((-Z004)*X(2)))))))
C     psi(Z003)
      Z008=EXP(((((0.0D0,1.0D0)*Z003)*(LOG(X(3))+((X(4)-(X(6)*X(7)))*X(2
     &))))+Z006+(Z007*X(12))+(X(6)*X(2)*((((1.0D0+X(7))**((0.0D0,1.0D0)*
     &Z003))*EXP((((X(13)**2)/2.0D0)*((0.0D0,1.0D0)*Z003)*(((0.0D0,1.0D0
     &)*Z003)-1.0D0))))-1.0D0))))
C     F
      R009 = (X(3)*EXP((X(4)*X(2))))
      WF002=DBLE(((EXP(((-(0.0D0,1.0D0))*XV*LOG(X(5))))*Z008)/((0.0D0,1.
     &0D0)*XV*R009)))
      RETURN
      END
      DOUBLE PRECISION FUNCTION WF012(XV)
      INTEGER NIN
      PARAMETER (NIN = 13)
      DOUBLE PRECISION XV
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE COMPLEX Z013, Z014, Z015, Z016, Z017
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
C     d(XV)
      Z013=SQRT((((X(10)-(X(11)*X(9)*((0.0D0,1.0D0)*XV)))**2)+((X(9)**2)
     &*(((0.0D0,1.0D0)*XV)+(XV**2)))))
C     g(XV)
      Z014=(((X(10)-(X(11)*X(9)*((0.0D0,1.0D0)*XV)))-Z013)/((X(10)-(X(11
     &)*X(9)*((0.0D0,1.0D0)*XV)))+Z013))
C     A(XV)
      Z015=((X(8)/(X(9)**2))*((((X(10)-(X(11)*X(9)*((0.0D0,1.0D0)*XV)))-
     &Z013)*X(2))-(2.0D0*LOG(((1.0D0-(Z014*EXP(((-Z013)*X(2)))))/(1.0D0-
     &Z014))))))
C     B(XV)
      Z016=((((X(10)-(X(11)*X(9)*((0.0D0,1.0D0)*XV)))-Z013)/(X(9)**2))*(
     &(1.0D0-EXP(((-Z013)*X(2))))/(1.0D0-(Z014*EXP(((-Z013)*X(2)))))))
C     psi(XV)
      Z017=EXP(((((0.0D0,1.0D0)*XV)*(LOG(X(3))+((X(4)-(X(6)*X(7)))*X(2))
     &))+Z015+(Z016*X(12))+(X(6)*X(2)*((((1.0D0+X(7))**((0.0D0,1.0D0)*XV
     &))*EXP((((X(13)**2)/2.0D0)*((0.0D0,1.0D0)*XV)*(((0.0D0,1.0D0)*XV)-
     &1.0D0))))-1.0D0))))
      WF012=DBLE(((EXP(((-(0.0D0,1.0D0))*XV*LOG(X(5))))*Z017)/((0.0D0,1.
     &0D0)*XV)))
      RETURN
      END

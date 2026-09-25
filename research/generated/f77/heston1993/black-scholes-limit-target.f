C     heston1993/black-scholes-limit-target
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = S
C       X(2) = K
C       X(3) = r
C       X(4) = tau
C       X(5) = kappa
C       X(6) = theta
C       X(7) = sigma
C       X(8) = lambda
C       X(9) = rho
C       X(10) = v
      PROGRAM WWMAIN
      INTEGER NIN
      PARAMETER (NIN = 10)
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
      PARAMETER (NIN = 10)
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION R011, R012, R013, R024, R025
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
      DOUBLE PRECISION WF001
      EXTERNAL WF001
      DOUBLE PRECISION WF014
      EXTERNAL WF014
C     integral over phi
      R011 = WWQUAD(WF001, 0.0D0, 0.0D0, 1)
C     P[1]
      R012 = ((1.0D0/2.0D0) + ((1.0D0/3.14159265358979324D0)*R011))
C     P_tT
      R013 = EXP(((-X(3))*X(4)))
C     integral over phi
      R024 = WWQUAD(WF014, 0.0D0, 0.0D0, 1)
C     P[2]
      R025 = ((1.0D0/2.0D0) + ((1.0D0/3.14159265358979324D0)*R024))
      WWEVAL = ((X(1)*R012) - (X(2)*R013*R025))
      RETURN
      END
      DOUBLE PRECISION FUNCTION WF001(XV)
      INTEGER NIN
      PARAMETER (NIN = 10)
      DOUBLE PRECISION XV
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION R002, R003, R004, R009
      DOUBLE COMPLEX Z005, Z006, Z007, Z008, Z010
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
C     a
      R002 = (X(5)*X(6))
C     b[1]
      R003 = ((X(5) + X(8)) - (X(9)*X(7)))
C     u[1]
      R004 = (1.0D0/2.0D0)
C     d[1]
      Z005=SQRT(((((X(9)*X(7)*XV*(0.0D0,1.0D0))-R003)**2)-((X(7)**2)*((2
     &.0D0*R004*XV*(0.0D0,1.0D0))-(XV**2)))))
C     g[1]
      Z006=(((R003-(X(9)*X(7)*XV*(0.0D0,1.0D0)))+Z005)/((R003-(X(9)*X(7)
     &*XV*(0.0D0,1.0D0)))-Z005))
C     C[1]
      Z007=((X(3)*XV*(0.0D0,1.0D0)*X(4))+((R002/(X(7)**2))*((((R003-(X(9
     &)*X(7)*XV*(0.0D0,1.0D0)))+Z005)*X(4))-(2.0D0*LOG(((1.0D0-(Z006*EXP
     &((Z005*X(4)))))/(1.0D0-Z006)))))))
C     D[1]
      Z008=((((R003-(X(9)*X(7)*XV*(0.0D0,1.0D0)))+Z005)/(X(7)**2))*((1.0
     &D0-EXP((Z005*X(4))))/(1.0D0-(Z006*EXP((Z005*X(4)))))))
C     x
      R009 = LOG(X(1))
C     f[1]
      Z010 = EXP((Z007 + (Z008*X(10)) + ((0.0D0,1.0D0)*XV*R009)))
      WF001=DBLE(((EXP(((-(0.0D0,1.0D0))*XV*LOG(X(2))))*Z010)/((0.0D0,1.
     &0D0)*XV)))
      RETURN
      END
      DOUBLE PRECISION FUNCTION WF014(XV)
      INTEGER NIN
      PARAMETER (NIN = 10)
      DOUBLE PRECISION XV
      DOUBLE PRECISION X(NIN)
      COMMON /WWIN/ X
      DOUBLE PRECISION R015, R016, R017, R022
      DOUBLE COMPLEX Z018, Z019, Z020, Z021, Z023
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
C     a
      R015 = (X(5)*X(6))
C     b[2]
      R016 = (X(5) + X(8))
C     u[2]
      R017 = (-(1.0D0/2.0D0))
C     d[2]
      Z018=SQRT(((((X(9)*X(7)*XV*(0.0D0,1.0D0))-R016)**2)-((X(7)**2)*((2
     &.0D0*R017*XV*(0.0D0,1.0D0))-(XV**2)))))
C     g[2]
      Z019=(((R016-(X(9)*X(7)*XV*(0.0D0,1.0D0)))+Z018)/((R016-(X(9)*X(7)
     &*XV*(0.0D0,1.0D0)))-Z018))
C     C[2]
      Z020=((X(3)*XV*(0.0D0,1.0D0)*X(4))+((R015/(X(7)**2))*((((R016-(X(9
     &)*X(7)*XV*(0.0D0,1.0D0)))+Z018)*X(4))-(2.0D0*LOG(((1.0D0-(Z019*EXP
     &((Z018*X(4)))))/(1.0D0-Z019)))))))
C     D[2]
      Z021=((((R016-(X(9)*X(7)*XV*(0.0D0,1.0D0)))+Z018)/(X(7)**2))*((1.0
     &D0-EXP((Z018*X(4))))/(1.0D0-(Z019*EXP((Z018*X(4)))))))
C     x
      R022 = LOG(X(1))
C     f[2]
      Z023 = EXP((Z020 + (Z021*X(10)) + ((0.0D0,1.0D0)*XV*R022)))
      WF014=DBLE(((EXP(((-(0.0D0,1.0D0))*XV*LOG(X(2))))*Z023)/((0.0D0,1.
     &0D0)*XV)))
      RETURN
      END

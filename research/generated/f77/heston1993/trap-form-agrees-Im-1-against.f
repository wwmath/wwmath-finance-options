C     heston1993/trap-form-agrees-Im-1-against
C     Generated from the Math AST by research/tools/f77.py
C     Inputs (read from standard input in this order):
C       X(1) = r
C       X(2) = phi
C       X(3) = tau
C       X(4) = kappa
C       X(5) = theta
C       X(6) = sigma
C       X(7) = lambda
C       X(8) = rho
C       X(9) = v
C       X(10) = S
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
      DOUBLE PRECISION R001, R002, R003, R008
      DOUBLE COMPLEX Z004, Z005, Z006, Z007, Z009
      DOUBLE PRECISION WWNCDF, WWNPDF, WWQUAD
C     a
      R001 = (X(4)*X(5))
C     b[1]
      R002 = ((X(4) + X(7)) - (X(8)*X(6)))
C     u[1]
      R003 = (1.0D0/2.0D0)
C     d[1]
      Z004=SQRT(((((X(8)*X(6)*X(2)*(0.0D0,1.0D0))-R002)**2)-((X(6)**2)*(
     &(2.0D0*R003*X(2)*(0.0D0,1.0D0))-(X(2)**2)))))
C     gt[1]
      Z005=(((R002-(X(8)*X(6)*X(2)*(0.0D0,1.0D0)))+(-Z004))/((R002-(X(8)
     &*X(6)*X(2)*(0.0D0,1.0D0)))-(-Z004)))
C     Ct[1]
      Z006=((X(1)*X(2)*(0.0D0,1.0D0)*X(3))+((R001/(X(6)**2))*((((R002-(X
     &(8)*X(6)*X(2)*(0.0D0,1.0D0)))+(-Z004))*X(3))-(2.0D0*LOG(((1.0D0-(Z
     &005*EXP(((-Z004)*X(3)))))/(1.0D0-Z005)))))))
C     Dt[1]
      Z007=((((R002-(X(8)*X(6)*X(2)*(0.0D0,1.0D0)))+(-Z004))/(X(6)**2))*
     &((1.0D0-EXP(((-Z004)*X(3))))/(1.0D0-(Z005*EXP(((-Z004)*X(3)))))))
C     x
      R008 = LOG(X(10))
C     ft[1]
      Z009 = EXP((Z006 + (Z007*X(9)) + ((0.0D0,1.0D0)*X(2)*R008)))
      WWEVAL = DIMAG(Z009)
      RETURN
      END

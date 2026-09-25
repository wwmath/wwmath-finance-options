C     wwmath F77 runtime: normal CDF/PDF and quadrature
      DOUBLE PRECISION FUNCTION WWNPDF(X)
      DOUBLE PRECISION X
      WWNPDF = EXP(-0.5D0*X*X)/2.50662827463100050D0
      RETURN
      END
C     Standard normal CDF, Hart (1968) double-precision algorithm
C     as given by G. West, Wilmott Magazine (2005).
      DOUBLE PRECISION FUNCTION WWNCDF(X)
      DOUBLE PRECISION X, XA, E, B, C
      XA = ABS(X)
      IF (XA .GT. 37.0D0) THEN
        C = 0.0D0
      ELSE
        E = EXP(-XA*XA/2.0D0)
        IF (XA .LT. 7.07106781186547D0) THEN
          B = 3.52624965998911D-02*XA + 0.700383064443688D0
          B = B*XA + 6.37396220353165D0
          B = B*XA + 33.912866078383D0
          B = B*XA + 112.079291497871D0
          B = B*XA + 221.213596169931D0
          B = B*XA + 220.206867912376D0
          C = E*B
          B = 8.83883476483184D-02*XA + 1.75566716318264D0
          B = B*XA + 16.064177579207D0
          B = B*XA + 86.7807322029461D0
          B = B*XA + 296.564248779674D0
          B = B*XA + 637.333633378831D0
          B = B*XA + 793.826512519948D0
          B = B*XA + 440.413735824752D0
          C = C/B
        ELSE
          B = XA + 0.65D0
          B = XA + 4.0D0/B
          B = XA + 3.0D0/B
          B = XA + 2.0D0/B
          B = XA + 1.0D0/B
          C = E/B/2.506628274631D0
        END IF
      END IF
      IF (X .GT. 0.0D0) C = 1.0D0 - C
      WWNCDF = C
      RETURN
      END
C     Composite Gauss-Legendre quadrature.
C     MODE 0: [A,B]; MODE 1: [A,inf) via x = A + t/(1-t);
C     MODE 2: (-inf,inf) via x = t/(1-t*t).
      DOUBLE PRECISION FUNCTION WWQUAD(F, A, B, MODE)
      DOUBLE PRECISION F, A, B
      INTEGER MODE
      EXTERNAL F
      INTEGER NG, NP
      PARAMETER (NG = 16, NP = 1024)
      DOUBLE PRECISION GX(NG), GW(NG)
      DOUBLE PRECISION LO, HI, H, C, T, XX, JAC, S, FX
      INTEGER I, K
      DATA GX(1) /-9.89400934991649939D-01/
      DATA GX(2) /-9.44575023073232600D-01/
      DATA GX(3) /-8.65631202387831755D-01/
      DATA GX(4) /-7.55404408355002999D-01/
      DATA GX(5) /-6.17876244402643771D-01/
      DATA GX(6) /-4.58016777657227370D-01/
      DATA GX(7) /-2.81603550779258915D-01/
      DATA GX(8) /-9.50125098376374405D-02/
      DATA GX(9) /9.50125098376374405D-02/
      DATA GX(10) /2.81603550779258915D-01/
      DATA GX(11) /4.58016777657227370D-01/
      DATA GX(12) /6.17876244402643771D-01/
      DATA GX(13) /7.55404408355002999D-01/
      DATA GX(14) /8.65631202387831755D-01/
      DATA GX(15) /9.44575023073232600D-01/
      DATA GX(16) /9.89400934991649939D-01/
      DATA GW(1) /2.71524594117541762D-02/
      DATA GW(2) /6.22535239386474565D-02/
      DATA GW(3) /9.51585116824926053D-02/
      DATA GW(4) /1.24628971255534071D-01/
      DATA GW(5) /1.49595988816576708D-01/
      DATA GW(6) /1.69156519395002647D-01/
      DATA GW(7) /1.82603415044923639D-01/
      DATA GW(8) /1.89450610455068641D-01/
      DATA GW(9) /1.89450610455068641D-01/
      DATA GW(10) /1.82603415044923639D-01/
      DATA GW(11) /1.69156519395002647D-01/
      DATA GW(12) /1.49595988816576708D-01/
      DATA GW(13) /1.24628971255534071D-01/
      DATA GW(14) /9.51585116824926053D-02/
      DATA GW(15) /6.22535239386474565D-02/
      DATA GW(16) /2.71524594117541762D-02/
      IF (MODE .EQ. 0) THEN
        LO = A
        HI = B
      ELSE IF (MODE .EQ. 1) THEN
        LO = 0.0D0
        HI = 1.0D0
      ELSE
        LO = -1.0D0
        HI = 1.0D0
      END IF
      H = (HI - LO)/NP
      S = 0.0D0
      DO 20 K = 1, NP
        C = LO + (K - 0.5D0)*H
        DO 10 I = 1, NG
          T = C + 0.5D0*H*GX(I)
          IF (MODE .EQ. 0) THEN
            XX = T
            JAC = 1.0D0
          ELSE IF (MODE .EQ. 1) THEN
            XX = A + T/(1.0D0 - T)
            JAC = 1.0D0/(1.0D0 - T)**2
          ELSE
            XX = T/(1.0D0 - T*T)
            JAC = (1.0D0 + T*T)/(1.0D0 - T*T)**2
          END IF
          FX = F(XX)
C         Infinite-range integrands decay to zero: treat overflow
C         (NaN or huge values) in the far tail as zero.
          IF (MODE .NE. 0) THEN
            IF (FX .NE. FX .OR. ABS(FX) .GT. 1.0D300) FX = 0.0D0
          END IF
          S = S + 0.5D0*H*GW(I)*JAC*FX
   10   CONTINUE
   20 CONTINUE
      WWQUAD = S
      RETURN
      END

# Turbine Control Functional Block Diagram

## Block Overview

The Turbine Control block implements closed-loop speed control using a PID controller with fuel valve positioning. It includes triple-redundant speed sensing, exhaust temperature monitoring, and compressor control.

## Block Inputs

| Tag | Type | Description |
|-----|------|-------------|
| TNH_SPEED_1 | AI | Primary speed sensor (0-6000 RPM) |
| TNH_SPEED_2 | AI | Redundant speed sensor 2 |
| TNH_SPEED_3 | AI | Redundant speed sensor 3 |
| SPEED_SETPOINT | AO | Target speed from load controller |
| EXHAUST_TEMP_1 | AI | Exhaust thermocouple 1 (0-700°C) |
| EXHAUST_TEMP_2 | AI | Exhaust thermocouple 2 |
| EXHAUST_TEMP_3 | AI | Exhaust thermocouple 3 |
| FUEL_VALVE_POS | AI | Fuel valve position feedback (0-100%) |
| IGV_POSITION_FB | AI | Inlet guide vane position feedback |
| COMPRESSOR_DISCH_PRESS | AI | Compressor discharge pressure |
| TURBINE_RUNNING | DI | Operating mode flag |

## Block Outputs

| Tag | Type | Description |
|-----|------|-------------|
| FUEL_VALVE_CMD | AO | Fuel valve position command (0-100%) |
| IGV_POSITION_CMD | AO | IGV position command (0-100%) |
| SPEED_ERROR | Calc | Speed deviation from setpoint |
| EXHAUST_TEMP_AVG | Calc | Average exhaust temperature |
| OVERSPEED_TRIP | DO | Overspeed protection trip |
| EXHAUST_TEMP_TRIP | DO | High exhaust temperature trip |

## Functional Block Diagram Logic

### 1. Speed Measurement and Voting

```
┌─────────────────────────────────────────────────────────────┐
│  SPEED MEASUREMENT BLOCK                                     │
│                                                              │
│  TNH_SPEED_1 ──┐                                            │
│                 ├──► MEDIAN ──► LOW_PASS_FILTER ──► TNH_SPEED_VALID
│  TNH_SPEED_2 ──┤      VOTER      (10 Hz)                    │
│                 │                                            │
│  TNH_SPEED_3 ──┘                                            │
│                                                              │
│  Logic:                                                      │
│  1. Calculate median of three sensors                       │
│  2. Apply 10Hz low-pass filter                             │
│  3. Check each sensor deviation from median                 │
│  4. Mark sensor BAD if deviation > 50 RPM                   │
│  5. Use median value as TNH_SPEED_VALID                     │
│                                                              │
│  IF ABS(TNH_SPEED_1 - MEDIAN) > 50 THEN                    │
│      TNH_SPEED_1_VALID = FALSE                              │
│      ALARM_SPEED_SENSOR_1 = TRUE                            │
│  END IF                                                      │
│                                                              │
│  IF ALL_SENSORS_BAD THEN                                    │
│      TRIP_TURBINE = TRUE                                    │
│  END IF                                                      │
└─────────────────────────────────────────────────────────────┘
```

### 2. Speed Control Loop

```
┌─────────────────────────────────────────────────────────────┐
│  SPEED CONTROL BLOCK (PID Controller)                       │
│                                                              │
│  SPEED_SETPOINT ──┐                                         │
│                    ├──► SUBTRACT ──► PID ──► RATE_LIMIT ──► FUEL_VALVE_CMD
│  TNH_SPEED_VALID ─┘                                         │
│                                                              │
│  PID Parameters:                                            │
│  - Kp = 2.5 (Proportional gain)                            │
│  - Ki = 0.8 (Integral gain)                                │
│  - Kd = 0.1 (Derivative gain)                              │
│  - Output limits: 0-100%                                    │
│  - Rate limit: 5%/sec                                       │
│  - Anti-windup: Enabled                                     │
│                                                              │
│  SPEED_ERROR = SPEED_SETPOINT - TNH_SPEED_VALID            │
│                                                              │
│  PID_OUTPUT = Kp × ERROR +                                  │
│               Ki × ∫ERROR dt +                              │
│               Kd × d(ERROR)/dt                              │
│                                                              │
│  FUEL_VALVE_CMD = RATE_LIMIT(PID_OUTPUT, 5%/sec)           │
│                                                              │
│  Anti-Windup Logic:                                         │
│  IF FUEL_VALVE_CMD >= 100% OR FUEL_VALVE_CMD <= 0% THEN    │
│      STOP_INTEGRAL_ACCUMULATION                             │
│  END IF                                                      │
└─────────────────────────────────────────────────────────────┘
```

### 3. Exhaust Temperature Monitoring

```
┌─────────────────────────────────────────────────────────────┐
│  EXHAUST TEMPERATURE BLOCK                                   │
│                                                              │
│  EXHAUST_TEMP_1 ──┐                                         │
│                    ├──► AVERAGE ──► RATE_CHECK ──► EXHAUST_TEMP_AVG
│  EXHAUST_TEMP_2 ──┤     (with bad                          │
│                    │      sensor                             │
│  EXHAUST_TEMP_3 ──┘      rejection)                         │
│                                                              │
│  Logic:                                                      │
│  1. Check each TC for valid range (0-700°C)                │
│  2. Reject any TC reading > 700°C or < 0°C                 │
│  3. Average remaining valid TCs                             │
│  4. Check rate of change                                    │
│                                                              │
│  VALID_TC_COUNT = 0                                         │
│  TEMP_SUM = 0                                               │
│                                                              │
│  FOR EACH TC IN [TC1, TC2, TC3]:                           │
│      IF TC >= 0 AND TC <= 700 THEN                         │
│          TEMP_SUM = TEMP_SUM + TC                           │
│          VALID_TC_COUNT = VALID_TC_COUNT + 1                │
│      END IF                                                  │
│  END FOR                                                     │
│                                                              │
│  IF VALID_TC_COUNT > 0 THEN                                 │
│      EXHAUST_TEMP_AVG = TEMP_SUM / VALID_TC_COUNT          │
│  ELSE                                                        │
│      TRIP_TURBINE = TRUE  // All TCs failed                │
│  END IF                                                      │
│                                                              │
│  // Rate of change check                                    │
│  TEMP_RATE = (EXHAUST_TEMP_AVG - PREV_TEMP) / SCAN_TIME   │
│  IF TEMP_RATE > 50°C/min THEN                              │
│      ALARM_RAPID_TEMP_RISE = TRUE                           │
│  END IF                                                      │
│                                                              │
│  // High temperature trip                                   │
│  IF EXHAUST_TEMP_AVG > 650°C FOR 2 seconds THEN            │
│      EXHAUST_TEMP_TRIP = TRUE                               │
│  END IF                                                      │
└─────────────────────────────────────────────────────────────┘
```

### 4. Overspeed Protection

```
┌─────────────────────────────────────────────────────────────┐
│  OVERSPEED PROTECTION BLOCK                                  │
│                                                              │
│  TNH_SPEED_VALID ──► COMPARE ──► TIMER ──► OVERSPEED_TRIP  │
│                         │                                    │
│                      3750 RPM                                │
│                                                              │
│  Logic:                                                      │
│  IF TNH_SPEED_VALID > 3750 RPM THEN                        │
│      START_TIMER(50ms)  // Very short delay                │
│      IF TIMER_DONE THEN                                     │
│          OVERSPEED_TRIP = TRUE                              │
│          FSV_MAIN_SOL = FALSE  // Immediate fuel shutoff   │
│          LOG_EVENT("Overspeed trip", TNH_SPEED_VALID)      │
│      END IF                                                  │
│  ELSE                                                        │
│      RESET_TIMER                                            │
│  END IF                                                      │
│                                                              │
│  // High speed alarm (pre-trip warning)                     │
│  IF TNH_SPEED_VALID > 3650 RPM THEN                        │
│      ALARM_HIGH_SPEED = TRUE                                │
│  END IF                                                      │
│                                                              │
│  // Acceleration limit                                      │
│  ACCELERATION = (TNH_SPEED_VALID - PREV_SPEED) / SCAN_TIME │
│  IF ACCELERATION > 300 RPM/sec THEN                         │
│      LIMIT_FUEL_VALVE_CMD = TRUE                            │
│      FUEL_VALVE_CMD = MIN(FUEL_VALVE_CMD, PREV_CMD + 1%)   │
│  END IF                                                      │
└─────────────────────────────────────────────────────────────┘
```

### 5. Inlet Guide Vane Control

```
┌─────────────────────────────────────────────────────────────┐
│  IGV CONTROL BLOCK                                           │
│                                                              │
│  FUEL_VALVE_CMD ──┐                                         │
│                    ├──► FUNCTION ──► RATE_LIMIT ──► IGV_POSITION_CMD
│  COMPRESSOR_PRESS ─┘     GENERATOR    (10%/sec)            │
│                                                              │
│  Logic:                                                      │
│  // IGV position follows fuel valve with offset             │
│  // to maintain surge margin                                │
│                                                              │
│  BASE_IGV = FUEL_VALVE_CMD × 0.8 + 10  // 10% minimum     │
│                                                              │
│  // Surge protection adjustment                             │
│  IF COMPRESSOR_DISCH_PRESS > 280 PSIG THEN                 │
│      SURGE_CORRECTION = -10%  // Open IGVs                 │
│  ELSE IF COMPRESSOR_DISCH_PRESS < 100 PSIG THEN            │
│      SURGE_CORRECTION = +5%   // Close IGVs                │
│  ELSE                                                        │
│      SURGE_CORRECTION = 0                                   │
│  END IF                                                      │
│                                                              │
│  IGV_DEMAND = BASE_IGV + SURGE_CORRECTION                   │
│  IGV_DEMAND = LIMIT(IGV_DEMAND, 10%, 90%)                  │
│                                                              │
│  // Rate limiting for smooth operation                      │
│  IGV_POSITION_CMD = RATE_LIMIT(IGV_DEMAND, 10%/sec)        │
│                                                              │
│  // Position feedback check                                 │
│  IF ABS(IGV_POSITION_CMD - IGV_POSITION_FB) > 5% THEN      │
│      IF TIMER(2 sec) THEN                                   │
│          ALARM_IGV_STUCK = TRUE                             │
│      END IF                                                  │
│  END IF                                                      │
└─────────────────────────────────────────────────────────────┘
```

## Block Parameters

| Parameter | Value | Units | Description |
|-----------|-------|-------|-------------|
| PID_KP | 2.5 | - | Proportional gain |
| PID_KI | 0.8 | - | Integral gain |
| PID_KD | 0.1 | - | Derivative gain |
| FUEL_RATE_LIMIT | 5 | %/sec | Maximum fuel valve rate |
| IGV_RATE_LIMIT | 10 | %/sec | Maximum IGV rate |
| SPEED_FILTER_CUTOFF | 10 | Hz | Low-pass filter frequency |
| OVERSPEED_SETPOINT | 3750 | RPM | Trip setpoint |
| HIGH_SPEED_ALARM | 3650 | RPM | Pre-trip alarm |
| EXHAUST_TEMP_TRIP | 650 | °C | High temperature trip |
| EXHAUST_TEMP_ALARM | 620 | °C | High temperature alarm |
| SPEED_DEVIATION_ALARM | 50 | RPM | Sensor deviation limit |
| ACCEL_LIMIT | 300 | RPM/sec | Maximum acceleration |

## Block Execution

**Scan Rate**: 10ms (100 Hz)

**Execution Order**:
1. Read all analog inputs
2. Speed measurement and voting
3. Exhaust temperature averaging
4. Overspeed protection check
5. Speed control PID calculation
6. IGV position calculation
7. Rate limiting
8. Write outputs
9. Update alarms

## Block Interlocks

**Inputs Required**:
- At least 2 of 3 speed sensors valid
- At least 2 of 3 exhaust TCs valid
- Fuel valve feedback within 5% of command
- TURBINE_RUNNING flag true

**Trips Generated**:
- OVERSPEED_TRIP (speed > 3750 RPM)
- EXHAUST_TEMP_TRIP (temp > 650°C)
- ALL_SPEED_SENSORS_FAILED
- ALL_EXHAUST_TCS_FAILED

## Testing and Commissioning

### Pre-Start Checks
1. Verify all speed sensors reading 0 RPM at standstill
2. Check exhaust TCs reading ambient temperature
3. Confirm fuel valve at 0% position
4. Verify IGVs at minimum position (10%)

### Dynamic Testing
1. Manually command fuel valve 0-100% in steps
2. Verify IGVs follow fuel valve position
3. Test overspeed trip at 3750 RPM (commissioning only)
4. Verify speed control response to setpoint changes
5. Test exhaust temperature trip logic

### Tuning
1. Start with conservative PID gains
2. Increase Kp until slight oscillation
3. Add Ki to eliminate steady-state error
4. Add Kd to reduce overshoot
5. Verify stable operation across load range

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-15 | Controls | Initial FBD documentation |
| 1.1 | 2024-02-20 | Engineering | Added IGV control logic |
| 1.2 | 2024-03-10 | Controls | Updated PID parameters after tuning |

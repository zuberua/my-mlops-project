# Start Sequence Functional Block Diagram

## Block Overview

The Start Sequence block implements the turbine startup state machine, coordinating crank motor, purge cycle, ignition, fuel introduction, and acceleration to operating speed. It ensures all permissives are met before advancing through each state.

## State Machine Diagram

```
                    START_BUTTON
                         │
                         ▼
    ┌────────────────────────────────────────────────────────┐
    │  IDLE STATE                                             │
    │  - All outputs OFF                                      │
    │  - Waiting for start command                            │
    │  - Check start permissives                              │
    └────────────────────────────────────────────────────────┘
                         │
                    Permissives OK
                         │
                         ▼
    ┌────────────────────────────────────────────────────────┐
    │  CRANK STATE                                            │
    │  - Energize crank motor                                 │
    │  - Wait for 1200 RPM                                    │
    │  - Timeout: 60 seconds                                  │
    └────────────────────────────────────────────────────────┘
                         │
                    Speed > 1200 RPM
                         │
                         ▼
    ┌────────────────────────────────────────────────────────┐
    │  PURGE STATE                                            │
    │  - Continue cranking                                    │
    │  - Open IGVs to 50%                                     │
    │  - Purge for 60 seconds                                 │
    │  - Verify airflow                                       │
    └────────────────────────────────────────────────────────┘
                         │
                    Purge Timer Done
                         │
                         ▼
    ┌────────────────────────────────────────────────────────┐
    │  IGNITION STATE                                         │
    │  - Enable igniter (10 sec pulse)                        │
    │  - Open pilot fuel valve                                │
    │  - Wait for flame detection                             │
    │  - Timeout: 15 seconds                                  │
    └────────────────────────────────────────────────────────┘
                         │
                    Flame Detected
                         │
                         ▼
    ┌────────────────────────────────────────────────────────┐
    │  ACCELERATION STATE                                     │
    │  - De-energize crank motor at 1500 RPM                  │
    │  - Open main fuel valve                                 │
    │  - Ramp speed to 2900 RPM                               │
    │  - Monitor exhaust temperature                          │
    │  - Timeout: 120 seconds                                 │
    └────────────────────────────────────────────────────────┘
                         │
                    Speed > 2900 RPM
                         │
                         ▼
    ┌────────────────────────────────────────────────────────┐
    │  RUNNING STATE                                          │
    │  - Transfer to speed control                            │
    │  - Enable synchronization                               │
    │  - Ready for load                                       │
    └────────────────────────────────────────────────────────┘
                         │
                    STOP_BUTTON or TRIP
                         │
                         ▼
    ┌────────────────────────────────────────────────────────┐
    │  SHUTDOWN STATE                                         │
    │  - Close all fuel valves                                │
    │  - Open breaker if closed                               │
    │  - Coast down to stop                                   │
    │  - Return to IDLE when speed < 500 RPM                  │
    └────────────────────────────────────────────────────────┘
```

## Block Inputs

| Tag | Type | Description |
|-----|------|-------------|
| START_BUTTON | DI | Operator start command |
| STOP_BUTTON | DI | Operator stop command |
| EMERGENCY_STOP | DI | Emergency stop button |
| TNH_SPEED_VALID | AI | Validated turbine speed |
| FLAME_DETECTOR | DI | Combustion flame present |
| CRANK_MOTOR_SPEED_OK | DI | Crank motor at speed |
| FUEL_PRESSURE_OK | DI | Fuel pressure adequate |
| LUBE_OIL_PRESS_OK | DI | Lube oil pressure adequate |
| COOLING_WATER_FLOW | DI | Cooling water flowing |
| ANY_TRIP_ACTIVE | DI | Any protection trip active |

## Block Outputs

| Tag | Type | Description |
|-----|------|-------------|
| CRANK_MOTOR_RUN | DO | Crank motor contactor |
| IGNITER_ENABLE | DO | Ignition system enable |
| FSV_PILOT_SOL | DO | Pilot fuel solenoid |
| FSV_MAIN_SOL | DO | Main fuel solenoid |
| START_SEQUENCE_ACTIVE | DO | Start in progress flag |
| TURBINE_RUNNING | DO | At operating speed flag |
| PURGE_TIMER_DONE | DO | Purge complete flag |
| SEQUENCE_STATE | INT | Current state number |

## Detailed State Logic

### IDLE State (State 0)

```
┌─────────────────────────────────────────────────────────────┐
│  IDLE STATE LOGIC                                            │
│                                                              │
│  Conditions to Enter:                                        │
│  - Power-up initialization                                   │
│  - After shutdown complete (speed < 500 RPM)                │
│  - After trip reset                                          │
│                                                              │
│  State Actions:                                              │
│  CRANK_MOTOR_RUN = FALSE                                    │
│  IGNITER_ENABLE = FALSE                                     │
│  FSV_PILOT_SOL = FALSE                                      │
│  FSV_MAIN_SOL = FALSE                                       │
│  START_SEQUENCE_ACTIVE = FALSE                              │
│  TURBINE_RUNNING = FALSE                                    │
│  SEQUENCE_STATE = 0                                         │
│                                                              │
│  Transition to CRANK:                                        │
│  IF START_BUTTON.RISING_EDGE AND                           │
│     NOT(EMERGENCY_STOP) AND                                 │
│     NOT(ANY_TRIP_ACTIVE) AND                                │
│     TNH_SPEED_VALID < 500 RPM AND                          │
│     FUEL_PRESSURE_OK AND                                    │
│     LUBE_OIL_PRESS_OK AND                                   │
│     COOLING_WATER_FLOW THEN                                 │
│      SEQUENCE_STATE = 1  // Go to CRANK                    │
│      LOG_EVENT("Start sequence initiated")                  │
│  END IF                                                      │
│                                                              │
│  Abort Conditions:                                           │
│  - EMERGENCY_STOP pressed                                   │
│  - Any trip active                                          │
└─────────────────────────────────────────────────────────────┘
```

### CRANK State (State 1)

```
┌─────────────────────────────────────────────────────────────┐
│  CRANK STATE LOGIC                                           │
│                                                              │
│  Conditions to Enter:                                        │
│  - From IDLE when start permissives met                     │
│                                                              │
│  State Actions:                                              │
│  ON_ENTRY:                                                   │
│      CRANK_MOTOR_RUN = TRUE                                 │
│      START_SEQUENCE_ACTIVE = TRUE                           │
│      START_TIMER(60 sec)  // Crank timeout                 │
│      LOG_EVENT("Crank motor started")                       │
│                                                              │
│  WHILE IN STATE:                                             │
│      // Monitor crank motor current                         │
│      IF CRANK_MOTOR_CURRENT > 150A THEN                    │
│          ALARM_MOTOR_OVERLOAD = TRUE                        │
│          ABORT_START                                        │
│      END IF                                                  │
│                                                              │
│  Transition to PURGE:                                        │
│  IF CRANK_MOTOR_SPEED_OK AND                               │
│     TNH_SPEED_VALID > 1200 RPM THEN                        │
│      SEQUENCE_STATE = 2  // Go to PURGE                    │
│      LOG_EVENT("Crank speed achieved", TNH_SPEED_VALID)    │
│  END IF                                                      │
│                                                              │
│  Timeout Condition:                                          │
│  IF TIMER_EXPIRED(60 sec) THEN                             │
│      ALARM_CRANK_TIMEOUT = TRUE                             │
│      ABORT_START                                            │
│      LOG_EVENT("Crank timeout - failed to reach speed")    │
│  END IF                                                      │
│                                                              │
│  Abort Conditions:                                           │
│  - STOP_BUTTON or EMERGENCY_STOP                           │
│  - Any trip active                                          │
│  - Crank motor overload                                     │
│  - Timeout                                                   │
└─────────────────────────────────────────────────────────────┘
```

### PURGE State (State 2)

```
┌─────────────────────────────────────────────────────────────┐
│  PURGE STATE LOGIC                                           │
│                                                              │
│  Purpose: Clear combustion chamber of any fuel vapors       │
│                                                              │
│  State Actions:                                              │
│  ON_ENTRY:                                                   │
│      CRANK_MOTOR_RUN = TRUE  // Continue cranking          │
│      IGV_POSITION_CMD = 50%  // Open for airflow           │
│      START_TIMER(60 sec)     // Purge duration             │
│      PURGE_TIMER_DONE = FALSE                               │
│      LOG_EVENT("Purge cycle started")                       │
│                                                              │
│  WHILE IN STATE:                                             │
│      // Verify adequate airflow                             │
│      IF COMPRESSOR_DISCH_PRESS < 20 PSIG THEN              │
│          ALARM_LOW_PURGE_AIRFLOW = TRUE                     │
│          ABORT_START                                        │
│      END IF                                                  │
│                                                              │
│      // Monitor speed stability                             │
│      IF TNH_SPEED_VALID < 1000 RPM THEN                    │
│          ALARM_SPEED_DROPPED = TRUE                         │
│          ABORT_START                                        │
│      END IF                                                  │
│                                                              │
│  Transition to IGNITION:                                     │
│  IF TIMER_EXPIRED(60 sec) THEN                             │
│      PURGE_TIMER_DONE = TRUE                                │
│      SEQUENCE_STATE = 3  // Go to IGNITION                 │
│      LOG_EVENT("Purge complete")                            │
│  END IF                                                      │
│                                                              │
│  Abort Conditions:                                           │
│  - STOP_BUTTON or EMERGENCY_STOP                           │
│  - Any trip active                                          │
│  - Low airflow                                              │
│  - Speed dropped below 1000 RPM                             │
└─────────────────────────────────────────────────────────────┘
```

### IGNITION State (State 3)

```
┌─────────────────────────────────────────────────────────────┐
│  IGNITION STATE LOGIC                                        │
│                                                              │
│  Purpose: Establish combustion with pilot fuel              │
│                                                              │
│  State Actions:                                              │
│  ON_ENTRY:                                                   │
│      CRANK_MOTOR_RUN = TRUE                                 │
│      IGNITER_ENABLE = TRUE                                  │
│      START_TIMER(10 sec)  // Igniter pulse duration        │
│      WAIT_TIMER(2 sec)    // Delay before fuel             │
│      LOG_EVENT("Ignition sequence started")                 │
│                                                              │
│  AFTER 2 SECONDS:                                            │
│      FSV_PILOT_SOL = TRUE  // Open pilot fuel              │
│      START_TIMER(15 sec)   // Flame detection timeout      │
│                                                              │
│  AFTER 10 SECONDS:                                           │
│      IGNITER_ENABLE = FALSE  // Turn off igniter           │
│                                                              │
│  WHILE IN STATE:                                             │
│      // Monitor for flame                                   │
│      IF FLAME_DETECTOR = TRUE FOR 2 seconds THEN           │
│          FLAME_ESTABLISHED = TRUE                           │
│      END IF                                                  │
│                                                              │
│  Transition to ACCELERATION:                                 │
│  IF FLAME_ESTABLISHED THEN                                  │
│      SEQUENCE_STATE = 4  // Go to ACCELERATION             │
│      LOG_EVENT("Flame detected")                            │
│  END IF                                                      │
│                                                              │
│  Timeout Condition:                                          │
│  IF TIMER_EXPIRED(15 sec) AND NOT(FLAME_ESTABLISHED) THEN │
│      ALARM_FLAME_FAILURE = TRUE                             │
│      FSV_PILOT_SOL = FALSE                                  │
│      IGNITER_ENABLE = FALSE                                 │
│      ABORT_START                                            │
│      LOG_EVENT("Ignition failed - no flame detected")      │
│  END IF                                                      │
│                                                              │
│  Abort Conditions:                                           │
│  - STOP_BUTTON or EMERGENCY_STOP                           │
│  - Any trip active                                          │
│  - Flame detection timeout                                  │
│  - Speed dropped below 1000 RPM                             │
└─────────────────────────────────────────────────────────────┘
```

### ACCELERATION State (State 4)

```
┌─────────────────────────────────────────────────────────────┐
│  ACCELERATION STATE LOGIC                                    │
│                                                              │
│  Purpose: Accelerate turbine to operating speed             │
│                                                              │
│  State Actions:                                              │
│  ON_ENTRY:                                                   │
│      FSV_MAIN_SOL = TRUE  // Open main fuel valve          │
│      SPEED_SETPOINT = 2900 RPM                              │
│      START_TIMER(120 sec)  // Acceleration timeout         │
│      LOG_EVENT("Acceleration started")                      │
│                                                              │
│  WHILE IN STATE:                                             │
│      // De-energize crank motor at 1500 RPM                │
│      IF TNH_SPEED_VALID > 1500 RPM THEN                    │
│          CRANK_MOTOR_RUN = FALSE                            │
│          LOG_EVENT("Crank motor stopped", TNH_SPEED_VALID) │
│      END IF                                                  │
│                                                              │
│      // Monitor flame continuously                          │
│      IF NOT(FLAME_DETECTOR) FOR 5 seconds THEN             │
│          ALARM_FLAME_LOSS = TRUE                            │
│          ABORT_START                                        │
│      END IF                                                  │
│                                                              │
│      // Monitor exhaust temperature                         │
│      IF EXHAUST_TEMP_AVG > 650°C THEN                      │
│          ALARM_HIGH_EXHAUST_TEMP = TRUE                     │
│          ABORT_START                                        │
│      END IF                                                  │
│                                                              │
│      // Check acceleration rate                             │
│      ACCEL_RATE = (TNH_SPEED_VALID - PREV_SPEED) / dt     │
│      IF ACCEL_RATE < 10 RPM/sec FOR 30 seconds THEN        │
│          ALARM_SLOW_ACCELERATION = TRUE                     │
│          // Continue but alarm operator                     │
│      END IF                                                  │
│                                                              │
│  Transition to RUNNING:                                      │
│  IF TNH_SPEED_VALID > 2900 RPM AND                         │
│     SPEED_STABLE FOR 10 seconds THEN                        │
│      SEQUENCE_STATE = 5  // Go to RUNNING                  │
│      TURBINE_RUNNING = TRUE                                 │
│      START_SEQUENCE_ACTIVE = FALSE                          │
│      LOG_EVENT("Turbine at operating speed")               │
│  END IF                                                      │
│                                                              │
│  Timeout Condition:                                          │
│  IF TIMER_EXPIRED(120 sec) THEN                            │
│      ALARM_ACCEL_TIMEOUT = TRUE                             │
│      ABORT_START                                            │
│      LOG_EVENT("Acceleration timeout")                      │
│  END IF                                                      │
│                                                              │
│  Abort Conditions:                                           │
│  - STOP_BUTTON or EMERGENCY_STOP                           │
│  - Any trip active                                          │
│  - Flame loss                                               │
│  - High exhaust temperature                                 │
│  - Acceleration timeout                                     │
└─────────────────────────────────────────────────────────────┘
```

### RUNNING State (State 5)

```
┌─────────────────────────────────────────────────────────────┐
│  RUNNING STATE LOGIC                                         │
│                                                              │
│  Purpose: Normal operation at speed                          │
│                                                              │
│  State Actions:                                              │
│  ON_ENTRY:                                                   │
│      TURBINE_RUNNING = TRUE                                 │
│      START_SEQUENCE_ACTIVE = FALSE                          │
│      ENABLE_SYNCHRONIZATION = TRUE                          │
│      ENABLE_LOAD_CONTROL = TRUE                             │
│      LOG_EVENT("Turbine running - ready for load")         │
│                                                              │
│  WHILE IN STATE:                                             │
│      // Speed control active                                │
│      // Load control active                                 │
│      // All protection systems active                       │
│                                                              │
│      // Monitor for shutdown command                        │
│      IF STOP_BUTTON.RISING_EDGE THEN                       │
│          INITIATE_NORMAL_SHUTDOWN                           │
│      END IF                                                  │
│                                                              │
│      // Monitor for trips                                   │
│      IF ANY_TRIP_ACTIVE THEN                               │
│          INITIATE_EMERGENCY_SHUTDOWN                        │
│      END IF                                                  │
│                                                              │
│  Transition to SHUTDOWN:                                     │
│  IF STOP_BUTTON OR ANY_TRIP_ACTIVE THEN                   │
│      SEQUENCE_STATE = 6  // Go to SHUTDOWN                 │
│      LOG_EVENT("Shutdown initiated")                        │
│  END IF                                                      │
└─────────────────────────────────────────────────────────────┘
```

### SHUTDOWN State (State 6)

```
┌─────────────────────────────────────────────────────────────┐
│  SHUTDOWN STATE LOGIC                                        │
│                                                              │
│  Purpose: Safe turbine shutdown                              │
│                                                              │
│  State Actions:                                              │
│  ON_ENTRY:                                                   │
│      // Immediate actions                                   │
│      FSV_MAIN_SOL = FALSE  // Close main fuel              │
│      FSV_PILOT_SOL = FALSE // Close pilot fuel             │
│      IGNITER_ENABLE = FALSE                                 │
│                                                              │
│      // If breaker closed, open it                          │
│      IF BREAKER_52A_CLOSED THEN                            │
│          GENERATOR_BREAKER_OPEN = TRUE                      │
│          WAIT_FOR_BREAKER_OPEN                              │
│      END IF                                                  │
│                                                              │
│      TURBINE_RUNNING = FALSE                                │
│      LOG_EVENT("Shutdown sequence started")                 │
│                                                              │
│  WHILE IN STATE:                                             │
│      // Monitor coast down                                  │
│      // Keep lube oil pump running                          │
│      // Keep cooling water flowing                          │
│                                                              │
│      // Log speed during coast down                         │
│      IF TNH_SPEED_VALID MOD 500 = 0 THEN                   │
│          LOG_EVENT("Coast down", TNH_SPEED_VALID)          │
│      END IF                                                  │
│                                                              │
│  Transition to IDLE:                                         │
│  IF TNH_SPEED_VALID < 500 RPM FOR 10 seconds THEN          │
│      SEQUENCE_STATE = 0  // Return to IDLE                 │
│      LOG_EVENT("Shutdown complete")                         │
│  END IF                                                      │
│                                                              │
│  Post-Shutdown Actions:                                      │
│  AFTER 5 MINUTES AT STANDSTILL:                             │
│      // Can stop auxiliary systems                          │
│      LUBE_OIL_PUMP_PERMISSIVE_STOP = TRUE                  │
│      COOLING_WATER_PUMP_PERMISSIVE_STOP = TRUE             │
└─────────────────────────────────────────────────────────────┘
```

## Abort Start Logic

```
┌─────────────────────────────────────────────────────────────┐
│  ABORT START SUBROUTINE                                      │
│                                                              │
│  Called when start sequence must be aborted                  │
│                                                              │
│  SUBROUTINE ABORT_START:                                     │
│      // Immediate safety actions                            │
│      FSV_MAIN_SOL = FALSE                                   │
│      FSV_PILOT_SOL = FALSE                                  │
│      IGNITER_ENABLE = FALSE                                 │
│      CRANK_MOTOR_RUN = FALSE                                │
│                                                              │
│      // Set flags                                            │
│      START_SEQUENCE_ACTIVE = FALSE                          │
│      START_ABORTED = TRUE                                   │
│                                                              │
│      // Log event with reason                               │
│      LOG_EVENT("Start aborted", ABORT_REASON)              │
│                                                              │
│      // Go to shutdown state                                │
│      SEQUENCE_STATE = 6                                     │
│                                                              │
│      // Latch abort alarm                                   │
│      ALARM_START_ABORTED = TRUE                             │
│  END SUBROUTINE                                              │
└─────────────────────────────────────────────────────────────┘
```

## Block Parameters

| Parameter | Value | Units | Description |
|-----------|-------|-------|-------------|
| CRANK_TIMEOUT | 60 | sec | Maximum time to reach crank speed |
| PURGE_DURATION | 60 | sec | Combustion chamber purge time |
| IGNITER_PULSE | 10 | sec | Igniter energize duration |
| FLAME_TIMEOUT | 15 | sec | Maximum time to detect flame |
| ACCEL_TIMEOUT | 120 | sec | Maximum acceleration time |
| CRANK_SPEED_TARGET | 1200 | RPM | Target speed for cranking |
| CRANK_MOTOR_STOP_SPEED | 1500 | RPM | Speed to stop crank motor |
| OPERATING_SPEED | 2900 | RPM | Target operating speed |
| SHUTDOWN_SPEED | 500 | RPM | Speed considered stopped |

## Block Execution

**Scan Rate**: 100ms (10 Hz)

**State Machine Priority**: Highest (executes first)

## Testing and Commissioning

### Pre-Commissioning Tests
1. Test each state transition manually
2. Verify all timers function correctly
3. Test abort logic from each state
4. Verify all permissives block start
5. Test emergency stop from each state

### Commissioning Tests
1. Complete start sequence with no load
2. Verify timing of each state
3. Test flame detection logic
4. Verify crank motor stops at correct speed
5. Test normal shutdown
6. Test trip shutdown

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-15 | Controls | Initial FBD documentation |
| 1.1 | 2024-02-10 | Engineering | Added purge airflow check |
| 1.2 | 2024-03-05 | Controls | Updated acceleration monitoring |

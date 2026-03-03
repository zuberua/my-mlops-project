# COMPARE_50 - COMPARE Function Block

## Block Information

- **Block Name**: COMPARE_50
- **Block Type**: COMPARE
- **Status Code**: 6

## Inputs

### FUNC
- **Device**: BT
- **Value**: GT
- **Data Type**: STRING
- **Range**: GT/LT/EQ/GE/LE/NE
- **Description**: Comparison function selector
- **Logic**: Determines type of comparison operation (Greater Than selected)
- **Purpose**: Selects comparison logic type

### IN1
- **Device**: BZ23Y
- **Value**: 0.00
- **Data Type**: REAL
- **Range**: 0-100 mils
- **Description**: First comparison input value
- **Logic**: Current position value from BZ23Y output
- **Purpose**: Primary comparison operand

### IN2
- **Device**: LP45T
- **Value**: 7.4
- **Data Type**: REAL
- **Range**: 0-100 mils
- **Description**: Second comparison input value (setpoint)
- **Logic**: Target position setpoint for comparison
- **Purpose**: Secondary comparison operand (reference)

### SENS
- **Device**: Constant
- **Value**: 0
- **Data Type**: REAL
- **Range**: 0-10 mils
- **Description**: Sensitivity/deadband for comparison
- **Logic**: Tolerance value for comparison hysteresis
- **Purpose**: Prevents chattering on boundary conditions

## Outputs

### OUT
- **Device**: GT
- **Value**: FALSE
- **Data Type**: BOOL
- **Range**: 0-1
- **Description**: Comparison result output
- **Logic**: Result of IN1 > IN2 + SENS evaluation (0.00 > 7.4 = FALSE)
- **Purpose**: Boolean output indicating comparison result
- **Interlocks**: FUNC must be valid

## Block Logic Summary

```
CASE FUNC OF
    'GT': OUT := (IN1 > IN2 + SENS)
    'LT': OUT := (IN1 < IN2 - SENS)
    'EQ': OUT := (ABS(IN1 - IN2) <= SENS)
END_CASE
```

## Current State

| Pin | Device | Value | Type |
|-----|--------|-------|------|
| FUNC | BT | GT | STRING |
| IN1 | BZ23Y | 0.00 | REAL |
| IN2 | LP45T | 7.4 | REAL |
| SENS | Constant | 0 | REAL |
| OUT | GT | FALSE | BOOL |

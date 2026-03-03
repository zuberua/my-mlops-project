# COMPARE_50 Function Block Diagram

## Block Description
COMPARE instruction block that compares two analog values and outputs a boolean result based on the comparison function.

## Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  BT ──────────────┐                                              │
│  (GT)             │                                              │
│                   │         ┌─────────────────────┐ 
                    │         │ COMPARE_50          │
│                   ├────────►│ FUNC                │              │
│  BZ23Y ───────────┤         │                     │              │
│  (0.00 mils)      ├────────►│ IN1                 │              │
│                   │         │                     │              │
│  LP45T ───────────┤         │                     │              │
│  (7.4 mils)       ├────────►│ IN2                 │              │
│                   │         │                     │              │
│  0 ───────────────┤         │                     │              │
│  (Constant)       └────────►│SENS                 │              │
│                             │              ┌───┐  │              │
│                             │              │ 6 │  │              │
│                             │              └───┘  │              │
│                             │                OUT  │─────────────►│ GT
│                             │                     │              │ (FALSE)
│                             └─────────────────────┘              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Pin Configuration

| Pin  | Direction | Device   | Value      | Type | Description                           |
|------|-----------|----------|------------|------|---------------------------------------|
| FUNC | INPUT     | BT       | GT         | STR  | Comparison function (GT/LT/EQ/etc)    |
| IN1  | INPUT     | BZ23Y    | 0.00 mils  | REAL | First comparison value                |
| IN2  | INPUT     | LP45T    | 7.4 mils   | REAL | Second comparison value               |
| SENS | INPUT     | Constant | 0          | REAL | Sensitivity/deadband for comparison   |
| OUT  | OUTPUT    | GT       | FALSE      | BOOL | Comparison result output              |

## Internal Status
- Status Code: 6 (Comparison Active)

## Logic
```
CASE FUNC OF
    'GT': GT := (IN1 > IN2 + SENS)     // Greater Than
    'LT': GT := (IN1 < IN2 - SENS)     // Less Than
    'EQ': GT := (ABS(IN1 - IN2) <= SENS) // Equal (within sensitivity)
    'GE': GT := (IN1 >= IN2 + SENS)    // Greater or Equal
    'LE': GT := (IN1 <= IN2 - SENS)    // Less or Equal
    'NE': GT := (ABS(IN1 - IN2) > SENS) // Not Equal
END_CASE

STATUS := 6  // Active comparison
```

## Current Evaluation
```
FUNC = 'GT'
IN1 = 0.00 mils (BZ23Y)
IN2 = 7.4 mils (LP45T)
SENS = 0

Result: 0.00 > 7.4 + 0 = FALSE
Therefore: GT = FALSE
```

## Purpose
Compares BZ23Y position (0.00 mils) against LP45T setpoint (7.4 mils) using Greater Than function. Output GT is FALSE because current position is less than setpoint.

## Typical Use Cases
- Position limit checking
- Threshold monitoring
- Setpoint validation
- Safety interlocks based on analog values

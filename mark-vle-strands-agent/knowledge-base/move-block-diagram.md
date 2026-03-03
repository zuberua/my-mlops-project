# MOVE_150 Function Block Diagram

## Block Description
MOVE instruction block that transfers a value from source to destination when enabled.

## Diagram

```

│                                                             
│  bz23y_a ────────┐                                         
│  (TRUE)          │                                        
│  Value: 0        │         ┌─────────────────────┐         
│                  ├────────►│ SRC                 │         
│                            │                     │        
│  ENABLE ─────────┤         │   MOVE_150          │         
│  (TRUE)          └────────►│ EN                  │         
│                            │                     │         
│                            │              ┌───┐  │         
                             │              │ 2 │  │         
                             │              └───┘  │         
                             │                DEST │────────► BZ23Y
                             │                     │ 0.00 mils
                             └─────────────────────┘         

```

## Pin Configuration

| Pin  | Direction | Device   | Value      | Type | Description                    |
|------|-----------|----------|------------|------|--------------------------------|
| SRC  | INPUT     | bz23y_a  | 0          | BOOL | Source trigger input           |
| EN   | INPUT     | ENABLE   | TRUE       | BOOL | Enable signal                  |
| DEST | OUTPUT    | BZ23Y    | 0.00 mils  | REAL | Destination output position    |

## Internal Status
- Status Code: 2 (Active/Running)

## Logic
```
IF (bz23y_a = TRUE) AND (ENABLE = TRUE) THEN
    BZ23Y := SRC_VALUE
    STATUS := 2
ELSE
    STATUS := 0
END_IF
```

## Purpose
Transfers position value to BZ23Y output when both trigger and enable conditions are met.

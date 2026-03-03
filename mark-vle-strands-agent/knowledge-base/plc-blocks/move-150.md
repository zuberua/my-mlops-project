# MOVE_150 - MOVE Function Block

## Block Information

- **Block Name**: MOVE_150
- **Block Type**: MOVE
- **Status Code**: 2

## Inputs

### SRC
- **Device**: bz23y_a
- **Value**: 0
- **Data Type**: BOOL
- **Range**: 0-1
- **Description**: Source trigger input for MOVE operation
- **Logic**: When TRUE triggers data transfer from source to destination
- **Purpose**: Initiates position value transfer to output
- **Interlocks**: ENABLE must be TRUE

### EN
- **Device**: ENABLE
- **Value**: TRUE
- **Data Type**: BOOL
- **Range**: 0-1
- **Description**: Enable signal for MOVE instruction
- **Logic**: Must be TRUE for block to execute
- **Purpose**: Safety enable for MOVE operation
- **Interlocks**: System ready state

## Outputs

### DEST
- **Device**: BZ23Y
- **Value**: 0.00
- **Data Type**: REAL
- **Range**: 0-100 mils
- **Description**: Destination output for position value
- **Logic**: Receives value from SRC when both inputs are TRUE
- **Purpose**: Position control output for actuator
- **Interlocks**: bz23y_a AND ENABLE

## Block Logic Summary

```
IF (SRC = TRUE) AND (EN = TRUE) THEN
    DEST := SOURCE_VALUE
    STATUS := 2
END_IF
```

## Current State

| Pin | Device | Value | Type |
|-----|--------|-------|------|
| SRC | bz23y_a | 0 | BOOL |
| EN | ENABLE | TRUE | BOOL |
| DEST | BZ23Y | 0.00 | REAL |

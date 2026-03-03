# SPEED_ERROR

## Metadata
- **Block**: Turbine Control
- **I/O Type**: Calculated
- **Tag**: SPEED_ERROR
- **Hardware**: Internal
- **Signal Range**: -300 to +300 RPM

## Description

Difference between setpoint and actual speed

## Logic Implementation

### Purpose

Input to PID speed controller

### Algorithm

Algorithm not documented.

### Code/Configuration

```
SPEED_ERROR = SPEED_SETPOINT - TNH_SPEED_MEDIAN
```

## Related I/O Points

[To be documented]

## Troubleshooting

### Common Issues

[To be documented during commissioning and operation]

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Auto-generated | System | Initial documentation from export |

---
*This document was auto-generated. Please review and enhance with operational details.*

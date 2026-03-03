# EXHAUST_TEMP_AVG

## Metadata
- **Block**: Turbine Control
- **I/O Type**: Calculated
- **Tag**: EXHAUST_TEMP_AVG
- **Hardware**: Internal
- **Signal Range**: 0-700°C

## Description

Average of three exhaust thermocouples

## Logic Implementation

### Purpose

Primary exhaust temperature for control and protection

### Algorithm

Algorithm not documented.

### Code/Configuration

```
AVG = (TC1 + TC2 + TC3) / 3 with bad sensor rejection
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

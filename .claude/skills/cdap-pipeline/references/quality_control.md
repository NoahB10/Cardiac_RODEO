# Quality Control and Troubleshooting Guide

Comprehensive guide for quality control, debugging, and troubleshooting CDAP pipeline issues.

## Quality Control Checklist

### Stage 1: Filtering

- [ ] Check SNR values are realistic (typically 2-5)
- [ ] Verify oxygen range is reasonable (0-80% air)
- [ ] Confirm segment completeness ≥ 50%
- [ ] Validate timestamps are continuous
- [ ] Inspect timeline alignment across wells
- [ ] Review rejection statistics

### Stage 2: Aggregation

- [ ] Verify all timeline hours are present
- [ ] Check for excessive NaN values (> 40%)
- [ ] Validate concentration labels match
- [ ] Confirm replicate counts are correct
- [ ] Review interpolation warnings

### Stage 3: Prism Loading

- [ ] Check drug name matching succeeded
- [ ] Verify sparse column removal logs
- [ ] Confirm backups were created
- [ ] Validate Prism file structure

## Data Quality Metrics

### SNR (Signal-to-Noise Ratio)

**Typical values**:
- Excellent: SNR ≥ 3.0
- Good: SNR 2.0-3.0
- Marginal: SNR 1.4-2.0
- Poor: SNR < 1.4 (rejected)

### Oxygen Range

**Expected values**:
- Normoxic (baseline): 14-20% air
- Hypoxic (drug effect): 5-14% air
- Invalid: < 0% or > 80%

### Segment Completeness

**Typical values**:
- Good: ≥ 70%
- Acceptable: 50-70%
- Poor: < 50% (rejected)

## Common Issues and Solutions

### Issue 1: "No drug map found"

**Solutions**:
1. Check drug map files exist: `ls LogFiles/P*DrugMap.csv`
2. Verify file names: P1DrugMap.csv, P2DrugMap.csv, P3DrugMap.csv

### Issue 2: "All wells rejected in Stage 1"

**Solutions**:
1. Check SNR in raw data
2. Lower SNR threshold: `Stage1Config(min_snr=1.4)`
3. For Plate 3, verify SNR is in column 12

### Issue 3: "Stage 2 tables empty"

**Solutions**:
1. Check Stage 1 output: `ls Stage1_Raw/Amiodarone/`
2. Check timeline CSV: `ls *_timeline.csv`
3. Read processing notes

### Issue 4: "No Stage 2 data found for drug"

**Solutions**:
1. Check drug folders: `ls Stage2_Tables/`
2. Verify drug name matching

### Issue 5: "Permission denied" on Prism files

**Solutions**:
1. Close GraphPad Prism
2. Stage 3 will create timestamped backup automatically

## Best Practices

1. Always run validation checks after each stage
2. Keep debug mode on during development
3. Save raw files for inspection
4. Document rejection statistics
5. Compare results across parameter settings
6. Use version control for configurations
7. Create backups before Stage 3
8. Monitor memory usage
9. Log all warnings/errors
10. Validate timestamps

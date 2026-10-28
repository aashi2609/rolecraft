# Plan-Tier Migration Analysis

## Current State

### Legacy Plan Tiers
- `free`
- `basic`
- `premium`
- `elite`
- `starter`
- `growth`
- `scale`

### New Plan Tiers
- `resume_builder`
- `job_search`
- `complete`
- `corporate_annual`
- `corporate_lifetime`

## Migration Status

The enum values have been added to the database via migration `b4c5d6e7f8a9_sync_enum_values.py`. Both legacy and new values now coexist in the `plan_tier` enum type.

## Entitlement Code Analysis

**TO BE COMPLETED**: Need to analyze the entitlement code to determine how it currently treats legacy plan tiers.

### Questions to Answer

1. Does the entitlement code check for specific plan tier values?
2. What happens when a user has a legacy tier (e.g., `free`, `basic`)?
3. Are there any hardcoded checks for specific tier names?
4. Does the code use a mapping or feature flags?
5. Are there any errors or unexpected behavior with legacy tiers?

### Recommended Investigation

Search the codebase for:
- References to `plan_tier` in service layer
- Subscription checks and feature gates
- Rate limiting by plan
- Feature access control logic

## Proposed Mapping

**TO BE DETERMINED**: Product decision required.

### Draft Mapping Options

#### Option 1: Legacy → New Functional Mapping
- `free` → `resume_builder` (basic resume generation)
- `basic` → `job_search` (resume + job search)
- `premium` → `complete` (all features)
- `elite` → `complete` (all features, grandfathered)
- `starter` → `resume_builder` (entry-level)
- `growth` → `job_search` (growing business)
- `scale` → `corporate_annual` (enterprise)

#### Option 2: Status-Based Migration
- Keep legacy tiers as-is
- Add new tiers for new signups
- Gradually migrate users to new tiers via communication
- Eventually deprecate legacy tiers

#### Option 3: Data Migration with Grace Period
- Migrate all users to new tiers based on feature parity
- Keep mapping table for reference
- Allow manual override for special cases

## Migration Strategy

Once mapping is decided:

1. **Create data migration script** to update existing subscriptions
2. **Test on branch** with real data
3. **Communicate with users** about any changes to their plan
4. **Run migration** during maintenance window
5. **Verify entitlements** work correctly after migration
6. **Monitor** for issues post-migration

## Rollback Plan

If migration causes issues:

1. Restore from pre-migration backup
2. Revert code to legacy tier checks
3. Investigate root cause
4. Fix and retry migration

## Next Steps

1. **Product decision**: Choose mapping strategy
2. **Code analysis**: Document current entitlement behavior
3. **Data impact assessment**: Count users per legacy tier
4. **Migration script**: Write and test data migration
5. **Communication plan**: Notify affected users
6. **Schedule migration**: Coordinate with marketing/support

## Dependencies

- Part 7: Test data cleanup (some test accounts may have subscriptions)
- Part 4: Schema integrity review (verify subscriptions table constraints)
- Product approval for mapping strategy

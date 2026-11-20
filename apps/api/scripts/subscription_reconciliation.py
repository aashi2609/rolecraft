#!/usr/bin/env python
"""
D5: Subscription data reconciliation and cleanup report.

Generates:
1. Count of users by subscription status (pending, active, cancelled)
2. Count of subscriptions by plan tier
3. Expired subscriptions (renews_at < now, status=active)
4. Orphaned subscriptions (no user, foreign key constraint should prevent this)
5. Users without any subscription (should not happen - constraint)
6. Audit trail summary (created, updated, cancelled counts)
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure apps/api root is in sys.path
api_root = str(Path(__file__).resolve().parent.parent)
if api_root not in sys.path:
    sys.path.insert(0, api_root)

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.database import engine
from models import (
    PlanTier,
    Subscription,
    SubscriptionAuditLog,
    SubscriptionStatus,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def get_subscription_stats(db) -> dict[str, Any]:
    """Get comprehensive subscription statistics and health report."""

    report: dict[str, Any] = {}

    # 1. Total subscriptions by status
    status_counts = {}
    for status in SubscriptionStatus:
        count = (
            await db.scalar(
                select(func.count()).select_from(Subscription).where(Subscription.status == status)
            )
            or 0
        )
        status_counts[status.value] = count

    report["subscriptions_by_status"] = status_counts

    # 2. Subscriptions by plan tier
    tier_counts = {}
    for tier in PlanTier:
        count = (
            await db.scalar(
                select(func.count()).select_from(Subscription).where(Subscription.plan_tier == tier)
            )
            or 0
        )
        if count > 0:
            tier_counts[tier.value] = count

    report["subscriptions_by_plan_tier"] = tier_counts

    # 3. Expired subscriptions (renews_at < now, status=active)
    expired_count = (
        await db.scalar(
            select(func.count())
            .select_from(Subscription)
            .where(
                and_(
                    Subscription.status == SubscriptionStatus.active,
                    Subscription.renews_at.is_not(None),
                    Subscription.renews_at < datetime.now(timezone.utc),
                )
            )
        )
        or 0
    )

    report["expired_active_subscriptions"] = expired_count

    # 4. Get list of expired subscriptions for detailed review
    expired_subs = await db.scalars(
        select(Subscription)
        .where(
            and_(
                Subscription.status == SubscriptionStatus.active,
                Subscription.renews_at.is_not(None),
                Subscription.renews_at < datetime.now(timezone.utc),
            )
        )
        .order_by(Subscription.renews_at.asc())
    )

    expired_details = []
    for sub in expired_subs.all():
        user = await db.get(User, sub.user_id)
        expired_details.append(
            {
                "subscription_id": str(sub.id),
                "user_id": str(sub.user_id),
                "user_email": user.email if user else "Unknown",
                "plan_tier": sub.plan_tier.value,
                "expired_at": sub.renews_at.isoformat() if sub.renews_at else None,
                "days_expired": (datetime.now(timezone.utc) - sub.renews_at).days
                if sub.renews_at
                else None,
            }
        )

    report["expired_subscriptions_detail"] = expired_details

    # 5. Subscriptions by user role
    role_counts = {}
    for role in UserRole:
        count = (
            await db.scalar(
                select(func.count()).select_from(Subscription).where(Subscription.role == role)
            )
            or 0
        )
        if count > 0:
            role_counts[role.value] = count

    report["subscriptions_by_user_role"] = role_counts

    # 6. Average subscription lifetime for cancelled subscriptions
    # (only for those with both started_at and created audit logs)
    cancelled_subs = await db.scalars(
        select(Subscription)
        .where(Subscription.status == SubscriptionStatus.cancelled)
        .order_by(Subscription.id)
    )

    cancelled_count = len(cancelled_subs.all())
    report["total_cancelled_subscriptions"] = cancelled_count

    # 7. Audit log summary
    audit_actions = {}
    for action in ["create", "update_plan", "update_status", "cancel", "grant"]:
        count = (
            await db.scalar(
                select(func.count())
                .select_from(SubscriptionAuditLog)
                .where(SubscriptionAuditLog.action == action)
            )
            or 0
        )
        if count > 0:
            audit_actions[action] = count

    report["audit_log_by_action"] = audit_actions

    # 8. Recent audit changes (last 10)
    recent_audits = await db.scalars(
        select(SubscriptionAuditLog).order_by(SubscriptionAuditLog.created_at.desc()).limit(10)
    )

    recent_changes = []
    for audit in recent_audits.all():
        user = await db.get(User, audit.user_id)
        recent_changes.append(
            {
                "action": audit.action,
                "user_email": user.email if user else "Unknown",
                "old_status": audit.old_status,
                "new_status": audit.new_status,
                "old_plan_tier": audit.old_plan_tier,
                "new_plan_tier": audit.new_plan_tier,
                "reason": audit.reason,
                "timestamp": audit.created_at.isoformat(),
            }
        )

    report["recent_audit_changes"] = recent_changes

    # 9. Pending subscriptions (user signup, awaiting payment)
    pending_count = (
        await db.scalar(
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.status == SubscriptionStatus.pending)
        )
        or 0
    )

    report["pending_subscriptions_awaiting_payment"] = pending_count

    # 10. Data integrity checks
    integrity_issues = []

    # Check for users without subscriptions
    users_without_subs = await db.scalars(
        select(User).where(~User.id.in_(select(Subscription.user_id)))
    )
    users_without_subs_list = users_without_subs.all()
    if users_without_subs_list:
        integrity_issues.append(
            {
                "issue": "Users without subscriptions",
                "count": len(users_without_subs_list),
                "severity": "high",
                "users": [
                    {"id": str(u.id), "email": u.email, "role": u.role.value}
                    for u in users_without_subs_list[:5]
                ],
            }
        )

    report["data_integrity_issues"] = integrity_issues

    return report


async def cleanup_expired_subscriptions(db, dry_run: bool = True) -> dict[str, Any]:
    """
    Identify and optionally cancel expired subscriptions.

    D5 implementation: Only identify for now. Actual cancellation is manual
    to prevent accidental loss of service.

    Returns:
        dict with summary of actions
    """
    from services.subscription_service import log_subscription_change

    expired_subs = await db.scalars(
        select(Subscription)
        .where(
            and_(
                Subscription.status == SubscriptionStatus.active,
                Subscription.renews_at.is_not(None),
                Subscription.renews_at < datetime.now(timezone.utc),
            )
        )
        .order_by(Subscription.renews_at.asc())
    )

    expired_list = expired_subs.all()
    result: dict[str, Any] = {
        "dry_run": dry_run,
        "expired_found": len(expired_list),
        "processed": 0,
        "failed": 0,
        "errors": [],
        "subscriptions_processed": [],
    }

    for sub in expired_list:
        try:
            user = await db.get(User, sub.user_id)

            sub_info = {
                "subscription_id": str(sub.id),
                "user_id": str(sub.user_id),
                "user_email": user.email if user else "Unknown",
                "plan_tier": sub.plan_tier.value,
                "expired_at": sub.renews_at.isoformat() if sub.renews_at else None,
            }

            if not dry_run:
                # Actually cancel the subscription
                old_status = sub.status.value
                sub.status = SubscriptionStatus.cancelled

                await log_subscription_change(
                    db,
                    subscription_id=sub.id,
                    user_id=sub.user_id,
                    action="cancel",
                    old_status=old_status,
                    new_status=SubscriptionStatus.cancelled.value,
                    reason="Automatic expiration (renewal date passed)",
                )

            result["subscriptions_processed"].append(sub_info)
            result["processed"] += 1

        except Exception as exc:
            logger.error(f"Error processing subscription {sub.id}: {exc}")
            result["failed"] += 1
            result["errors"].append(
                {
                    "subscription_id": str(sub.id),
                    "error": str(exc),
                }
            )

    if not dry_run:
        await db.commit()
        logger.info(f"Cleanup complete: {result['processed']} subscriptions cancelled")
    else:
        logger.info(f"Dry run: {result['expired_found']} subscriptions would be cancelled")

    return result


async def get_part2_integrity_report(db) -> dict[str, Any]:
    """Part 2.7 read-only data report on subscription integrity."""
    from services.subscription_service import LIVE_STATUSES

    report: dict[str, Any] = {}

    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    users_with_subs = await db.scalar(select(func.count(func.distinct(Subscription.user_id)))) or 0
    report["users_total"] = total_users
    report["users_with_0_subscription_rows"] = total_users - users_with_subs

    # users with more than 1 row, and more than 1 live row
    multi_row = (
        await db.execute(
            select(Subscription.user_id, func.count().label("c"))
            .group_by(Subscription.user_id)
            .having(func.count() > 1)
        )
    ).all()
    report["users_with_multiple_rows"] = len(multi_row)

    live_multi = (
        await db.execute(
            select(Subscription.user_id, func.count().label("c"))
            .where(Subscription.status.in_(LIVE_STATUSES))
            .group_by(Subscription.user_id)
            .having(func.count() > 1)
        )
    ).all()
    report["users_with_multiple_live_rows"] = len(live_multi)

    # rows whose role differs from the user's role
    role_mismatch = (
        await db.scalar(
            select(func.count())
            .select_from(Subscription)
            .join(User, User.id == Subscription.user_id)
            .where(Subscription.role != User.role)
        )
        or 0
    )
    report["rows_role_mismatch"] = role_mismatch

    # legacy plan tiers still present
    all_tiers = (await db.scalars(select(Subscription.plan_tier).distinct())).all()
    report["plan_tiers_present"] = sorted(t.value for t in all_tiers)

    # active rows past renews_at (expired but not cancelled)
    expired_active = (
        await db.scalar(
            select(func.count())
            .select_from(Subscription)
            .where(
                and_(
                    Subscription.status == SubscriptionStatus.active,
                    Subscription.renews_at.is_not(None),
                    Subscription.renews_at < datetime.now(timezone.utc),
                )
            )
        )
        or 0
    )
    report["active_rows_past_valid_until"] = expired_active

    # subscription rows with no user (orphans)
    orphans = (
        await db.scalar(
            select(func.count())
            .select_from(Subscription)
            .outerjoin(User, User.id == Subscription.user_id)
            .where(User.id.is_(None))
        )
        or 0
    )
    report["subscription_rows_without_user"] = orphans

    return report


async def cleanup_duplicate_live_subscriptions(db, dry_run: bool = True) -> dict[str, Any]:
    """For users with >1 live row keep the newest active (else newest pending)
    and mark the others cancelled with an audit-log entry. Never deletes."""
    from services.subscription_service import LIVE_STATUSES, log_subscription_change

    live_rows = (
        (
            await db.execute(
                select(Subscription)
                .where(Subscription.status.in_(LIVE_STATUSES))
                .order_by(
                    Subscription.user_id,
                    Subscription.started_at.desc().nullslast(),
                    Subscription.id.desc(),
                )
            )
        )
        .scalars()
        .all()
    )

    by_user: dict = {}
    for s in live_rows:
        by_user.setdefault(s.user_id, []).append(s)

    result: dict[str, Any] = {
        "dry_run": dry_run,
        "users_with_multiple_live_rows": 0,
        "cancelled": 0,
        "details": [],
    }

    for user_id, subs in by_user.items():
        if len(subs) <= 1:
            continue
        result["users_with_multiple_live_rows"] += 1
        # keep newest active if any, else newest pending (list already sorted desc)
        keep = next((s for s in subs if s.status == SubscriptionStatus.active), subs[0])
        for s in subs:
            if s.id == keep.id:
                continue
            result["details"].append(
                {
                    "subscription_id": str(s.id),
                    "user_id": str(user_id),
                    "kept_id": str(keep.id),
                    "old_status": s.status.value,
                }
            )
            if not dry_run:
                old = s.status.value
                s.status = SubscriptionStatus.cancelled
                await log_subscription_change(
                    db,
                    subscription_id=s.id,
                    user_id=user_id,
                    action="cancel",
                    old_status=old,
                    new_status=SubscriptionStatus.cancelled.value,
                    reason="Duplicate live subscription cleanup (kept newest)",
                )
            result["cancelled"] += 1

    if not dry_run:
        await db.commit()
    return result


async def main():
    """Generate subscription reconciliation report and cleanup analysis."""
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        logger.info("Starting subscription reconciliation report...")

        # Generate stats report
        stats = await get_subscription_stats(db)

        print("\n" + "=" * 80)
        print("SUBSCRIPTION RECONCILIATION REPORT")
        print("=" * 80)
        print(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")

        print("SUBSCRIPTIONS BY STATUS:")
        for status, count in stats.get("subscriptions_by_status", {}).items():
            print(f"  {status}: {count}")

        print("\nSUBSCRIPTIONS BY PLAN TIER:")
        for tier, count in stats.get("subscriptions_by_plan_tier", {}).items():
            print(f"  {tier}: {count}")

        print("\nSUBSCRIPTIONS BY USER ROLE:")
        for role, count in stats.get("subscriptions_by_user_role", {}).items():
            print(f"  {role}: {count}")

        expired_count = stats.get("expired_active_subscriptions", 0)
        print(f"\nEXPIRED ACTIVE SUBSCRIPTIONS: {expired_count}")
        if expired_count > 0:
            print("\nExpired subscription details:")
            for exp in stats.get("expired_subscriptions_detail", [])[:10]:
                print(
                    f"  - {exp['user_email']} ({exp['plan_tier']}): expired {exp['days_expired']} days ago"
                )

        print(
            f"\nPENDING SUBSCRIPTIONS (awaiting payment): {stats.get('pending_subscriptions_awaiting_payment', 0)}"
        )

        print("\nAUDIT LOG SUMMARY:")
        for action, count in stats.get("audit_log_by_action", {}).items():
            print(f"  {action}: {count}")

        print("\nRECENT AUDIT CHANGES (last 10):")
        for change in stats.get("recent_audit_changes", []):
            print(
                f"  - {change['action']}: {change['user_email']} ({change.get('new_status', 'N/A')})"
            )

        print("\nDATA INTEGRITY CHECKS:")
        integrity = stats.get("data_integrity_issues", [])
        if integrity:
            for issue in integrity:
                print(f"  ⚠️  {issue['issue']} ({issue['severity']}): {issue['count']}")
        else:
            print("  ✅ All checks passed")

        # Part 2.7 integrity report
        print("\n" + "=" * 80)
        print("PART 2 DATA REPORT (read-only)")
        print("=" * 80)
        p2 = await get_part2_integrity_report(db)
        for k, v in p2.items():
            print(f"  {k}: {v}")

        dup = await cleanup_duplicate_live_subscriptions(db, dry_run=True)
        print(
            f"\nDuplicate live rows: {dup['users_with_multiple_live_rows']} users, "
            f"{dup['cancelled']} rows would be cancelled (dry run)"
        )

        # Cleanup analysis (dry run)
        print("\n" + "=" * 80)
        print("CLEANUP ANALYSIS (DRY RUN)")
        print("=" * 80)
        cleanup_result = await cleanup_expired_subscriptions(db, dry_run=True)
        print(f"Expired subscriptions found: {cleanup_result['expired_found']}")
        print("To actually cancel expired subscriptions, use:")
        print("  python subscription_reconciliation.py --cleanup")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    if "--cleanup" in sys.argv:
        logger.warning("Running cleanup mode: SUBSCRIPTIONS WILL BE CANCELLED")

        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async def cleanup():
            async with session_factory() as db:
                # Duplicate live rows MUST be cleaned before the unique index
                # migration runs, otherwise CREATE UNIQUE INDEX fails.
                dup = await cleanup_duplicate_live_subscriptions(db, dry_run=False)
                print(f"Duplicate live cleanup: {dup['cancelled']} rows cancelled")
                result = await cleanup_expired_subscriptions(db, dry_run=False)
                print(
                    f"\nCleanup result: {result['processed']} cancelled, {result['failed']} failed"
                )

        asyncio.run(cleanup())
    else:
        asyncio.run(main())

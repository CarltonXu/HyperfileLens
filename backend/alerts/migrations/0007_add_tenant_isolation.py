import django.db.models.deletion
from django.db import migrations, models


SYSTEM_TENANT_NAME = "administrator"


def backfill_alert_tenants(apps, schema_editor):
    Tenant = apps.get_model("tenants", "Tenant")
    User = apps.get_model("accounts", "User")
    AlertPolicy = apps.get_model("alerts", "AlertPolicy")
    AlertRecord = apps.get_model("alerts", "AlertRecord")
    NotificationChannel = apps.get_model("alerts", "NotificationChannel")
    NotificationLog = apps.get_model("alerts", "NotificationLog")
    SystemMetric = apps.get_model("alerts", "SystemMetric")

    system_tenant = Tenant.objects.filter(name=SYSTEM_TENANT_NAME).first()
    user_tenant_by_id = {
        user.id: user.tenant_id
        for user in User.objects.exclude(tenant_id__isnull=True).only("id", "tenant_id")
    }

    for policy in AlertPolicy.objects.filter(tenant__isnull=True).iterator():
        tenant_id = user_tenant_by_id.get(policy.created_by) or getattr(system_tenant, "id", None)
        if tenant_id:
            policy.tenant_id = tenant_id
            policy.save(update_fields=["tenant"])

    policy_tenant_by_id = {
        policy.id: policy.tenant_id
        for policy in AlertPolicy.objects.exclude(tenant_id__isnull=True).only("id", "tenant_id")
    }

    for record in AlertRecord.objects.filter(tenant__isnull=True).iterator():
        tenant_id = policy_tenant_by_id.get(record.policy_id) or getattr(system_tenant, "id", None)
        if tenant_id:
            record.tenant_id = tenant_id
            record.save(update_fields=["tenant"])

    record_tenant_by_id = {
        record.id: record.tenant_id
        for record in AlertRecord.objects.exclude(tenant_id__isnull=True).only("id", "tenant_id")
    }

    for log in NotificationLog.objects.filter(tenant__isnull=True).iterator():
        tenant_id = record_tenant_by_id.get(log.alert_record_id) or getattr(system_tenant, "id", None)
        if tenant_id:
            log.tenant_id = tenant_id
            log.save(update_fields=["tenant"])

    if system_tenant:
        NotificationChannel.objects.filter(tenant__isnull=True).update(tenant=system_tenant)
        SystemMetric.objects.filter(tenant__isnull=True).update(tenant=system_tenant)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_user_mfa_enabled_user_mfa_method_user_mfa_secret"),
        ("tenants", "0006_alter_tenantinvitation_token"),
        ("alerts", "0006_notification_log_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="alertpolicy",
            name="tenant",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="alert_policies",
                to="tenants.tenant",
            ),
        ),
        migrations.AddField(
            model_name="alertrecord",
            name="tenant",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="alert_records",
                to="tenants.tenant",
            ),
        ),
        migrations.AddField(
            model_name="notificationchannel",
            name="tenant",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="notification_channels",
                to="tenants.tenant",
            ),
        ),
        migrations.AddField(
            model_name="notificationlog",
            name="tenant",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="notification_logs",
                to="tenants.tenant",
            ),
        ),
        migrations.AddField(
            model_name="systemmetric",
            name="tenant",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="system_metrics",
                to="tenants.tenant",
            ),
        ),
        migrations.RunPython(backfill_alert_tenants, migrations.RunPython.noop),
    ]

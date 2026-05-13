"""URL configuration for the global alert center."""

from django.urls import path

from .views import AlertPolicyViewSet, AlertRecordViewSet, MetadataResourcesView, MetadataView, NotificationChannelViewSet, NotificationLogViewSet, SystemMonitorView


policy_list = AlertPolicyViewSet.as_view({"get": "list", "post": "create"})
policy_detail = AlertPolicyViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"})
policy_enable = AlertPolicyViewSet.as_view({"post": "enable"})
policy_disable = AlertPolicyViewSet.as_view({"post": "disable"})
policy_duplicate = AlertPolicyViewSet.as_view({"post": "duplicate"})

record_list = AlertRecordViewSet.as_view({"get": "list"})
record_detail = AlertRecordViewSet.as_view({"get": "retrieve"})
record_acknowledge = AlertRecordViewSet.as_view({"post": "acknowledge"})
record_resolve = AlertRecordViewSet.as_view({"post": "resolve"})

channel_list = NotificationChannelViewSet.as_view({"get": "list", "post": "create"})
channel_detail = NotificationChannelViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"})
channel_test = NotificationChannelViewSet.as_view({"post": "test"})
channel_details = NotificationChannelViewSet.as_view({"get": "details"})

notification_log_list = NotificationLogViewSet.as_view({"get": "list"})
notification_log_detail = NotificationLogViewSet.as_view({"get": "retrieve"})
notification_log_stats = NotificationLogViewSet.as_view({"get": "stats"})


urlpatterns = [
    path("system/", SystemMonitorView.as_view(), name="alert-system-monitor"),
    path("policies/", policy_list, name="alert-policy-list"),
    path("policies/<uuid:pk>/", policy_detail, name="alert-policy-detail"),
    path("policies/<uuid:pk>/enable/", policy_enable, name="alert-policy-enable"),
    path("policies/<uuid:pk>/disable/", policy_disable, name="alert-policy-disable"),
    path("policies/<uuid:pk>/duplicate/", policy_duplicate, name="alert-policy-duplicate"),
    path("records/", record_list, name="alert-record-list"),
    path("records/<uuid:pk>/", record_detail, name="alert-record-detail"),
    path("records/<uuid:pk>/acknowledge/", record_acknowledge, name="alert-record-acknowledge"),
    path("records/<uuid:pk>/resolve/", record_resolve, name="alert-record-resolve"),
    path("notification-channels/", channel_list, name="notification-channel-list"),
    path("notification-channels/<uuid:pk>/", channel_detail, name="notification-channel-detail"),
    path("notification-channels/<uuid:pk>/test/", channel_test, name="notification-channel-test"),
    path("notification-channels/<uuid:pk>/details/", channel_details, name="notification-channel-details"),
    path("notification-logs/", notification_log_list, name="notification-log-list"),
    path("notification-logs/stats/", notification_log_stats, name="notification-log-stats"),
    path("notification-logs/<uuid:pk>/", notification_log_detail, name="notification-log-detail"),
    path("metadata/resources/", MetadataResourcesView.as_view(), name="alert-metadata-resources"),
    path("metadata/<str:kind>/", MetadataView.as_view(), name="alert-metadata"),
]

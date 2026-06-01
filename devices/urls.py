from django.urls import path

from .fine_views import (
    DeviceCheckoutAddFinesView,
    DeviceFineListView,
    DeviceReturnInspectionView,
)
from .settings_views import (
    DeviceCheckoutPolicyUpdateView,
    DeviceFineMarkStatusView,
    DeviceFineTypeCreateView,
    DeviceFineTypeDeleteView,
    DeviceFineTypeListView,
    DeviceFineTypeUpdateView,
    DeviceSettingsHubView,
)
from .views import (
    DeviceCreateView,
    DeviceDetailView,
    DeviceExportCsvView,
    DeviceImportView,
    DeviceListView,
    DevicePrintBulkView,
    DevicePrintLabelView,
    DeviceUpdateView,
    PublicDeviceReportView,
)

app_name = 'devices'

urlpatterns = [
    path('', DeviceListView.as_view(), name='list'),
    path('new/', DeviceCreateView.as_view(), name='create'),
    path('import/', DeviceImportView.as_view(), name='import'),
    path('export.csv', DeviceExportCsvView.as_view(), name='export_csv'),
    path('print-selected/', DevicePrintBulkView.as_view(), name='print_bulk'),
    path('fines/', DeviceFineListView.as_view(), name='fine_list'),
    path('settings/', DeviceSettingsHubView.as_view(), name='settings_hub'),
    path('settings/fine-types/', DeviceFineTypeListView.as_view(), name='finetype_list'),
    path('settings/fine-types/new/', DeviceFineTypeCreateView.as_view(), name='finetype_create'),
    path('settings/fine-types/<int:pk>/edit/', DeviceFineTypeUpdateView.as_view(), name='finetype_edit'),
    path('settings/fine-types/<int:pk>/delete/', DeviceFineTypeDeleteView.as_view(), name='finetype_delete'),
    path('settings/checkout-policy/', DeviceCheckoutPolicyUpdateView.as_view(), name='checkout_policy'),
    path('fines/<int:fine_pk>/status/', DeviceFineMarkStatusView.as_view(), name='fine_mark_status'),
    path('report/<uuid:report_uuid>/', PublicDeviceReportView.as_view(), name='public_report'),
    path('<int:pk>/return/', DeviceReturnInspectionView.as_view(), name='return_inspection'),
    path(
        '<int:pk>/checkouts/<int:checkout_pk>/add-fines/',
        DeviceCheckoutAddFinesView.as_view(),
        name='checkout_add_fines',
    ),
    path('<int:pk>/', DeviceDetailView.as_view(), name='detail'),
    path('<int:pk>/print/', DevicePrintLabelView.as_view(), name='print_label'),
    path('<int:pk>/edit/', DeviceUpdateView.as_view(), name='edit'),
]

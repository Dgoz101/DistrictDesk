from django.urls import path

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
    path('report/<uuid:report_uuid>/', PublicDeviceReportView.as_view(), name='public_report'),
    path('<int:pk>/', DeviceDetailView.as_view(), name='detail'),
    path('<int:pk>/print/', DevicePrintLabelView.as_view(), name='print_label'),
    path('<int:pk>/edit/', DeviceUpdateView.as_view(), name='edit'),
]

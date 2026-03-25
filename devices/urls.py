from django.urls import path

from .views import DeviceCreateView, DeviceListView, DeviceUpdateView

app_name = 'devices'

urlpatterns = [
    path('', DeviceListView.as_view(), name='list'),
    path('new/', DeviceCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', DeviceUpdateView.as_view(), name='edit'),
]

from django.urls import path

from .settings_views import (
    PriorityLevelCreateView,
    PriorityLevelDeleteView,
    PriorityLevelListView,
    PriorityLevelUpdateView,
    TicketCategoryCreateView,
    TicketCategoryDeleteView,
    TicketCategoryListView,
    TicketCategoryUpdateView,
    TicketSettingsHubView,
)
from .views import (
    TicketAdminUpdateView,
    TicketAssignView,
    TicketCommentAddView,
    TicketCreateView,
    TicketDetailView,
    TicketListView,
)

app_name = 'tickets'

urlpatterns = [
    path('settings/', TicketSettingsHubView.as_view(), name='settings_hub'),
    path('settings/categories/', TicketCategoryListView.as_view(), name='category_list'),
    path('settings/categories/new/', TicketCategoryCreateView.as_view(), name='category_create'),
    path('settings/categories/<int:pk>/edit/', TicketCategoryUpdateView.as_view(), name='category_edit'),
    path('settings/categories/<int:pk>/delete/', TicketCategoryDeleteView.as_view(), name='category_delete'),
    path('settings/priorities/', PriorityLevelListView.as_view(), name='priority_list'),
    path('settings/priorities/new/', PriorityLevelCreateView.as_view(), name='priority_create'),
    path('settings/priorities/<int:pk>/edit/', PriorityLevelUpdateView.as_view(), name='priority_edit'),
    path('settings/priorities/<int:pk>/delete/', PriorityLevelDeleteView.as_view(), name='priority_delete'),
    path('', TicketListView.as_view(), name='list'),
    path('new/', TicketCreateView.as_view(), name='create'),
    path('<int:pk>/admin/update/', TicketAdminUpdateView.as_view(), name='admin_update'),
    path('<int:pk>/assign/', TicketAssignView.as_view(), name='assign'),
    path('<int:pk>/comment/', TicketCommentAddView.as_view(), name='comment_add'),
    path('<int:pk>/', TicketDetailView.as_view(), name='detail'),
]

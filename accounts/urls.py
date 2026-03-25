from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from .views import (
    DistrictDeskLoginView,
    DistrictDeskLogoutView,
    RegisterView,
    UserAdminUpdateView,
    UserListView,
)

app_name = 'accounts'

urlpatterns = [
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/edit/', UserAdminUpdateView.as_view(), name='user_edit'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', DistrictDeskLoginView.as_view(), name='login'),
    path('logout/', DistrictDeskLogoutView.as_view(), name='logout'),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.txt',
            subject_template_name='registration/password_reset_subject.txt',
            success_url=reverse_lazy('accounts:password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url=reverse_lazy('accounts:password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
]

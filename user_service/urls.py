from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    UserRegistrationView,
    UserProfileView, 
    LogoutView,
    GoogleLoginView,
    reset_password_view,
    CompleteProfileView,
    AdminLogsView  # 👈 Adicione a nova view aqui
)

urlpatterns = [
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),  
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),

    # 1. Coloque a rota de logs AQUI (antes dos que não usam barra)
    path('admin-logs/', AdminLogsView.as_view(), name='admin-logs'),

    path("auth/google/", GoogleLoginView.as_view(), name="google-login"),
    path("profile/complete/", CompleteProfileView.as_view(), name="complete-profile"), 
    path('reset-password/', views.reset_password_view, name='reset-password'), # Adicionada a barra no final
]
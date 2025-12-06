from django.urls import path
from .views import (
    UserRegistrationView,
    VendorRegistrationView,
    CustomerJoinStoreView,
    CustomTokenObtainPairView
)

urlpatterns = [
    path('', UserRegistrationView.as_view(), name='register'),
    path('vendor/', VendorRegistrationView.as_view(), name='vendor-register'),
    path('join-store/', CustomerJoinStoreView.as_view(), name='join-store'),
]
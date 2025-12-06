from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
CustomerProfileViewSet,
CustomerAddressViewSet,
CustomerWishlistViewSet,
CustomerReviewViewSet,
CustomerNotificationViewSet,
CustomerDashboardView
)
router = DefaultRouter()
router.register(r'profiles', CustomerProfileViewSet, basename='customer-profile')
router.register(r'addresses', CustomerAddressViewSet, basename='customer-address')
router.register(r'wishlist', CustomerWishlistViewSet, basename='customer-wishlist')
router.register(r'reviews', CustomerReviewViewSet, basename='customer-review')
router.register(r'notifications', CustomerNotificationViewSet,
basename='customer-notification')
urlpatterns = [
path('dashboard/', CustomerDashboardView.as_view(), name='customer-dashboard'),
path('', include(router.urls)),
]
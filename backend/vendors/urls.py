from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantViewSet, PublicTenantListView, MyTenantsView, SwitchTenantView
from . import views

router = DefaultRouter(trailing_slash=False)
router.register(r'', views.TenantViewSet, basename='tenant')

urlpatterns = [
    path('public/', PublicTenantListView.as_view(), name='public-tenants'),
    
    path('my/', MyTenantsView.as_view(), name='my-tenants'),
    path('switch/', SwitchTenantView.as_view(), name='switch-tenant'),
  
    path('', include(router.urls)),
]
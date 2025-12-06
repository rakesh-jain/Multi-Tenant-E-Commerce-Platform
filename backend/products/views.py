from rest_framework import generics, permissions, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from .models import Product
from .serializers import ProductSerializer
from vendors.models import TenantUser

class ProductViewSet(ModelViewSet):
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['price', 'name', 'created_at']
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Product.objects.none()
        
        queryset = Product.objects.filter(tenant=tenant)
        user_role = getattr(self.request, 'user_role', None)
        
        if user_role == TenantUser.Role.CUSTOMER:
            queryset = queryset.filter(is_active=True)
        elif user_role == TenantUser.Role.STAFF:
            pass
        
        return queryset
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            serializer.save(
                tenant=tenant,
                created_by=self.request.user
            )
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response([])
        
        categories = Product.objects.filter(
            tenant=tenant,
            is_active=True
        ).values_list('category', flat=True).distinct()
        
        return Response([cat for cat in categories if cat])
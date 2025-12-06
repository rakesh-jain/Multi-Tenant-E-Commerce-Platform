from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Sum, Q
from django.contrib.auth import get_user_model

from .models import Tenant, TenantUser
from .serializers import (
    TenantSerializer, 
    TenantUserSerializer, 
    TenantUserCreateSerializer,
    TenantStatsSerializer
)
from products.models import Product
from orders.models import Order

User = get_user_model()

class TenantViewSet(viewsets.ModelViewSet):
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser:
            return Tenant.objects.all()
        elif user.is_vendor:
            owned_tenants = Tenant.objects.filter(owner=user)
            member_tenants = Tenant.objects.filter(
                tenantuser__user=user,
                tenantuser__is_active=True
            )
            return (owned_tenants | member_tenants).distinct()
        else:
            return Tenant.objects.filter(
                tenantuser__user=user,
                tenantuser__is_active=True
            )
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get tenant statistics (store owners only)"""
        tenant = self.get_object()
        
        if not self._has_tenant_permission(tenant, request.user):
            return Response(
                {'error': 'You do not have permission to view these stats'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        total_products = Product.objects.filter(tenant=tenant).count()
        active_products = Product.objects.filter(tenant=tenant, is_active=True).count()
        total_orders = Order.objects.filter(tenant=tenant).count()
        pending_orders = Order.objects.filter(
            tenant=tenant, 
            status__in=['pending', 'processing']
        ).count()
        
        total_customers = TenantUser.objects.filter(
            tenant=tenant,
            role=TenantUser.Role.CUSTOMER,
            is_active=True
        ).count()
        
        total_staff = TenantUser.objects.filter(
            tenant=tenant,
            role=TenantUser.Role.STAFF,
            is_active=True
        ).count()
        
        revenue_result = Order.objects.filter(
            tenant=tenant,
            status=Order.Status.DELIVERED
        ).aggregate(total_revenue=Sum('total_amount'))
        
        revenue = revenue_result['total_revenue'] or 0
        
        stats_data = {
            'total_products': total_products,
            'active_products': active_products,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'total_customers': total_customers,
            'total_staff': total_staff,
            'revenue': revenue
        }
        
        serializer = TenantStatsSerializer(stats_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get all members of a tenant (store owners and staff only)"""
        tenant = self.get_object()
        
        if not self._has_tenant_permission(tenant, request.user):
            return Response(
                {'error': 'You do not have permission to view members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        members = TenantUser.objects.filter(tenant=tenant, is_active=True)
        serializer = TenantUserSerializer(members, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Add a member to a tenant (store owners only)"""
        tenant = self.get_object()
        
        try:
            tenant_user = TenantUser.objects.get(
                user=request.user,
                tenant=tenant,
                role=TenantUser.Role.STORE_OWNER
            )
        except TenantUser.DoesNotExist:
            return Response(
                {'error': 'Only store owners can add members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = TenantUserCreateSerializer(
            data=request.data,
            context={'tenant': tenant}
        )
        
        if serializer.is_valid():
            tenant_user = serializer.save()
            return Response(
                TenantUserSerializer(tenant_user).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        """Remove a member from a tenant (store owners only)"""
        tenant = self.get_object()
        member_id = request.data.get('member_id')
        
        if not member_id:
            return Response(
                {'error': 'member_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            requesting_user = TenantUser.objects.get(
                user=request.user,
                tenant=tenant,
                role=TenantUser.Role.STORE_OWNER
            )
        except TenantUser.DoesNotExist:
            return Response(
                {'error': 'Only store owners can remove members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if member_id == requesting_user.id:
            return Response(
                {'error': 'Cannot remove yourself from the tenant'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            member = TenantUser.objects.get(id=member_id, tenant=tenant)
            
            if member.role == TenantUser.Role.STORE_OWNER:
                store_owners_count = TenantUser.objects.filter(
                    tenant=tenant,
                    role=TenantUser.Role.STORE_OWNER,
                    is_active=True
                ).count()
                
                if store_owners_count <= 1:
                    return Response(
                        {'error': 'Cannot remove the only store owner'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            member.is_active = False
            member.save()
            
            return Response(
                {'message': 'Member removed successfully'},
                status=status.HTTP_200_OK
            )
            
        except TenantUser.DoesNotExist:
            return Response(
                {'error': 'Member not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def update_member_role(self, request, pk=None):
        """Update a member's role (store owners only)"""
        tenant = self.get_object()
        member_id = request.data.get('member_id')
        new_role = request.data.get('role')
        
        if not member_id or not new_role:
            return Response(
                {'error': 'member_id and role are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_roles = dict(TenantUser.Role.choices)
        if new_role not in valid_roles:
            return Response(
                {'error': f'Invalid role. Valid roles: {", ".join(valid_roles.keys())}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        try:
            requesting_user = TenantUser.objects.get(
                user=request.user,
                tenant=tenant,
                role=TenantUser.Role.STORE_OWNER
            )
        except TenantUser.DoesNotExist:
            return Response(
                {'error': 'Only store owners can update roles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            member = TenantUser.objects.get(id=member_id, tenant=tenant)
            if member.id == requesting_user.id and new_role != TenantUser.Role.STORE_OWNER:
                return Response(
                    {'error': 'Cannot change your own role from store owner'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if (member.role == TenantUser.Role.STORE_OWNER and 
                new_role != TenantUser.Role.STORE_OWNER):
                
                store_owners_count = TenantUser.objects.filter(
                    tenant=tenant,
                    role=TenantUser.Role.STORE_OWNER,
                    is_active=True
                ).count()
                
                if store_owners_count <= 1:
                    return Response(
                        {'error': 'Cannot change role of the only store owner'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            member.role = new_role
            member.save()
            
            return Response(
                TenantUserSerializer(member).data,
                status=status.HTTP_200_OK
            )
            
        except TenantUser.DoesNotExist:
            return Response(
                {'error': 'Member not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def _has_tenant_permission(self, tenant, user):
        if user.is_superuser:
            return True
        
        try:
            tenant_user = TenantUser.objects.get(
                user=user,
                tenant=tenant,
                is_active=True
            )
            return tenant_user.role in [
                TenantUser.Role.STORE_OWNER,
                TenantUser.Role.STAFF
            ]
        except TenantUser.DoesNotExist:
            return False

class PublicTenantListView(generics.ListAPIView):
    serializer_class = TenantSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return Tenant.objects.filter(is_active=True)

class MyTenantsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        tenant_users = TenantUser.objects.filter(
            user=user,
            is_active=True
        ).select_related('tenant')
        
        tenants = [tu.tenant for tu in tenant_users]
        owned_tenants = Tenant.objects.filter(owner=user)
        for tenant in owned_tenants:
            if tenant not in tenants:
                tenants.append(tenant)
        
        serializer = TenantSerializer(tenants, many=True)
        return Response(serializer.data)

class SwitchTenantView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        tenant_id = request.data.get('tenant_id')
        
        if not tenant_id:
            return Response(
                {'error': 'tenant_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            tenant_user = TenantUser.objects.get(
                user=request.user,
                tenant_id=tenant_id,
                is_active=True
            )
            return Response({
                'message': 'Tenant switched successfully',
                'tenant': {
                    'id': tenant_user.tenant.id,
                    'name': tenant_user.tenant.name,
                    'domain': tenant_user.tenant.domain,
                    'subdomain': tenant_user.tenant.subdomain
                },
                'role': tenant_user.role
            })
            
        except TenantUser.DoesNotExist:
            try:
                tenant = Tenant.objects.get(id=tenant_id, owner=request.user)
                tenant_user, created = TenantUser.objects.get_or_create(
                    user=request.user,
                    tenant=tenant,
                    defaults={'role': TenantUser.Role.STORE_OWNER}
                )
                
                return Response({
                    'message': 'Tenant switched successfully',
                    'tenant': {
                        'id': tenant.id,
                        'name': tenant.name,
                        'domain': tenant.domain,
                        'subdomain': tenant.subdomain
                    },
                    'role': tenant_user.role
                })
                
            except Tenant.DoesNotExist:
                return Response(
                    {'error': 'You are not a member of this tenant'},
                    status=status.HTTP_403_FORBIDDEN
                )
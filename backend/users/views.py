from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from vendors.models import Tenant, TenantUser


from .serializer import (
    UserRegistrationSerializer,
    VendorRegistrationSerializer,
    CustomTokenObtainPairSerializer
)


User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        }, status=status.HTTP_201_CREATED)


class VendorRegistrationView(generics.CreateAPIView):
    queryset = Tenant.objects.all()
    serializer_class = VendorRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = serializer.save()
        
        return Response({
            'message': 'Vendor registered successfully',
            'tenant': {
                'id': tenant.id,
                'name': tenant.name,
                'domain': tenant.domain,
                'subdomain': tenant.subdomain
            },
            'owner': {
                'id': tenant.owner.id,
                'email': tenant.owner.email,
                'name': f"{tenant.owner.first_name} {tenant.owner.last_name}"
            }
        }, status=status.HTTP_201_CREATED)


class CustomerJoinStoreView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        tenant_id = request.data.get('tenant_id')
        
        if not tenant_id:
            return Response(
                {'error': 'tenant_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            tenant = Tenant.objects.get(id=tenant_id, is_active=True)
        except Tenant.DoesNotExist:
            return Response(
                {'error': 'Tenant not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        tenant_user, created = TenantUser.objects.get_or_create(
            user=request.user,
            tenant=tenant,
            defaults={'role': TenantUser.Role.CUSTOMER}
        )
        
        if not created and not tenant_user.is_active:
            tenant_user.is_active = True
            tenant_user.save()
        
        return Response({
            'message': 'Successfully joined store',
            'tenant': {
                'id': tenant.id,
                'name': tenant.name
            },
            'role': tenant_user.role
        })


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
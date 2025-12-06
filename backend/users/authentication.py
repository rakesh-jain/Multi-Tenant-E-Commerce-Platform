import jwt
from django.conf import settings
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from django_tenants.utils import get_tenant_model
from .models import CustomUser

class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
        try:
            token = auth_header.split(' ')[1]
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

            tenant_id = payload.get('tenant_id')
            user_id = payload.get('user_id')
            role = payload.get('role')

            if not tenant_id or not user_id:
                raise AuthenticationFailed('Invalid token')

            Tenant = get_tenant_model()
            try:
                tenant = Tenant.objects.get(id=tenant_id)
                request.tenant = tenant
            except Tenant.DoesNotExist:
                raise AuthenticationFailed('Tenant not found')

            try:
                user = CustomUser.objects.get(id=user_id, tenant_id=tenant_id)
                user.role = role
                return (user, None)
            except CustomUser.DoesNotExist:
                raise AuthenticationFailed('User not found')
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except Exception as e:
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')

class TenantAwarePermission:
    def has_permission(self, request, view):
        if not hasattr(request, 'tenant'):
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'tenant'):
            return obj.tenant_id == request.tenant.id
        return True

class IsStoreOwner(TenantAwarePermission):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.role == 'store_owner'

class IsStaffMember(TenantAwarePermission):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.role in ['store_owner', 'staff']

class IsCustomer(TenantAwarePermission):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.role == 'customer'
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from vendors.models import Tenant
import jwt
from django.conf import settings
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/api/auth/'):
            return None
        auth_header = request.headers.get('Authorization', '')
        
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            try:
                untyped_token = UntypedToken(token)
                token_data = untyped_token.payload
                tenant_id = token_data.get('tenant_id')
                
                if tenant_id:
                    try:
                        tenant = Tenant.objects.get(id=tenant_id)
                        request.tenant = tenant
                        request.tenant_id = tenant_id
                        request.user_role = token_data.get('role')
                    except Tenant.DoesNotExist:
                        return JsonResponse(
                            {'error': 'Tenant not found'}, 
                            status=404
                        )
                else:
                    request.tenant = None
                    request.tenant_id = None
                    
            except (InvalidToken, TokenError, jwt.DecodeError):
                return JsonResponse(
                    {'error': 'Invalid token'}, 
                    status=401
                )
        
        return None
    
class NormalizeTrailingSlashMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.strip()
        if path.endswith('/ '): 
            path = path.rstrip(' ')
        
        request.path_info = path
        return self.get_response(request)

from django.utils.deprecation import MiddlewareMixin

class DisableCSRFMiddlewareForAPI(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None

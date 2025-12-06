from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from vendors.models import Tenant, TenantUser


User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'first_name', 'last_name', 'phone')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields don't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class VendorRegistrationSerializer(serializers.ModelSerializer):
    user = UserRegistrationSerializer()
    store_name = serializers.CharField(write_only=True)
    domain = serializers.CharField(write_only=True)
    subdomain = serializers.CharField(write_only=True)
    contact_email = serializers.EmailField(write_only=True)
    contact_phone = serializers.CharField(write_only=True)
    address = serializers.CharField(write_only=True)
    
    class Meta:
        model = Tenant
        fields = ('user', 'store_name', 'domain', 'subdomain', 'contact_email', 'contact_phone', 'address')
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        store_data = {
            'name': validated_data.pop('store_name'),
            'domain': validated_data.pop('domain'),
            'subdomain': validated_data.pop('subdomain'),
            'contact_email': validated_data.pop('contact_email'),
            'contact_phone': validated_data.pop('contact_phone'),
            'address': validated_data.pop('address'),
        }
        
        user_serializer = UserRegistrationSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        user.is_vendor = True
        user.save()
        
        tenant = Tenant.objects.create(owner=user, **store_data)
        
        TenantUser.objects.create(
            user=user,
            tenant=tenant,
            role=TenantUser.Role.STORE_OWNER
        )
        
        return tenant


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        token['email'] = user.email
        token['is_vendor'] = user.is_vendor
        
        if user.is_vendor:
            tenant_users = TenantUser.objects.filter(user=user, is_active=True)
            if tenant_users.exists():
                # For now, use the first tenant (could extend to support multiple tenants per user)
                tenant_user = tenant_users.first()
                token['tenant_id'] = tenant_user.tenant.id
                token['role'] = tenant_user.role
                token['tenant_name'] = tenant_user.tenant.name
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['user'] = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_vendor': user.is_vendor,
        }
        
        if user.is_vendor:
            tenant_users = TenantUser.objects.filter(user=user, is_active=True)
            if tenant_users.exists():
                tenant_user = tenant_users.first()
                data['tenant'] = {
                    'id': tenant_user.tenant.id,
                    'name': tenant_user.tenant.name,
                    'role': tenant_user.role
                }
        
        return data
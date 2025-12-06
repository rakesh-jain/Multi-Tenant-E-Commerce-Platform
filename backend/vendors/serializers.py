from rest_framework import serializers
from .models import Tenant, TenantUser
from users.models import User
from django.contrib.auth import get_user_model

User = get_user_model()

class TenantSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    owner_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'domain', 'subdomain', 'contact_email', 
            'contact_phone', 'address', 'is_active', 'created_at', 
            'updated_at', 'owner', 'owner_email', 'owner_name'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']
    
    def get_owner_name(self, obj):
        return f"{obj.owner.first_name} {obj.owner.last_name}"

class TenantCreateSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(write_only=True)
    owner_password = serializers.CharField(write_only=True, min_length=8)
    owner_first_name = serializers.CharField(write_only=True, required=False, default='')
    owner_last_name = serializers.CharField(write_only=True, required=False, default='')
    
    class Meta:
        model = Tenant
        fields = [
            'name', 'domain', 'subdomain', 'contact_email', 'contact_phone',
            'address', 'owner_email', 'owner_password', 'owner_first_name', 'owner_last_name'
        ]
    
    def validate_domain(self, value):
        if Tenant.objects.filter(domain=value).exists():
            raise serializers.ValidationError("Domain already exists")
        return value
    
    def validate_subdomain(self, value):
        if Tenant.objects.filter(subdomain=value).exists():
            raise serializers.ValidationError("Subdomain already exists")
        return value
    
    def create(self, validated_data):
        owner_email = validated_data.pop('owner_email')
        owner_password = validated_data.pop('owner_password')
        owner_first_name = validated_data.pop('owner_first_name', '')
        owner_last_name = validated_data.pop('owner_last_name', '')
        owner = User.objects.create_user(
            email=owner_email,
            password=owner_password,
            first_name=owner_first_name,
            last_name=owner_last_name,
            is_vendor=True
        )
        
        tenant = Tenant.objects.create(owner=owner, **validated_data)
        TenantUser.objects.create(
            user=owner,
            tenant=tenant,
            role=TenantUser.Role.STORE_OWNER
        )
        
        return tenant

class TenantUserSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField(read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = TenantUser
        fields = [
            'id', 'user', 'user_email', 'user_name', 'tenant', 
            'tenant_name', 'role', 'is_active', 'created_at'
        ]
        read_only_fields = ['user', 'tenant', 'created_at']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

class TenantUserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    
    class Meta:
        model = TenantUser
        fields = ['email', 'role']
    
    def validate(self, attrs):
        email = attrs.get('email')
        tenant = self.context.get('tenant')
        if not tenant:
            raise serializers.ValidationError("Tenant context is required")
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError(f"User with email {email} does not exist")
        
        if TenantUser.objects.filter(user=user, tenant=tenant).exists():
            raise serializers.ValidationError(f"User is already a member of this tenant")
        
        attrs['user'] = user
        return attrs
    
    def create(self, validated_data):
        tenant = self.context.get('tenant')
        user = validated_data.get('user')
        role = validated_data.get('role')
        
        tenant_user = TenantUser.objects.create(
            user=user,
            tenant=tenant,
            role=role
        )
        
        return tenant_user

class TenantStatsSerializer(serializers.Serializer):
    total_products = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    total_customers = serializers.IntegerField()
    total_staff = serializers.IntegerField()
    active_products = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
CustomerProfile,
CustomerAddress,
CustomerWishlist,
CustomerReview,
CustomerNotification
)
from vendors.models import Tenant, TenantUser
from products.models import Product
from products.serializers import ProductSerializer

User = get_user_model()
class CustomerProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_first_name = serializers.CharField(source='user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user.last_name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    class Meta:
        model = CustomerProfile
        fields = [
        'id', 'user', 'user_email', 'user_first_name', 'user_last_name',
        'tenant', 'tenant_name', 'phone', 'address', 'city', 'state',
        'country', 'postal_code', 'date_of_birth', 'profile_picture',
        'preferences', 'loyalty_points', 'total_spent', 'last_purchase_date',
        'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
        'user','tenant', 'loyalty_points', 'total_spent',
        'last_purchase_date', 'created_at', 'updated_at'
        ]

# class UserNestedSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ["email", "first_name", "last_name"]


# class CustomerProfileSerializer(serializers.ModelSerializer):
#     user = UserNestedSerializer(required=False)

#     tenant_name = serializers.CharField(source='tenant.name', read_only=True)

#     class Meta:
#         model = CustomerProfile
#         fields = [
#             "id", "user", "tenant", "tenant_name",
#             "phone", "address", "city", "state", "country",
#             "postal_code", "date_of_birth",
#             "profile_picture", "preferences",
#             "loyalty_points", "total_spent",
#             "last_purchase_date", "is_active",
#             "created_at", "updated_at"
#         ]
#         read_only_fields = [
#             "tenant", "loyalty_points", "total_spent",
#             "last_purchase_date", "created_at", "updated_at"
#         ]

#     def update(self, instance, validated_data):
#         user_data = validated_data.pop("user", None)

#         # update user
#         if user_data:
#             user = instance.user
#             for field, value in user_data.items():
#                 setattr(user, field, value)
#             user.save()

#         return super().update(instance, validated_data)


# class CustomerAddressSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CustomerAddress
#         fields = '__all__'
#         read_only_fields = ['customer', 'created_at', 'updated_at']
        
#     def validate(self, attrs):
#         # Ensure address belongs to the same tenant
#         request = self.context.get('request')
#         if request and hasattr(request, 'tenant'):
#             customer = self.context.get('customer')
#         if customer and customer.tenant != request.tenant:
#             raise serializers.ValidationError("Address must belong to the current tenant")
#         return attrs

class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = '__all__'
        read_only_fields = ['customer', 'created_at', 'updated_at']
    
    # def validate(self, attrs):
    #     # Ensure address belongs to the same tenant
    #     request = self.context.get('request')
    #     if request and hasattr(request, 'tenant'):
    #         customer = self.context.get('customer')
    #         # Check if customer exists and belongs to the same tenant
    #         if customer:
    #             # The customer should already belong to the request.tenant
    #             # This validation is checking that customer's tenant matches request.tenant
    #             if customer.tenant != request.tenant:
    #                 raise serializers.ValidationError("Address must belong to the current tenant")
    #     return attrs

class CustomerWishlistSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    class Meta:
        model = CustomerWishlist
        fields = ['id', 'customer', 'product', 'product_details', 'added_at']
        read_only_fields = ['customer', 'added_at']
        
    # def validate_product(self, value):
    # # Ensure product belongs to the same tenant
    #     request = self.context.get('request')
    #     if request and hasattr(request, 'tenant'):
    #         if value.tenant != request.tenant:
    #             raise serializers.ValidationError("Product must belong to the current tenant")
    #     return value


class CustomerReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField(read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = CustomerReview
        fields = [
            'id', 'customer', 'customer_name', 'product', 'product_name',
            'rating', 'title', 'comment', 'is_verified_purchase',
            'helpful_votes', 'not_helpful_votes', 'is_approved',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'customer', 'is_verified_purchase', 'helpful_votes',
            'not_helpful_votes', 'is_approved', 'created_at', 'updated_at'
        ]
    
    def get_customer_name(self, obj):
        try:
            return f"{obj.customer.user.first_name} {obj.customer.user.last_name}"
        except (AttributeError, TypeError):
         
            customer_data = getattr(obj, 'customer', obj.get('customer', {}))
            user_data = getattr(customer_data, 'user', customer_data.get('user', {}))
            first_name = getattr(user_data, 'first_name', user_data.get('first_name', 'Unknown'))
            last_name = getattr(user_data, 'last_name', user_data.get('last_name', ''))
            return f"{first_name} {last_name}".strip()
    
    def validate(self, attrs):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and 'product' in attrs:
            from orders.models import OrderItem
            product = attrs['product']
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                tenant = TenantUser.objects.filter(user = self.request.user,is_active =True).first().tenant
            product_id = product.id if hasattr(product, 'id') else product
            
            has_purchased = OrderItem.objects.filter(
                order__customer=request.user,
                order__tenant=tenant,
                product_id=product_id
            ).exists()
            
            if has_purchased:
                attrs['is_verified_purchase'] = True
        return attrs

    
    
class CustomerNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerNotification
        fields = '__all__'
        read_only_fields = ['customer', 'created_at']

class CustomerStatsSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    loyalty_points = serializers.IntegerField()
    wishlist_count = serializers.IntegerField()
    reviews_count = serializers.IntegerField()
    average_rating = serializers.FloatField()

# class CustomerCreateSerializer(serializers.ModelSerializer):
#     email = serializers.EmailField(write_only=True)
#     first_name = serializers.CharField(write_only=True, required=False, default='')
#     last_name = serializers.CharField(write_only=True, required=False, default='')
#     phone = serializers.CharField(write_only=True, required=False, default='')
#     class Meta:
#         model = CustomerProfile
#         fields = ['email', 'first_name', 'last_name', 'phone', 'address', 'city', 'state', 'country',
#         'postal_code']
        
#     def create(self, validated_data):
#         # Extract user data
#         email = validated_data.pop('email')
#         first_name = validated_data.pop('first_name', '')
#         last_name = validated_data.pop('last_name', '')
#         phone = validated_data.pop('phone', '')
#         # Get tenant from context
#         tenant = self.context.get('tenant')
#         if not tenant:
#             raise serializers.ValidationError("Tenant context is required")
#         # Check if user exists
#         user, created = User.objects.get_or_create(
#         email=email,
#         defaults={
#         'first_name': first_name,
#         'last_name': last_name,
#         'phone': phone
#         }
#         )
#         if created:
#             # Set a temporary password that user can reset
#             user.set_unusable_password()
#             user.save()
#             # Create or get customer profile
#         customer_profile, created = CustomerProfile.objects.get_or_create(
#         user=user,
#         tenant=tenant,
#         defaults=validated_data
#         )
#         # Create tenant user relationship
#         tenant_user, created = TenantUser.objects.get_or_create(
#         user=user,
#         tenant=tenant,
#         defaults={'role': TenantUser.Role.CUSTOMER}
#         )
#         if not customer_profile.phone and phone:
#             customer_profile.phone = phone
#             customer_profile.save()
#         return customer_profile
class CustomerCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True, required=False, default='')
    last_name = serializers.CharField(write_only=True, required=False, default='')
    phone = serializers.CharField(write_only=True, required=False, default='')
    
    
    class Meta:
        model = CustomerProfile
        fields = ['email', 'first_name', 'last_name', 'phone', 'address', 'city', 'state', 'country', 'postal_code']
    
    def create(self, validated_data):
        # Extract user data
        email = validated_data.pop('email')
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        phone = validated_data.pop('phone', '')
        preferences = validated_data.pop('preferences', {})
        
        # Get request and tenant from context
        request = self.context.get('request')

        if not request:
            raise serializers.ValidationError("Request context is required")
        
        tenant = getattr(request, 'tenant', None)

        if not tenant:
            raise serializers.ValidationError("No tenant found in request")
        
 
        # Check if user exists
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone
            }
        )
        
        if created:
            # Set a temporary password that user can reset
            user.set_unusable_password()
            user.save()
            
        # Create or get customer profile
        customer_profile, profile_created = CustomerProfile.objects.get_or_create(
            user=user,
            tenant=tenant,
            defaults={**validated_data,"preferences":preferences}
        )
       
        # Create tenant user relationship
        tenant_user, tenant_user_created = TenantUser.objects.get_or_create(
            user=user,
            tenant=tenant,
            defaults={'role': TenantUser.Role.CUSTOMER}
        )
        
        # Update phone if provided
        if not customer_profile.phone and phone:
            customer_profile.phone = phone
            customer_profile.save()
            
        if not profile_created:
            customer_profile.preferences = preferences
            customer_profile.save()
        
        return customer_profile
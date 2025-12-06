from rest_framework import generics, permissions, status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Avg, Sum, Q
from django.contrib.auth import get_user_model
from .models import (
CustomerProfile,
CustomerAddress,
CustomerWishlist,
CustomerReview,
CustomerNotification
)
from .serializers import (
CustomerProfileSerializer,
CustomerAddressSerializer,
CustomerWishlistSerializer,
CustomerReviewSerializer,
CustomerNotificationSerializer,
CustomerStatsSerializer,
CustomerCreateSerializer
)
from vendors.models import TenantUser
from products.models import Product
from orders.models import Order
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

User = get_user_model()

class CustomerProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for managing customer profiles"""
    serializer_class = CustomerProfileSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['city', 'state', 'country', 'is_active']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'phone']
    ordering_fields = ['total_spent', 'loyalty_points', 'last_purchase_date', 'created_at']
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        # if not tenant:
        #     print("not customer")
        #     return CustomerProfile.objects.none()
        user_role = getattr(self.request, 'user_role', TenantUser.Role.CUSTOMER)
        
        if user_role in [TenantUser.Role.STORE_OWNER, TenantUser.Role.STAFF]:
            return CustomerProfile.objects.filter(tenant=tenant)
        
        elif user_role == TenantUser.Role.CUSTOMER:
            return CustomerProfile.objects.filter(
            tenant=tenant,
            user=self.request.user
            )
        return CustomerProfile.objects.none()
    
    # def get_permissions(self):
    #     if self.action in ['list', 'retrieve', 'stats']:
    #     # Store owners, staff, and customers (own profile) can view
    #         permission_classes = [permissions.IsAuthenticated]
    #     elif self.action in ['create']:
    #     # Only store owners and staff can create customer profiles
    #         permission_classes = [permissions.IsAuthenticated]
    #     elif self.action in ['update', 'partial_update', 'destroy']:
    #     # Store owners and staff can update, customers can update own
    #         permission_classes = [permissions.IsAuthenticated]
    #     else:
    #         permission_classes = [permissions.IsAuthenticated]
    #         return [permission() for permission in permission_classes]
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'stats', 'orders']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy', 'update_loyalty_points']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CustomerCreateSerializer
        return CustomerProfileSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        context['tenant'] = getattr(self.request,'tenant',None)
        return context
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            raise serializer.ValidationError("No Tenant context found")
        serializer.context['tenant'] = tenant
        serializer.save(tenant=tenant)
        
            
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user_role = getattr(request, 'user_role', None)
        if (user_role == TenantUser.Role.CUSTOMER and
            instance.user != request.user):
            return Response(
            {'error': 'You can only view your own profile'},
            status=status.HTTP_403_FORBIDDEN
            )
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        customer = self.get_object()
        user_role = getattr(request, 'user_role', None)
        if (user_role == TenantUser.Role.CUSTOMER and
        customer.user != request.user):
            return Response(
            {'error': 'You can only view your own statistics'},
            status=status.HTTP_403_FORBIDDEN
            )
        total_orders = Order.objects.filter(
            tenant=request.tenant,
            customer=customer.user
            ).count()
        
        wishlist_count = CustomerWishlist.objects.filter(
            customer=customer
            ).count()
        reviews_count = CustomerReview.objects.filter(
            customer=customer
            ).count()
        avg_rating = CustomerReview.objects.filter(
            customer=customer
            ).aggregate(avg=Avg('rating'))['avg'] or 0
        stats_data = {
            'total_orders': total_orders,
            'total_spent': customer.total_spent,
            'loyalty_points': customer.loyalty_points,
            'wishlist_count': wishlist_count,
            'reviews_count': reviews_count,
            'average_rating': round(avg_rating, 2)
            }
        
        serializer = CustomerStatsSerializer(stats_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def orders(self, request, pk=None):
        """Get customer's orders"""
        customer = self.get_object()
        user_role = getattr(request, 'user_role', None)
        if (user_role == TenantUser.Role.CUSTOMER and
            customer.user != request.user):
            return Response(
            {'error': 'You can only view your own orders'},
            status=status.HTTP_403_FORBIDDEN
        )
        from orders.models import Order
        from orders.serializers import OrderSerializer
        orders = Order.objects.filter(
        tenant=request.tenant,
        customer=customer.user
        ).order_by('-created_at')
        page = self.paginate_queryset(orders)
        if page is not None:
            serializer = OrderSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_loyalty_points(self, request, pk=None):
        """Update customer loyalty points (store owners/staff only)"""
        customer = self.get_object()
        user_role = getattr(request, 'user_role', None)
        if user_role not in [TenantUser.Role.STORE_OWNER, TenantUser.Role.STAFF]:
            return Response(
            {'error': 'Only store owners and staff can update loyalty points'},
            status=status.HTTP_403_FORBIDDEN
            )
            
        points = request.data.get('points')
        action_type = request.data.get('action', 'add')
        
        if points is None:
            return Response(
            {'error': 'points is required'},
            status=status.HTTP_400_BAD_REQUEST
            )
        try:
            points = int(points)
        except ValueError:
            return Response(
            {'error': 'points must be an integer'},
            status=status.HTTP_400_BAD_REQUEST
            )
        if action_type == 'add':
            customer.loyalty_points += points
        elif action_type == 'subtract':
            customer.loyalty_points = max(0, customer.loyalty_points - points)
        else:
            return Response(
            {'error': 'action must be either "add" or "subtract"'},
            status=status.HTTP_400_BAD_REQUEST
            )
        customer.save()
        return Response({
        'message': f'Loyalty points updated successfully',
        'loyalty_points': customer.loyalty_points
        })
    
class CustomerAddressViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerAddressSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['address_type', 'is_default']
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            tenant_users = TenantUser.objects.filter(
                user=self.request.user,
                is_active=True
            ).select_related('tenant')
            
            if tenant_users.exists():
                tenant = tenant_users.first().tenant
                self.request.tenant = tenant
            else:
                return CustomerAddress.objects.none()
        
        try:
            customer_profile = CustomerProfile.objects.get(
                user=self.request.user,
                tenant=tenant
            )
            return CustomerAddress.objects.filter(customer=customer_profile)
        except CustomerProfile.DoesNotExist:
            customer_profile, created = CustomerProfile.objects.get_or_create(
                user=self.request.user,
                tenant=tenant,
                defaults={'phone': '', 'address': ''}
            )
            return CustomerAddress.objects.filter(customer=customer_profile)
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        
        if not tenant:
           
            tenant_users = TenantUser.objects.filter(
                user=self.request.user,
                is_active=True
            ).select_related('tenant')
            
            if tenant_users.exists():
                tenant = tenant_users.first().tenant
               
            else:
                # Alternative 2: Get from customer's last order
                from orders.models import Order
                last_order = Order.objects.filter(
                    customer=self.request.user
                ).select_related('tenant').first()
                
                if last_order:
                    tenant = last_order.tenant
                    
                else:
                    # Alternative 3: Get first tenant (fallback)
                    from vendors.models import Tenant
                    tenant = Tenant.objects.first()
                    if not tenant:
                        raise serializer.ValidationError("No tenant available")
        
        try:
            # Get or create customer profile
            customer_profile, created = CustomerProfile.objects.get_or_create(
                user=self.request.user,
                tenant=tenant,
                defaults={'phone': '', 'address': ''}
            )
    
            # Check if address already exists
            address_type = serializer.validated_data.get('address_type')
            is_default = serializer.validated_data.get('is_default', False)
            
            # If setting as default, unset other defaults of same type
            if is_default:
                CustomerAddress.objects.filter(
                    customer=customer_profile,
                    address_type=address_type,
                    is_default=True
                ).update(is_default=False)
            
            serializer.save(customer=customer_profile)
          
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            tenant_users = TenantUser.objects.filter(
                user=self.request.user,
                is_active=True
            ).select_related('tenant')
            
            if tenant_users.exists():
                tenant = tenant_users.first().tenant
                
        
        if tenant:
            customer_profile, created = CustomerProfile.objects.get_or_create(
                user=self.request.user,
                tenant=tenant,
                defaults={'phone': '', 'address': ''}
            )
            context['customer'] = customer_profile
               
        return context
    
class CustomerWishlistViewSet(viewsets.ModelViewSet):
    """ViewSet for managing customer wishlist"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerWishlistSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            tenant = TenantUser.objects.filter(user = self.request.user,is_active =True).first().tenant
        try:
            customer_profile = CustomerProfile.objects.get(
            user=self.request.user,
            tenant=tenant
            )
        except CustomerProfile.DoesNotExist:
            return CustomerWishlist.objects.none()
        return CustomerWishlist.objects.filter(customer=customer_profile)
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
             tenant = TenantUser.objects.filter(user = self.request.user,is_active =True).first().tenant
        
        try:
            customer_profile = CustomerProfile.objects.get(
            user=self.request.user,
            tenant=tenant
            )
            # Check if product is already in wishlist
            product = serializer.validated_data.get('product')
            if CustomerWishlist.objects.filter(
            customer=customer_profile,
            product=product
            ).exists():
                raise serializer.ValidationError("Product already in wishlist")
            serializer.save(customer=customer_profile)
        except CustomerProfile.DoesNotExist:
            raise serializer.ValidationError("Customer profile not found")
            
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)



class CustomerReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for managing customer reviews"""
    serializer_class = CustomerReviewSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['rating', 'is_verified_purchase', 'is_approved']
    ordering_fields = ['rating', 'created_at', 'helpful_votes']
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            tenant = TenantUser.objects.filter(user = self.request.user,is_active =True).first().tenant
        user_role = getattr(self.request, 'user_role', None)
        
        if not user_role:
            user_role = TenantUser.objects.filter(user = self.request.user,is_active =True).first().tenant
    
        queryset = CustomerReview.objects.filter(
        customer__tenant=tenant,
        product__tenant=tenant
        )
        if user_role == TenantUser.Role.CUSTOMER:
            queryset = queryset.filter(
            Q(is_approved=True) |
            Q(customer__user=self.request.user)
            )
        elif user_role in [TenantUser.Role.STORE_OWNER, TenantUser.Role.STAFF]:
            pass
        else:
            queryset = queryset.filter(is_approved=True)
        return queryset
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            tenant = TenantUser.objects.filter(user = self.request.user,is_active =True).first().tenant
        try:
            customer_profile = CustomerProfile.objects.get(
            user=self.request.user,
            tenant=tenant
            )
            product = serializer.validated_data.get('product')
            if CustomerReview.objects.filter(
            customer=customer_profile,
            product=product
            ).exists():
                
                raise serializer.ValidationError("You have already reviewed this product")
            serializer.save(customer=customer_profile)
        except CustomerProfile.DoesNotExist:
            raise serializer.ValidationError("Customer profile not found")
    
    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        review = self.get_object()
        vote_type = request.data.get('type') 
        if vote_type == 'helpful':
            review.helpful_votes += 1
        elif vote_type == 'not_helpful':
            review.not_helpful_votes += 1
        else:
            return Response(
            {'error': 'type must be either "helpful" or "not_helpful"'},
            status=status.HTTP_400_BAD_REQUEST
            )
        review.save()
        return Response({
        'message': 'Vote recorded successfully',
        'helpful_votes': review.helpful_votes,
        'not_helpful_votes': review.not_helpful_votes
        })
        
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        review = self.get_object()
        # Check if user is store owner or staff
        user_role = getattr(request, 'user_role', None)
        if user_role not in [TenantUser.Role.STORE_OWNER, TenantUser.Role.STAFF]:
                return Response(
            {'error': 'Only store owners and staff can approve reviews'},
            status=status.HTTP_403_FORBIDDEN
            )
        review.is_approved = True
        review.save()
        return Response({
        'message': 'Review approved successfully',
        'review': CustomerReviewSerializer(review).data
        })

class CustomerNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomerNotificationSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['notification_type', 'is_read']
    ordering_fields = ['created_at']
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return CustomerNotification.objects.none()
        try:
            customer_profile = CustomerProfile.objects.get(
            user=self.request.user,
            tenant=tenant
            )
        except CustomerProfile.DoesNotExist:
            return CustomerNotification.objects.none()
        
        return CustomerNotification.objects.filter(customer=customer_profile)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
        {'error': 'No tenant context'},
        status=status.HTTP_400_BAD_REQUEST
        )
        try:
            customer_profile = CustomerProfile.objects.get(
            user=request.user,
            tenant=tenant
            )
            updated = CustomerNotification.objects.filter(
            customer=customer_profile,
            is_read=False
            ).update(is_read=True)
            return Response({
            'message': f'{updated} notifications marked as read'
            })
        except CustomerProfile.DoesNotExist:
            return Response(
            {'error': 'Customer profile not found'},
            status=status.HTTP_404_NOT_FOUND
            )
            
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if notification.is_read:
            return Response({'message': 'Notification already marked as read'})
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'})

class CustomerDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        print(f"{request.user},{request.tenant}")
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant context'},status=status.HTTP_400_BAD_REQUEST)
        try:
            customer_profile = CustomerProfile.objects.get(
            user=request.user,
            tenant=tenant
            )
        except CustomerProfile.DoesNotExist:
            return Response(
            {'error': 'Customer profile not found'},
            status=status.HTTP_404_NOT_FOUND
            )
        from orders.models import Order
        recent_orders = Order.objects.filter(tenant=tenant,customer=request.user).order_by('-created_at')[:5]
        
        from orders.serializers import OrderSerializer

        unread_notifications = CustomerNotification.objects.filter(
        customer=customer_profile,
        is_read=False
        ).count()
        
       
        wishlist_count = CustomerWishlist.objects.filter(
            customer=customer_profile
            ).count()
        
      
        recent_reviews = CustomerReview.objects.filter(
            customer=customer_profile
            ).order_by('-created_at')[:5]
        
        from .serializers import CustomerReviewSerializer
        dashboard_data = {
            'customer': CustomerProfileSerializer(customer_profile).data,
            'stats': {
            'total_orders': Order.objects.filter(
            tenant=tenant,
            
        customer=request.user
            ).count(),
            'total_spent': customer_profile.total_spent,
            'loyalty_points': customer_profile.loyalty_points,
            'wishlist_count': wishlist_count,
            'unread_notifications': unread_notifications
            },
            'recent_orders': OrderSerializer(recent_orders, many=True).data,
            'recent_reviews': CustomerReviewSerializer(recent_reviews, many=True).data
            }
        return Response(dashboard_data)

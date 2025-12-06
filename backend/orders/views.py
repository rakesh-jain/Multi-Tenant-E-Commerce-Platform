from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Sum, F
import uuid

from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderCreateSerializer, OrderItemSerializer
from products.models import Product
from vendors.models import TenantUser

class OrderViewSet(ModelViewSet):
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['order_number', 'customer__email']
    ordering_fields = ['created_at', 'total_amount', 'status']
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        data = TenantUser.objects.filter(user = self.request.user,is_active =True).first()
        
        if not tenant:
            tenant = data.tenant 
        
        user = self.request.user
        user_role = getattr(self.request, 'user_role', None)
        if not user_role:
            user_role=data.role
        
        queryset = Order.objects.filter(tenant=tenant)
        
        if user_role == TenantUser.Role.CUSTOMER:
            queryset = queryset.filter(customer=user)
        elif user_role == TenantUser.Role.STAFF:
            queryset = queryset.filter(staff=user)
      
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            tenant = TenantUser.objects.filter(user = self.request.user,is_active =True).first().tenant
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
       
        items_data = serializer.validated_data['items']
        products_to_update = []
        
        for item_data in items_data:
            product_id = item_data['product'].id
            quantity = item_data['quantity']
            
            try:
                product = Product.objects.get(
                    id=product_id,
                    tenant=tenant,
                    is_active=True
                )
                
                if product.stock_quantity < quantity:
                    return Response(
                        {'error': f'Insufficient stock for {product.name}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                product.stock_quantity -= quantity
                products_to_update.append(product)
                
            except Product.DoesNotExist:
                return Response(
                    {'error': f'Product {product_id} not found or not available in tenant'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        order = Order.objects.create(
            tenant=tenant,
            order_number=order_number,
            customer=request.user,
            shipping_address=serializer.validated_data['shipping_address'],
            billing_address=serializer.validated_data['billing_address'],
            notes=serializer.validated_data.get('notes', '')
        )
     
        total_amount = 0
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            unit_price = product.price
            
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=quantity * unit_price
            )
            
            total_amount += quantity * unit_price

        order.total_amount = total_amount
        order.save()
        
        for product in products_to_update:
            product.save()
        
        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')
        
        if not new_status:
            return Response(
                {'error': 'Status is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        user_role = getattr(request, 'user_role', None)
        
        if user_role == TenantUser.Role.CUSTOMER:
            if new_status != Order.Status.CANCELLED:
                return Response(
                    {'error': 'Customers can only cancel orders'},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif user_role == TenantUser.Role.STAFF:
            if new_status in [Order.Status.REFUNDED]:
                return Response(
                    {'error': 'Staff cannot issue refunds'},
                    status=status.HTTP_403_FORBIDDEN
                )

        order.status = new_status
        order.save()
        
        return Response(OrderSerializer(order).data)
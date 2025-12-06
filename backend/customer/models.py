from django.db import models
from django.contrib.auth import get_user_model
from vendors.models import Tenant
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()
class CustomerProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='customer_profiles')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE,related_name='customer_profiles')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.URLField(blank=True)
    preferences = models.JSONField(default=dict, blank=True) 
    loyalty_points = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_purchase_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'tenant')
        indexes = [
        models.Index(fields=['tenant', 'user']),
        models.Index(fields=['tenant', 'is_active']),
        models.Index(fields=['tenant', 'loyalty_points']),
        ]
    def __str__(self):
        return f"{self.user.email} - {self.tenant.name}"
    
    def update_spending(self, amount):
        """Update customer's total spent and last purchase date"""
        self.total_spent += amount
        self.last_purchase_date = models.DateTimeField(auto_now=True)
        self.save()
        
class CustomerAddress(models.Model):
    ADDRESS_TYPES = [
    ('shipping', 'Shipping Address'),
    ('billing', 'Billing Address'),
    ('both', 'Both Shipping and Billing'),
    ]
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE,
    related_name='addresses')
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPES,
    default='shipping')
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('customer', 'address_type', 'is_default')
        indexes = [
        models.Index(fields=['customer', 'is_default']),
        models.Index(fields=['customer', 'address_type']),
        ]
    def __str__(self):
        return f"{self.full_name} - {self.get_address_type_display()} - {self.city}"
    def save(self, *args, **kwargs):
        if self.is_default:
            CustomerAddress.objects.filter(
            customer=self.customer,
            address_type=self.address_type,
            is_default=True
            ).update(is_default=False)
            super().save(*args, **kwargs)
        
class CustomerWishlist(models.Model):
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE,
    related_name='wishlist_items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE,
    related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('customer', 'product')
        indexes = [
    models.Index(fields=['customer', 'added_at']),
    ]
    def __str__(self):
        return f"{self.customer.user.email} - {self.product.name}"
    
class CustomerReview(models.Model):
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE,
    related_name='reviews')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE,
    related_name='reviews')
    rating = models.IntegerField(
    validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    helpful_votes = models.IntegerField(default=0)
    not_helpful_votes = models.IntegerField(default=0)
    is_approved = models.BooleanField(default=False) # For store owner approval
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('customer', 'product')
        indexes = [
        models.Index(fields=['product', 'rating']),
        models.Index(fields=['product', 'is_approved']),
        models.Index(fields=['customer', 'created_at']),
        ]
    def __str__(self):
        return f"{self.customer.user.email} - {self.product.name} - {self.rating} stars"
    
class CustomerNotification(models.Model):
    NOTIFICATION_TYPES = [
    ('order', 'Order Update'),
    ('product', 'Product Update'),
    ('promotion', 'Promotion'),
    ('system', 'System Notification'),
    ]
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE,
    related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True) # Additional data
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [
        models.Index(fields=['customer', 'is_read']),
        models.Index(fields=['customer', 'created_at']),
        ]
    def __str__(self):
        return f"{self.customer.user.email} - {self.title}"
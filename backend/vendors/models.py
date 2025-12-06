from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class Tenant(models.Model):
    name = models.CharField(max_length=255, unique=True)
    domain = models.CharField(max_length=255, unique=True)
    subdomain = models.CharField(max_length=255, unique=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    address = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='owned_tenants'
    )
    
    def __str__(self):
        return self.name


class TenantUser(models.Model):
    class Role(models.TextChoices):
        STORE_OWNER = 'store_owner', 'Store Owner'
        STAFF = 'staff', 'Staff'
        CUSTOMER = 'customer', 'Customer'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'tenant')
    
    def __str__(self):
        return f"{self.user.email} - {self.tenant.name} ({self.role})"
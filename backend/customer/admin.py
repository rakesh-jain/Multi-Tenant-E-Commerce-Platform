from django.contrib import admin
from .models import (
CustomerProfile,
CustomerAddress,
CustomerWishlist,
CustomerReview,
CustomerNotification
)
@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tenant', 'phone', 'city', 'total_spent', 'loyalty_points', 'is_active')
    list_filter = ('tenant', 'city', 'state', 'country', 'is_active')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'phone')
    readonly_fields = ('total_spent', 'last_purchase_date', 'created_at', 'updated_at')
    fieldsets = (
    ('Basic Information', {'fields': ('user', 'tenant')}),
    ('Contact Information', {
    'fields': ('phone', 'address', 'city', 'state', 'country', 'postal_code')
    }),
    ('Additional Information', {
    'fields': ('date_of_birth', 'profile_picture', 'preferences')
    }),
    ('Statistics', {
    'fields': ('loyalty_points', 'total_spent', 'last_purchase_date')
    }),
    ('Status', {
    'fields': ('is_active',)
    }),
    ('Timestamps', {
    'fields': ('created_at', 'updated_at'),
    'classes': ('collapse',)
    }),
    )
    
@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ('customer', 'address_type', 'full_name', 'city', 'state', 'is_default')
    list_filter = ('address_type', 'city', 'state', 'country', 'is_default')
    search_fields = ('customer__user__email', 'full_name', 'city', 'state')
    readonly_fields = ('created_at', 'updated_at')
    
@admin.register(CustomerWishlist)
class CustomerWishlistAdmin(admin.ModelAdmin):
    list_display = ('customer', 'product', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('customer__user__email', 'product__name')
    readonly_fields = ('added_at',)

@admin.register(CustomerReview)
class CustomerReviewAdmin(admin.ModelAdmin):
    list_display = ('customer', 'product', 'rating', 'title', 'is_verified_purchase', 'is_approved')
    list_filter = ('rating', 'is_verified_purchase', 'is_approved', 'created_at')
    search_fields = ('customer__user__email', 'product__name', 'title')
    readonly_fields = ('helpful_votes', 'not_helpful_votes', 'created_at', 'updated_at')
    fieldsets = (
    ('Review Details', {
    'fields': ('customer', 'product', 'rating', 'title', 'comment')
    }),
    ('Verification', {
    'fields': ('is_verified_purchase', 'is_approved')
    }),
    ('Votes', {
    'fields': ('helpful_votes', 'not_helpful_votes')
    }),
    ('Timestamps', {
    'fields': ('created_at', 'updated_at'),
    'classes': ('collapse',)
    }),
    )
    
@admin.register(CustomerNotification)
class CustomerNotificationAdmin(admin.ModelAdmin):
    list_display = ('customer', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('customer__user__email', 'title', 'message')
    readonly_fields = ('created_at',)
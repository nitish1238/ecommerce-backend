from django.contrib import admin
from django.utils.html import format_html
from .models import *

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ['name']}
    raw_id_fields = ['parent']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'discounted_price', 'stock', 'is_active', 'is_featured']
    list_filter = ['is_active', 'is_featured', 'category', 'brand']
    search_fields = ['name', 'description', 'sku']
    prepopulated_fields = {'slug': ['name']}
    list_editable = ['price', 'stock', 'is_active', 'is_featured']
    readonly_fields = ['average_rating', 'total_reviews', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'slug', 'description', 'short_description')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'discounted_price', 'stock', 'sku')
        }),
        ('Media', {
            'fields': ('image', 'additional_images')
        }),
        ('Product Details', {
            'fields': ('brand', 'weight', 'dimensions', 'materials')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Statistics', {
            'fields': ('average_rating', 'total_reviews')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_approved', 'is_verified_purchase', 'created_at']
    list_filter = ['rating', 'is_approved', 'is_verified_purchase', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']
    list_editable = ['is_approved']
    readonly_fields = ['created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Update product average rating
        reviews = ProductReview.objects.filter(product=obj.product, is_approved=True)
        if reviews.exists():
            avg_rating = reviews.aggregate(avg=models.Avg('rating'))['avg']
            obj.product.average_rating = round(avg_rating, 1)
            obj.product.total_reviews = reviews.count()
            obj.product.save()

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'address_type', 'city', 'country', 'is_default']
    list_filter = ['address_type', 'country', 'is_default']
    search_fields = ['user__username', 'full_name', 'address_line1', 'city']
    raw_id_fields = ['user']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_id', 'total_items', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'session_id']
    raw_id_fields = ['user']
    
    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Total Items'

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'total_price']
    list_filter = ['created_at']
    search_fields = ['product__name']
    raw_id_fields = ['cart', 'product']

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'product__name']
    raw_id_fields = ['user', 'product']

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'type', 'value', 'minimum_order', 'usage_limit', 'used_count', 'is_active']
    list_filter = ['type', 'is_active', 'valid_from', 'valid_to']
    search_fields = ['code']
    filter_horizontal = ['applicable_products', 'applicable_categories', 'exclude_products']
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'type', 'value', 'minimum_order', 'maximum_discount')
        }),
        ('Usage Limits', {
            'fields': ('usage_limit', 'used_count', 'per_user_limit')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Applicability', {
            'fields': ('applicable_products', 'applicable_categories', 'exclude_products')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'total', 'status', 'payment_status', 'created_at']
    list_filter = ['status', 'payment_status', 'created_at']
    search_fields = ['order_number', 'user__username', 'user__email']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    raw_id_fields = ['user', 'coupon']
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'payment_status')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'shipping_cost', 'tax_amount', 'discount_amount', 'total')
        }),
        ('Addresses', {
            'fields': ('shipping_addresses', 'billing_address')
        }),
        ('Payment', {
            'fields': ('coupon', 'payment_intent_id', 'payment_method')
        }),
        ('Shipping', {
            'fields': ('tracking_number', 'estimated_delivery', 'delivered_at')
        }),
        ('Notes', {
            'fields': ('customer_notes', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price', 'total']
    list_filter = ['order__status']
    search_fields = ['order__order_number', 'product__name']
    raw_id_fields = ['order', 'product']

@admin.register(OrderShipment)
class OrderShipmentAdmin(admin.ModelAdmin):
    list_display = ['order', 'status', 'tracking_number', 'carrier', 'shipped_at', 'delivered_at']
    list_filter = ['status', 'carrier']
    search_fields = ['order__order_number', 'tracking_number']
    raw_id_fields = ['order']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['order', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['payment_method', 'status', 'created_at']
    search_fields = ['order__order_number', 'payment_intent_id']
    raw_id_fields = ['order', 'user']
    readonly_fields = ['metadata']

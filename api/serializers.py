from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from .models import *
import stripe
import random
import string
from .models import UserProfile
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY
# Add these to your existing serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
import random
import string
from .models import UserProfile

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 'last_name', 'phone']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True}
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "User with this email already exists."})
        
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "Username already exists."})
        
        return data

    def create(self, validated_data):
        # Remove password2 and phone from validated_data
        validated_data.pop('password2')
        phone = validated_data.pop('phone', '')
        
        # Create user
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        
        # Update profile with phone
        user.profile.phone = phone
        user.profile.save()
        
        # Generate email verification token
        verification_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        user.profile.email_verification_token = verification_token
        user.profile.save()
        
        # Send verification email (implement this function)
        # send_verification_email(user.email, verification_token)
        
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    def validate(self, data):
        username = data.get('username', '')
        email = data.get('email', '')
        password = data.get('password', '')

        if not username and not email:
            raise serializers.ValidationError("Either username or email is required.")
        
        if not password:
            raise serializers.ValidationError("Password is required.")

        # Try to authenticate with username
        user = None
        if username:
            user = authenticate(username=username, password=password)
        
        # If username fails, try with email
        if not user and email:
            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")

        data['user'] = user
        return data

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    
    class Meta:
        model = UserProfile
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 
                 'profile_picture', 'date_of_birth', 'email_verified', 
                 'created_at', 'updated_at']
        read_only_fields = ['email_verified', 'created_at', 'updated_at']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        
        # Update user fields
        if user_data:
            user = instance.user
            if 'first_name' in user_data:
                user.first_name = user_data['first_name']
            if 'last_name' in user_data:
                user.last_name = user_data['last_name']
            user.save()
        
        # Update profile fields
        return super().update(instance, validated_data)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(required=True, style={'input_type': 'password'})

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this email address.")
        return value

class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(required=True, style={'input_type': 'password'})

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']

class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = '__all__'
    
    def get_children(self, obj):
        if obj.children.exists():
            return CategorySerializer(obj.children.all(), many=True).data
        return []

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    current_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = '__all__'
    
    def get_current_price(self, obj):
        return obj.get_price()

class ProductReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = ProductReview
        fields = '__all__'
        read_only_fields = ['user', 'is_verified_purchase', 'is_approved']
    
    def validate(self, data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            # Check if user has purchased the product
            has_purchased = OrderItem.objects.filter(
                order__user=request.user,
                product=data['product'],
                order__status='delivered'
            ).exists()
            data['is_verified_purchase'] = has_purchased
        return data

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'
        read_only_fields = ['user']
    
    def validate(self, data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            data['user'] = request.user
        return data

class CartItemSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_details', 'quantity', 'total', 'created_at']
        read_only_fields = ['cart']
    
    def get_total(self, obj):
        return obj.total_price

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'user', 'session_id', 'items', 'total', 'item_count', 'created_at', 'updated_at']
    
    def get_total(self, obj):
        return obj.subtotal
    
    def get_item_count(self, obj):
        return obj.total_items

class WishlistSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    
    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'product_details', 'added_at']
        read_only_fields = ['user']
    
    def validate(self, data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            data['user'] = request.user
        return data

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'

class CouponValidateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    cart_subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'total']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_details = UserSerializer(source='user', read_only=True)
    coupon_code = serializers.CharField(source='coupon.code', read_only=True)
    
    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['order_number', 'user']

class OrderCreateSerializer(serializers.Serializer):
    shipping_addresses = serializers.ListField(child=serializers.DictField(), min_length=1)
    billing_address = serializers.DictField()
    coupon_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(choices=['stripe', 'cod'])
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        request = self.context.get('request')
        cart = Cart.objects.filter(user=request.user).first()
        
        if not cart or not cart.items.exists():
            raise serializers.ValidationError("Cart is empty")
        
        # Validate stock
        for item in cart.items.all():
            if item.quantity > item.product.stock:
                raise serializers.ValidationError(
                    f"Insufficient stock for {item.product.name}. Available: {item.product.stock}"
                )
        
        data['cart'] = cart
        return data

class PaymentIntentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    payment_method_id = serializers.CharField(required=False)
    
    def create_payment_intent(self, order):
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(order.total * 100),  # Convert to cents
                currency='usd',
                metadata={
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'user_id': order.user.id
                }
            )
            return intent
        except stripe.error.StripeError as e:
            raise serializers.ValidationError(str(e))

class OrderShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderShipment
        fields = '__all__'

# Admin Dashboard Serializers
class AdminDashboardStatsSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_customers = serializers.IntegerField()
    total_products = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    low_stock_products = serializers.IntegerField()
    recent_orders = OrderSerializer(many=True)
    top_products = serializers.ListField()

class AdminOrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status', 'payment_status', 'tracking_number', 'estimated_delivery', 'admin_notes']
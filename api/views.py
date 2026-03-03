from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from django.shortcuts import get_object_or_404
from datetime import timedelta
import random
import string
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal
import json
import stripe

from .models import *
from .serializers import *

stripe.api_key = settings.STRIPE_SECRET_KEY

# ==================== AUTHENTICATION VIEWS ====================

class RegisterView(APIView):
    """
    Register a new user
    
    * Required fields: username, email, password, password2, first_name, last_name
    * Optional field: phone
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    serializer_class = UserRegistrationSerializer
    
    def get(self, request):
        """Return serializer metadata for form generation"""
        serializer = self.serializer_class()
        return Response(serializer.data)
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            try:
                user = serializer.save()
                return Response({
                    'success': True,
                    'message': 'Registration successful',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name
                    }
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'success': False,
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    Login user
    POST: Authenticate user
    GET: Show login form (for browsable API)
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    serializer_class = UserLoginSerializer
    
    def get(self, request):
        """Handle GET requests - return empty form for browsable API"""
        serializer = self.serializer_class()
        return Response({
            'message': 'Please send a POST request with username/email and password',
            'fields': serializer.data
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            
            # Get or create cart for user
            cart, created = Cart.objects.get_or_create(user=user)
            
            return Response({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff
                },
                'cart_id': cart.id,
                'cart_items_count': cart.total_items
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        logout(request)
        return Response({
            'success': True,
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    """
    Get currently logged in user details
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff
            }
        })


class UserListView(generics.ListAPIView):
    """
    List all users (admin only)
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'username']


class UserDetailView(APIView):
    """
    Get details of a specific user (admin only)
    """
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            serializer = UserSerializer(user)
            return Response({
                'success': True,
                'user': serializer.data
            })
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    
    def put(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'data': serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            
            # Check old password
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({
                    'success': False,
                    'message': 'Old password is incorrect'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({
                'success': True,
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            
            # Generate reset token
            reset_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
            user.profile.reset_password_token = reset_token
            user.profile.reset_password_expires = timezone.now() + timedelta(hours=24)
            user.profile.save()
            
            # Send reset email
            reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
            
            # Uncomment to actually send email
            # send_password_reset_email(email, reset_link)
            
            return Response({
                'success': True,
                'message': 'Password reset link has been sent to your email'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            
            try:
                profile = UserProfile.objects.get(
                    reset_password_token=token,
                    reset_password_expires__gt=timezone.now()
                )
                
                # Update password
                user = profile.user
                user.set_password(new_password)
                user.save()
                
                # Clear reset token
                profile.reset_password_token = ''
                profile.reset_password_expires = None
                profile.save()
                
                return Response({
                    'success': True,
                    'message': 'Password reset successful'
                }, status=status.HTTP_200_OK)
                
            except UserProfile.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Invalid or expired reset token'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, token):
        try:
            profile = UserProfile.objects.get(email_verification_token=token)
            profile.email_verified = True
            profile.email_verification_token = ''
            profile.save()
            
            return Response({
                'success': True,
                'message': 'Email verified successfully'
            }, status=status.HTTP_200_OK)
            
        except UserProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Invalid verification token'
            }, status=status.HTTP_400_BAD_REQUEST)


class CheckAuthStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        return Response({
            'is_authenticated': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'is_staff': request.user.is_staff
            }
        })


class SocialAuthView(APIView):
    """
    Handle social authentication (Google, Facebook, etc.)
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        provider = request.data.get('provider')
        token = request.data.get('token')
        email = request.data.get('email')
        name = request.data.get('name', '').split()
        
        if not provider or not token:
            return Response({
                'success': False,
                'message': 'Provider and token are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Here you would verify the token with the provider
        # This is a simplified example
        
        # Find or create user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Create new user
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=User.objects.make_random_password(),
                first_name=name[0] if name else '',
                last_name=' '.join(name[1:]) if len(name) > 1 else ''
            )
            user.profile.email_verified = True
            user.profile.save()
        
        # Log the user in
        login(request, user)
        
        return Response({
            'success': True,
            'message': f'Logged in with {provider}',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        })


# ==================== CATEGORY VIEWS ====================

class CategoryList(generics.ListCreateAPIView):
    queryset = Category.objects.filter(parent=None)
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']


class CategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# ==================== PRODUCT VIEWS ====================

class ProductList(generics.ListCreateAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'brand']
    ordering_fields = ['price', 'created_at', 'average_rating']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        in_stock = self.request.query_params.get('in_stock')
        featured = self.request.query_params.get('featured')
        
        if category:
            queryset = queryset.filter(category__slug=category)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if in_stock:
            queryset = queryset.filter(stock__gt=0)
        if featured:
            queryset = queryset.filter(is_featured=True)
        
        return queryset


class ProductDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# ==================== PRODUCT REVIEW VIEWS ====================

class ProductReviewList(generics.ListCreateAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        product_id = self.kwargs['product_id']
        return ProductReview.objects.filter(product_id=product_id, is_approved=True)
    
    def perform_create(self, serializer):
        product = get_object_or_404(Product, id=self.kwargs['product_id'])
        serializer.save(user=self.request.user, product=product)


class ProductReviewDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductReview.objects.all()
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ProductReview.objects.filter(user=self.request.user)


# ==================== CART VIEWS ====================

class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    def post(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        product = get_object_or_404(Product, id=product_id)
        
        if product.stock < quantity:
            return Response(
                {'error': 'Insufficient stock'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    def put(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        item_id = request.data.get('item_id')
        quantity = int(request.data.get('quantity'))
        
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        if quantity > cart_item.product.stock:
            return Response(
                {'error': 'Insufficient stock'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if quantity <= 0:
            cart_item.delete()
        else:
            cart_item.quantity = quantity
            cart_item.save()
        
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    def delete(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        item_id = request.query_params.get('item_id')
        
        if item_id:
            CartItem.objects.filter(id=item_id, cart=cart).delete()
        else:
            cart.items.all().delete()
        
        serializer = CartSerializer(cart)
        return Response(serializer.data)


# ==================== WISHLIST VIEWS ====================

class WishlistView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        wishlist = Wishlist.objects.filter(user=request.user)
        serializer = WishlistSerializer(wishlist, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        product_id = request.data.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        if not created:
            return Response(
                {'message': 'Product already in wishlist'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = WishlistSerializer(wishlist_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def delete(self, request):
        product_id = request.query_params.get('product_id')
        Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================== ADDRESS VIEWS ====================

class AddressList(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AddressDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


# ==================== COUPON VIEWS ====================

class CouponValidateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = CouponValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            coupon = Coupon.objects.get(
                code=serializer.validated_data['code'],
                is_active=True
            )
            
            is_valid, message = coupon.is_valid(
                user=request.user,
                cart_subtotal=serializer.validated_data['cart_subtotal']
            )
            
            if is_valid:
                discount = coupon.calculate_discount(
                    serializer.validated_data['cart_subtotal']
                )
                return Response({
                    'valid': True,
                    'discount': discount,
                    'type': coupon.type,
                    'value': coupon.value
                })
            else:
                return Response({
                    'valid': False,
                    'message': message
                })
                
        except Coupon.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'Invalid coupon code'
            })


# ==================== ORDER VIEWS ====================

class OrderList(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderDetail(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class CreateOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = OrderCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        cart = serializer.validated_data['cart']
        coupon_code = serializer.validated_data.get('coupon_code')
        coupon = None
        discount_amount = 0
        
        # Calculate totals
        subtotal = cart.subtotal
        shipping_cost = Decimal('10.00')  # Example shipping cost
        tax_amount = subtotal * Decimal('0.1')  # Example 10% tax
        
        # Apply coupon if provided
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                is_valid, message = coupon.is_valid(
                    user=request.user,
                    cart_subtotal=subtotal
                )
                if is_valid:
                    discount_amount = coupon.calculate_discount(subtotal)
                else:
                    return Response(
                        {'error': message},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Coupon.DoesNotExist:
                return Response(
                    {'error': 'Invalid coupon code'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        total = subtotal + shipping_cost + tax_amount - discount_amount
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total=total,
            shipping_addresses=serializer.validated_data['shipping_addresses'],
            billing_address=serializer.validated_data['billing_address'],
            coupon=coupon,
            customer_notes=serializer.validated_data.get('customer_notes', ''),
            payment_method=serializer.validated_data['payment_method']
        )
        
        # Create order items and reduce stock
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.get_price(),
                total=cart_item.total_price
            )
            cart_item.product.reduce_stock(cart_item.quantity)
        
        # Record coupon usage
        if coupon:
            CouponUsage.objects.create(
                coupon=coupon,
                user=request.user,
                order=order
            )
            coupon.used_count += 1
            coupon.save()
        
        # Create shipments for different addresses
        for idx, address in enumerate(serializer.validated_data['shipping_addresses']):
            items_for_address = []  # You can implement logic to split items per address
            OrderShipment.objects.create(
                order=order,
                address_index=idx,
                items=items_for_address
            )
        
        # Clear cart
        cart.items.all().delete()
        
        # Create payment intent for Stripe
        if serializer.validated_data['payment_method'] == 'stripe':
            try:
                intent = stripe.PaymentIntent.create(
                    amount=int(total * 100),
                    currency='usd',
                    metadata={
                        'order_id': order.id,
                        'order_number': order.order_number
                    }
                )
                order.payment_intent_id = intent.id
                order.save()
                
                return Response({
                    'order': OrderSerializer(order).data,
                    'client_secret': intent.client_secret,
                    'requires_payment': True
                })
            except stripe.error.StripeError as e:
                order.status = 'cancelled'
                order.save()
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response({
            'order': OrderSerializer(order).data,
            'requires_payment': False
        }, status=status.HTTP_201_CREATED)


# ==================== PAYMENT VIEWS ====================

class CreatePaymentIntent(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PaymentIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order = get_object_or_404(
            Order,
            id=serializer.validated_data['order_id'],
            user=request.user
        )
        
        intent = serializer.create_payment_intent(order)
        order.payment_intent_id = intent.id
        order.save()
        
        return Response({
            'client_secret': intent.client_secret,
            'payment_intent_id': intent.id
        })


class ConfirmPayment(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        payment_intent_id = request.data.get('payment_intent_id')
        
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status == 'succeeded':
                order = Order.objects.get(payment_intent_id=payment_intent_id)
                order.payment_status = 'completed'
                order.status = 'confirmed'
                order.save()
                
                Payment.objects.create(
                    order=order,
                    user=request.user,
                    amount=intent.amount / 100,
                    payment_method='stripe',
                    payment_intent_id=payment_intent_id,
                    status='completed',
                    metadata=intent
                )
                
                return Response({'status': 'success'})
            else:
                return Response(
                    {'error': 'Payment not successful'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except stripe.error.StripeError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class StripeWebhook(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            order = Order.objects.get(payment_intent_id=payment_intent['id'])
            order.payment_status = 'completed'
            order.status = 'confirmed'
            order.save()
            
            Payment.objects.create(
                order=order,
                user=order.user,
                amount=payment_intent['amount'] / 100,
                payment_method='stripe',
                payment_intent_id=payment_intent['id'],
                status='completed',
                metadata=payment_intent
            )
        
        return Response(status=status.HTTP_200_OK)


# ==================== ADMIN DASHBOARD VIEWS ====================

class AdminDashboardStats(APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        # Calculate statistics
        total_orders = Order.objects.count()
        total_revenue = Order.objects.filter(
            payment_status='completed'
        ).aggregate(total=Sum('total'))['total'] or 0
        
        total_customers = User.objects.filter(is_active=True).count()
        total_products = Product.objects.count()
        pending_orders = Order.objects.filter(status='pending').count()
        low_stock_products = Product.objects.filter(stock__lt=10).count()
        
        # Recent orders
        recent_orders = Order.objects.order_by('-created_at')[:10]
        
        # Top products
        top_products = OrderItem.objects.values(
            'product__name', 'product__id'
        ).annotate(
            total_sold=Sum('quantity'),
            total_revenue=Sum('total')
        ).order_by('-total_sold')[:10]
        
        data = {
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'total_customers': total_customers,
            'total_products': total_products,
            'pending_orders': pending_orders,
            'low_stock_products': low_stock_products,
            'recent_orders': OrderSerializer(recent_orders, many=True).data,
            'top_products': top_products
        }
        
        serializer = AdminDashboardStatsSerializer(data)
        return Response(serializer.data)


class AdminOrderList(generics.ListAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['order_number', 'user__email', 'user__username']
    ordering_fields = ['created_at', 'total', 'status']


class AdminOrderUpdate(generics.UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = AdminOrderUpdateSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def perform_update(self, serializer):
        order = self.get_object()
        old_status = order.status
        serializer.save()
        
        # If order is delivered, update delivered_at
        if serializer.validated_data.get('status') == 'delivered' and old_status != 'delivered':
            order.delivered_at = timezone.now()
            order.save()


class AdminProductManage(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminCategoryManage(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAdminUser]


class AdminCouponManage(generics.ListCreateAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        return Coupon.objects.all().order_by('-created_at')


class AdminCouponDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAdminUser]
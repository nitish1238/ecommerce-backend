from django.urls import path
from . import views

urlpatterns = [
    # ==================== AUTHENTICATION & USER URLS ====================
    
    # Registration & Login
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    
    # User Profile & Management
    path('auth/me/', views.CurrentUserView.as_view(), name='current-user'),
    path('auth/profile/', views.UserProfileView.as_view(), name='profile'),
    path('auth/users/', views.UserListView.as_view(), name='user-list'),
    path('auth/users/<int:user_id>/', views.UserDetailView.as_view(), name='user-detail'),
    
    # Password Management
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('auth/forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),
    
    # Email Verification
    path('auth/verify-email/<str:token>/', views.VerifyEmailView.as_view(), name='verify-email'),
    
    # Auth Status & Social
    path('auth/status/', views.CheckAuthStatusView.as_view(), name='auth-status'),
    path('auth/social/', views.SocialAuthView.as_view(), name='social-auth'),
    
    # ==================== CATEGORY URLS ====================
    path('categories/', views.CategoryList.as_view(), name='category-list'),
    path('categories/<int:pk>/', views.CategoryDetail.as_view(), name='category-detail'),
    
    # ==================== PRODUCT URLS ====================
    path('products/', views.ProductList.as_view(), name='product-list'),
    path('products/<int:pk>/', views.ProductDetail.as_view(), name='product-detail'),
    path('products/<int:product_id>/reviews/', views.ProductReviewList.as_view(), name='product-reviews'),
    path('reviews/<int:pk>/', views.ProductReviewDetail.as_view(), name='review-detail'),
    
    # ==================== CART URLS ====================
    path('cart/', views.CartView.as_view(), name='cart'),
    
    # ==================== WISHLIST URLS ====================
    path('wishlist/', views.WishlistView.as_view(), name='wishlist'),
    
    # ==================== ADDRESS URLS ====================
    path('addresses/', views.AddressList.as_view(), name='address-list'),
    path('addresses/<int:pk>/', views.AddressDetail.as_view(), name='address-detail'),
    
    # ==================== COUPON URLS ====================
    path('coupons/validate/', views.CouponValidateView.as_view(), name='coupon-validate'),
    
    # ==================== ORDER URLS ====================
    path('orders/', views.OrderList.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.OrderDetail.as_view(), name='order-detail'),
    path('orders/create/', views.CreateOrderView.as_view(), name='create-order'),
    
    # ==================== PAYMENT URLS ====================
    path('payments/create-intent/', views.CreatePaymentIntent.as_view(), name='create-payment-intent'),
    path('payments/confirm/', views.ConfirmPayment.as_view(), name='confirm-payment'),
    path('payments/webhook/', views.StripeWebhook.as_view(), name='stripe-webhook'),
    
    # ==================== ADMIN DASHBOARD URLS ====================
    path('admin/stats/', views.AdminDashboardStats.as_view(), name='admin-stats'),
    path('admin/orders/', views.AdminOrderList.as_view(), name='admin-orders'),
    path('admin/orders/<int:pk>/', views.AdminOrderUpdate.as_view(), name='admin-order-update'),
    path('admin/products/<int:pk>/', views.AdminProductManage.as_view(), name='admin-product-manage'),
    path('admin/categories/<int:pk>/', views.AdminCategoryManage.as_view(), name='admin-category-manage'),
    path('admin/coupons/', views.AdminCouponManage.as_view(), name='admin-coupon-list'),
    path('admin/coupons/<int:pk>/', views.AdminCouponDetail.as_view(), name='admin-coupon-detail'),
]
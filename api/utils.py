import random
import string
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime 

def send_verification_email(email, token):
    """Send email verification link to user"""
    verification_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    
    subject = 'Verify Your Email Address'
    message = f"""
    Thank you for registering!
    
    Please click the link below to verify your email address:
    {verification_link}
    
    If you didn't register for an account, please ignore this email.
    
    Thank you!
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL or 'noreply@ecommerce.com',
        [email],
        fail_silently=False,
    )

def send_password_reset_email(email, reset_link):
    """Send password reset link to user"""
    subject = 'Reset Your Password'
    message = f"""
    You requested to reset your password.
    
    Please click the link below to reset your password:
    {reset_link}
    
    This link will expire in 24 hours.
    
    If you didn't request this, please ignore this email.
    
    Thank you!
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL or 'noreply@ecommerce.com',
        [email],
        fail_silently=False,
    )

def generate_username_from_email(email):
    """Generate a unique username from email"""
    base_username = email.split('@')[0]
    username = base_username
    counter = 1
    
    from django.contrib.auth.models import User
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
    
    return username

def generate_order_number():
    """Generate a unique order number"""
    prefix = 'ORD'
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{timestamp}-{random_str}"

def send_order_confirmation_email(order):
    """Send order confirmation email to customer"""
    subject = f'Order Confirmation - {order.order_number}'
    message = f"""
    Thank you for your order!
    
    Order Number: {order.order_number}
    Total Amount: ${order.total}
    
    We'll notify you when your order ships.
    
    Thank you for shopping with us!
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        fail_silently=True,
    )

def calculate_tax(amount, country, state=None):
    """Calculate tax based on location"""
    # Implement your tax calculation logic here
    # This is a simple example
    tax_rates = {
        'US': 0.08,  # 8% for US
        'CA': 0.13,  # 13% for Canada
        'UK': 0.20,  # 20% for UK
    }
    
    rate = tax_rates.get(country, 0)
    return amount * rate

def validate_stock(items):
    """Validate stock availability for items"""
    for item in items:
        product = item['product']
        if product.stock < item['quantity']:
            return False, f"Insufficient stock for {product.name}"
    return True, "Stock available"

def process_refund(order, amount=None):
    """Process refund for an order"""
    if amount is None:
        amount = order.total
    
    if order.payment_method == 'stripe' and order.payment_intent_id:
        try:
            import stripe
            refund = stripe.Refund.create(
                payment_intent=order.payment_intent_id,
                amount=int(amount * 100)
            )
            return True, refund
        except stripe.error.StripeError as e:
            return False, str(e)
    
    return False, "Refund method not available"
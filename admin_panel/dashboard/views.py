from django.shortcuts import render
from django.db.models import Sum, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from decimal import Decimal
from common.decorators import admin_required
from user_panel.authentication.models import User
from user_panel.orders.models import Order
from admin_panel.products.models import Product

@admin_required
def admin_dashboard_view(request):
    total_users = User.objects.filter(is_staff=False, is_verified=True).count()
    total_orders = Order.objects.count()
    total_products = Product.objects.filter(is_active=True).count()
    
    total_sales = Order.objects.filter(payment_status='PAID').aggregate(Sum('total_price'))['total_price__sum'] or Decimal('0.00')
    pending_returns = Order.objects.filter(order_status='RETURN_REQUESTED').count()


    orders_qs = Order.objects.prefetch_related('items__product__images', 'items__variant__images', 'user')


    status_filter = request.GET.get('status', 'all').strip()
    if status_filter and status_filter != 'all':
        orders_qs = orders_qs.filter(order_status=status_filter)


    sort_by = request.GET.get('sort', 'newest').strip()
    if sort_by == 'oldest':
        orders_qs = orders_qs.order_by('created_at')
    elif sort_by == 'price_high':
        orders_qs = orders_qs.order_by('-total_price')
    elif sort_by == 'price_low':
        orders_qs = orders_qs.order_by('total_price')
    else:  
        orders_qs = orders_qs.order_by('-created_at')


    paginator = Paginator(orders_qs, 10)
    page_number = request.GET.get('page', 1)
    try:
        recent_orders = paginator.page(page_number)
    except PageNotAnInteger:
        recent_orders = paginator.page(1)
    except EmptyPage:
        recent_orders = paginator.page(paginator.num_pages)

    context = {
        "total_users": total_users,
        "total_orders": total_orders,
        "total_products": total_products,
        "total_sales": total_sales,
        "pending_returns": pending_returns,
        "active_offers": 0,
        "recent_orders": recent_orders,
        "status_filter": status_filter,
        "sort_by": sort_by,
        "admin_name": request.user.fullname,
    }
    return render(request, "admin_panel/dashboard/dashboard.html", context)


@admin_required
def admin_unimplemented_view(request):
    return render(request, "admin_panel/404.html", {"admin_name": request.user.fullname})

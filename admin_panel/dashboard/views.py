import json
from datetime import datetime, timedelta, time
from decimal import Decimal
from django.shortcuts import render
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate, TruncHour, TruncMonth
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from common.decorators import admin_required
from user_panel.authentication.models import User
from user_panel.orders.models import Order, OrderItem
from admin_panel.products.models import Product
from admin_panel.category.models import Category
from admin_panel.offers.models import ProductOffer


def get_dashboard_chart_data(preset, curr_tz):
    now = timezone.localtime(timezone.now())
    today_start = timezone.make_aware(datetime.combine(now.date(), time.min), curr_tz)
    today_end = timezone.make_aware(datetime.combine(now.date(), time.max), curr_tz)

    labels, sales_data, orders_data = [], [], []

    if preset == 'DAILY':
        start_date = today_start
        end_date = today_end
        hourly_aggs = Order.objects.filter(
            created_at__gte=start_date, created_at__lte=end_date
        ).exclude(order_status='CANCELLED').annotate(
            h=TruncHour('created_at', tzinfo=curr_tz)
        ).values('h').annotate(rev=Sum('total_price'), cnt=Count('id'))
        
        hdict = {item['h'].hour: (item['rev'] or Decimal('0.00'), item['cnt']) for item in hourly_aggs if item['h']}
        time_windows = [(0, 2, '12 AM'), (3, 5, '3 AM'), (6, 8, '6 AM'), (9, 11, '9 AM'), (12, 14, '12 PM'), (15, 17, '3 PM'), (18, 20, '6 PM'), (21, 23, '9 PM')]
        for start_h, end_h, label in time_windows:
            w_rev, w_cnt = Decimal('0.00'), 0
            for h in range(start_h, end_h + 1):
                r, c = hdict.get(h, (Decimal('0.00'), 0))
                w_rev += r
                w_cnt += c
            labels.append(label)
            sales_data.append(float(w_rev))
            orders_data.append(w_cnt)

    elif preset == 'WEEKLY':
        seven_days_ago = now.date() - timedelta(days=6)
        start_date = timezone.make_aware(datetime.combine(seven_days_ago, time.min), curr_tz)
        end_date = today_end
        daily_aggs = Order.objects.filter(
            created_at__gte=start_date, created_at__lte=end_date
        ).exclude(order_status='CANCELLED').annotate(
            d=TruncDate('created_at', tzinfo=curr_tz)
        ).values('d').annotate(rev=Sum('total_price'), cnt=Count('id'))

        ddict = {item['d']: (item['rev'] or Decimal('0.00'), item['cnt']) for item in daily_aggs if item['d']}
        curr_dt = start_date.date()
        while curr_dt <= end_date.date():
            r, c = ddict.get(curr_dt, (Decimal('0.00'), 0))
            labels.append(curr_dt.strftime('%a %d').upper())
            sales_data.append(float(r))
            orders_data.append(c)
            curr_dt += timedelta(days=1)

    elif preset == 'YEARLY':
        jan_first = now.date().replace(month=1, day=1)
        start_date = timezone.make_aware(datetime.combine(jan_first, time.min), curr_tz)
        end_date = today_end
        monthly_aggs = Order.objects.filter(
            created_at__gte=start_date, created_at__lte=end_date
        ).exclude(order_status='CANCELLED').annotate(
            m=TruncMonth('created_at', tzinfo=curr_tz)
        ).values('m').annotate(rev=Sum('total_price'), cnt=Count('id'))

        mdict = {item['m'].month: (item['rev'] or Decimal('0.00'), item['cnt']) for item in monthly_aggs if item['m']}
        for m in range(1, 13):
            r, c = mdict.get(m, (Decimal('0.00'), 0))
            labels.append(datetime(now.year, m, 1).strftime('%b').upper())
            sales_data.append(float(r))
            orders_data.append(c)

    else:  # MONTHLY
        preset = 'MONTHLY'
        thirty_days_ago = now.date() - timedelta(days=30)
        start_date = timezone.make_aware(datetime.combine(thirty_days_ago, time.min), curr_tz)
        end_date = today_end
        daily_aggs = Order.objects.filter(
            created_at__gte=start_date, created_at__lte=end_date
        ).exclude(order_status='CANCELLED').annotate(
            d=TruncDate('created_at', tzinfo=curr_tz)
        ).values('d').annotate(rev=Sum('total_price'), cnt=Count('id'))

        ddict = {item['d']: (item['rev'] or Decimal('0.00'), item['cnt']) for item in daily_aggs if item['d']}
        curr_dt = start_date.date()
        while curr_dt <= end_date.date():
            r, c = ddict.get(curr_dt, (Decimal('0.00'), 0))
            labels.append(curr_dt.strftime('%b %d'))
            sales_data.append(float(r))
            orders_data.append(c)
            curr_dt += timedelta(days=1)

    return preset, labels, sales_data, orders_data


@admin_required
def admin_dashboard_view(request):
    curr_tz = timezone.get_current_timezone()
    chart_preset = request.GET.get('preset', 'MONTHLY').strip().upper()

    total_users = User.objects.filter(is_staff=False, is_verified=True).count()
    total_orders = Order.objects.count()
    total_products = Product.objects.filter(is_active=True).count()
    total_sales = Order.objects.filter(payment_status='PAID').aggregate(Sum('total_price'))['total_price__sum'] or Decimal('0.00')
    pending_returns = Order.objects.filter(order_status='RETURN_REQUESTED').count()

    # Dynamic Chart Data
    chart_preset, chart_labels, chart_sales, chart_orders = get_dashboard_chart_data(chart_preset, curr_tz)

    # Top 10 Best Selling Products
    top_products = OrderItem.objects.exclude(item_status='CANCELLED') \
        .values('product__id', 'product__name', 'product__category__name') \
        .annotate(total_units=Sum('quantity'), total_revenue=Sum('item_subtotal')) \
        .order_by('-total_units')[:10]

    # Top 10 Best Selling Categories
    top_categories = OrderItem.objects.exclude(item_status='CANCELLED') \
        .filter(product__category__isnull=False) \
        .values('product__category__name') \
        .annotate(total_units=Sum('quantity'), total_revenue=Sum('item_subtotal')) \
        .order_by('-total_units')[:10]

    # Top 10 Best Selling Brands
    top_brands = OrderItem.objects.exclude(item_status='CANCELLED') \
        .filter(product__brand__isnull=False) \
        .values('product__brand') \
        .annotate(total_units=Sum('quantity'), total_revenue=Sum('item_subtotal')) \
        .order_by('-total_units')[:10]

    # Recent Orders Table
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

    active_prod_offers = ProductOffer.objects.filter(is_active=True).count()
    active_cat_offers = Category.objects.filter(is_deleted=False, is_active=True, is_offer_active=True, discount__gt=0).count()
    active_offers = active_prod_offers + active_cat_offers

    context = {
        "total_users": total_users,
        "total_orders": total_orders,
        "total_products": total_products,
        "total_sales": total_sales,
        "pending_returns": pending_returns,
        "active_offers": active_offers,
        "recent_orders": recent_orders,
        "status_filter": status_filter,
        "sort_by": sort_by,
        "chart_preset": chart_preset,
        "chart_labels_json": json.dumps(chart_labels),
        "chart_sales_json": json.dumps(chart_sales),
        "chart_orders_json": json.dumps(chart_orders),
        "top_products": top_products,
        "top_categories": top_categories,
        "top_brands": top_brands,
        "admin_name": getattr(request.user, 'fullname', None) or getattr(request.user, 'username', 'Admin'),
    }
    return render(request, "admin_panel/dashboard/dashboard.html", context)



@admin_required
def admin_unimplemented_view(request):
    return render(request, "admin_panel/404.html", {"admin_name": request.user.fullname})

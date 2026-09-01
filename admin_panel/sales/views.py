import csv
import json
import logging
from decimal import Decimal
from datetime import datetime, timedelta, time
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Sum, Count, Q, Avg
from django.db.models.functions import TruncDate, TruncHour, TruncMonth
from django.core.paginator import Paginator
from django.utils import timezone
from common.decorators import admin_required
from user_panel.orders.models import Order, OrderItem

logger = logging.getLogger(__name__)


def get_date_range_for_preset(filter_preset, start_date_str='', end_date_str=''):
    now = timezone.localtime(timezone.now())
    curr_tz = timezone.get_current_timezone()

    today_start = timezone.make_aware(datetime.combine(now.date(), time.min), curr_tz)
    today_end = timezone.make_aware(datetime.combine(now.date(), time.max), curr_tz)

    if filter_preset == 'DAILY':
        start_date = today_start
        end_date = today_end
        prev_start_date = today_start - timedelta(days=1)
        prev_end_date = today_end - timedelta(days=1)
    elif filter_preset == 'WEEKLY':
        seven_days_ago = now.date() - timedelta(days=6)
        start_date = timezone.make_aware(datetime.combine(seven_days_ago, time.min), curr_tz)
        end_date = today_end
        prev_start_date = start_date - timedelta(days=7)
        prev_end_date = start_date - timedelta(seconds=1)
    elif filter_preset == 'MONTHLY':
        thirty_days_ago = now.date() - timedelta(days=30)
        start_date = timezone.make_aware(datetime.combine(thirty_days_ago, time.min), curr_tz)
        end_date = today_end
        prev_start_date = start_date - timedelta(days=31)
        prev_end_date = start_date - timedelta(seconds=1)
    elif filter_preset == 'YEARLY':
        jan_first = now.date().replace(month=1, day=1)
        start_date = timezone.make_aware(datetime.combine(jan_first, time.min), curr_tz)
        end_date = today_end
        try:
            prev_start_date = start_date.replace(year=now.year - 1)
            prev_end_date = end_date.replace(year=now.year - 1)
        except ValueError:
            prev_start_date = start_date - timedelta(days=365)
            prev_end_date = start_date - timedelta(seconds=1)
    elif filter_preset == 'CUSTOM':
        try:
            if start_date_str:
                d_start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                start_date = timezone.make_aware(datetime.combine(d_start, time.min), curr_tz)
            else:
                start_date = timezone.make_aware(datetime.combine(now.date() - timedelta(days=30), time.min), curr_tz)
            
            if end_date_str:
                d_end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                end_date = timezone.make_aware(datetime.combine(d_end, time.max), curr_tz)
            else:
                end_date = today_end
        except ValueError:
            start_date = timezone.make_aware(datetime.combine(now.date() - timedelta(days=30), time.min), curr_tz)
            end_date = today_end
            filter_preset = 'CUSTOM'

        duration = end_date - start_date
        prev_start_date = start_date - duration - timedelta(seconds=1)
        prev_end_date = start_date - timedelta(seconds=1)
    else:
        filter_preset = 'MONTHLY'
        thirty_days_ago = now.date() - timedelta(days=30)
        start_date = timezone.make_aware(datetime.combine(thirty_days_ago, time.min), curr_tz)
        end_date = today_end
        prev_start_date = start_date - timedelta(days=31)
        prev_end_date = start_date - timedelta(seconds=1)

    return now, curr_tz, start_date, end_date, prev_start_date, prev_end_date, filter_preset


@admin_required
def admin_sales_report_view(request):
    filter_preset = request.GET.get('preset', 'MONTHLY').strip().upper()
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    page_num = request.GET.get('page', '1').strip()

    now, curr_tz, start_date, end_date, prev_start_date, prev_end_date, filter_preset = get_date_range_for_preset(filter_preset, start_date_str, end_date_str)

    # Query Non-Cancelled Orders within Date Window
    base_orders_qs = Order.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    valid_orders_qs = base_orders_qs.exclude(order_status='CANCELLED')

    prev_valid_orders_qs = Order.objects.filter(
        created_at__gte=prev_start_date,
        created_at__lte=prev_end_date
    ).exclude(order_status='CANCELLED')

    # Aggregated KPI Metrics
    total_orders = valid_orders_qs.count()
    gross_sales = valid_orders_qs.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
    net_revenue = valid_orders_qs.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
    total_discounts = valid_orders_qs.aggregate(total=Sum('discount_amount'))['total'] or Decimal('0.00')
    
    avg_order_value = (net_revenue / Decimal(total_orders)).quantize(Decimal('0.01')) if total_orders > 0 else Decimal('0.00')

    wallet_used = valid_orders_qs.filter(payment_method='WALLET').aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
    cod_revenue = valid_orders_qs.filter(payment_method='CASH_ON_DELIVERY').aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')

    # Period-Over-Period percentage calculations
    prev_total_orders = prev_valid_orders_qs.count()
    prev_gross_sales = prev_valid_orders_qs.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
    prev_net_revenue = prev_valid_orders_qs.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
    prev_total_discounts = prev_valid_orders_qs.aggregate(total=Sum('discount_amount'))['total'] or Decimal('0.00')
    prev_avg_order_value = (prev_net_revenue / Decimal(prev_total_orders)).quantize(Decimal('0.01')) if prev_total_orders > 0 else Decimal('0.00')

    def calc_pct(curr, prev):
        c_val = float(curr)
        p_val = float(prev)
        if p_val == 0:
            return 100.0 if c_val > 0 else 0.0
        return round(((c_val - p_val) / p_val) * 100.0, 1)

    orders_pct = calc_pct(total_orders, prev_total_orders)
    gross_pct = calc_pct(gross_sales, prev_gross_sales)
    revenue_pct = calc_pct(net_revenue, prev_net_revenue)
    aov_pct = calc_pct(avg_order_value, prev_avg_order_value)
    discounts_pct = calc_pct(total_discounts, prev_total_discounts)

    # Payment Methods Distribution
    razorpay_count = valid_orders_qs.filter(payment_method='RAZORPAY').count()
    wallet_count = valid_orders_qs.filter(payment_method='WALLET').count()
    cod_count = valid_orders_qs.filter(payment_method='CASH_ON_DELIVERY').count()

    total_pay_count = razorpay_count + wallet_count + cod_count
    if total_pay_count > 0:
        razorpay_pct = round((razorpay_count / total_pay_count) * 100, 1)
        wallet_pct = round((wallet_count / total_pay_count) * 100, 1)
        cod_pct = round((cod_count / total_pay_count) * 100, 1)
    else:
        razorpay_pct = wallet_pct = cod_pct = 0.0

    # Trend Chart Data Aggregation
    trend_labels = []
    trend_gross = []
    trend_revenue = []
    trend_orders = []

    if filter_preset == 'DAILY':
        # Hourly breakdown for Today (3-hour windows: 12 AM, 3 AM, 6 AM, 9 AM, 12 PM, 3 PM, 6 PM, 9 PM)
        hourly_aggs = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).exclude(order_status='CANCELLED').annotate(
            h=TruncHour('created_at', tzinfo=curr_tz)
        ).values('h').annotate(
            gross=Sum('subtotal'),
            rev=Sum('total_price'),
            cnt=Count('id')
        )
        hdict = {item['h'].hour: (item['gross'] or Decimal('0.00'), item['rev'] or Decimal('0.00'), item['cnt']) for item in hourly_aggs if item['h']}

        time_windows = [
            (0, 2, '12 AM'),
            (3, 5, '3 AM'),
            (6, 8, '6 AM'),
            (9, 11, '9 AM'),
            (12, 14, '12 PM'),
            (15, 17, '3 PM'),
            (18, 20, '6 PM'),
            (21, 23, '9 PM')
        ]
        for start_h, end_h, label in time_windows:
            w_gross = Decimal('0.00')
            w_rev = Decimal('0.00')
            w_cnt = 0
            for h in range(start_h, end_h + 1):
                g, r, c = hdict.get(h, (Decimal('0.00'), Decimal('0.00'), 0))
                w_gross += g
                w_rev += r
                w_cnt += c
            trend_labels.append(label)
            trend_gross.append(float(w_gross))
            trend_revenue.append(float(w_rev))
            trend_orders.append(w_cnt)

    elif filter_preset == 'YEARLY':
        # Monthly breakdown for Year (12 months: JAN, FEB, ..., DEC)
        monthly_aggs = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).exclude(order_status='CANCELLED').annotate(
            m=TruncMonth('created_at', tzinfo=curr_tz)
        ).values('m').annotate(
            gross=Sum('subtotal'),
            rev=Sum('total_price'),
            cnt=Count('id')
        )
        mdict = {item['m'].month: (item['gross'] or Decimal('0.00'), item['rev'] or Decimal('0.00'), item['cnt']) for item in monthly_aggs if item['m']}

        for m in range(1, 13):
            gross_val, rev_val, cnt_val = mdict.get(m, (Decimal('0.00'), Decimal('0.00'), 0))
            trend_labels.append(datetime(now.year, m, 1).strftime('%b').upper())
            trend_gross.append(float(gross_val))
            trend_revenue.append(float(rev_val))
            trend_orders.append(cnt_val)

    else:
        # Daily breakdown for WEEKLY, MONTHLY, CUSTOM
        daily_aggregates = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).exclude(order_status='CANCELLED').annotate(
            order_date=TruncDate('created_at', tzinfo=curr_tz)
        ).values('order_date').annotate(
            gross=Sum('subtotal'),
            rev=Sum('total_price'),
            cnt=Count('id')
        )

        rev_dict = {item['order_date']: (item['gross'] or Decimal('0.00'), item['rev'] or Decimal('0.00'), item['cnt']) for item in daily_aggregates if item['order_date']}

        curr_dt = start_date.date()
        end_dt = end_date.date()
        while curr_dt <= end_dt:
            gross_val, rev_val, cnt_val = rev_dict.get(curr_dt, (Decimal('0.00'), Decimal('0.00'), 0))

            if filter_preset == 'WEEKLY':
                trend_labels.append(curr_dt.strftime('%a %d').upper())
            else:
                trend_labels.append(curr_dt.strftime('%b %d'))

            trend_gross.append(float(gross_val))
            trend_revenue.append(float(rev_val))
            trend_orders.append(cnt_val)
            curr_dt += timedelta(days=1)

    # Paginated Transactions Table
    transactions_list = valid_orders_qs.select_related('user').order_by('-created_at')
    paginator = Paginator(transactions_list, 10)
    try:
        transactions = paginator.page(page_num)
    except Exception:
        transactions = paginator.page(1)

    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'filter_preset': filter_preset,
        'start_date_str': start_date.strftime('%Y-%m-%d'),
        'end_date_str': end_date.strftime('%Y-%m-%d'),
        'total_orders': total_orders,
        'gross_sales': gross_sales,
        'net_revenue': net_revenue,
        'avg_order_value': avg_order_value,
        'total_discounts': total_discounts,
        'wallet_used': wallet_used,
        'cod_revenue': cod_revenue,
        'orders_pct': orders_pct,
        'gross_pct': gross_pct,
        'revenue_pct': revenue_pct,
        'aov_pct': aov_pct,
        'discounts_pct': discounts_pct,
        'razorpay_count': razorpay_count,
        'wallet_count': wallet_count,
        'cod_count': cod_count,
        'total_pay_count': total_pay_count,
        'razorpay_pct': razorpay_pct,
        'wallet_pct': wallet_pct,
        'cod_pct': cod_pct,
        'trend_labels_json': json.dumps(trend_labels),
        'trend_gross_json': json.dumps(trend_gross),
        'trend_revenue_json': json.dumps(trend_revenue),
        'trend_orders_json': json.dumps(trend_orders),
        'page_obj': transactions,
        'transactions': transactions,
        'admin_name': getattr(request.user, 'fullname', None) or getattr(request.user, 'username', 'Admin'),
    }

    return render(request, 'admin_panel/sales/sales_report.html', context)


@admin_required
def export_sales_report_excel(request):
    filter_preset = request.GET.get('preset', 'DAILY').strip().upper()
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()

    now, curr_tz, start_date, end_date, prev_start_date, prev_end_date, filter_preset = get_date_range_for_preset(filter_preset, start_date_str, end_date_str)

    base_orders_qs = Order.objects.filter(created_at__gte=start_date, created_at__lte=end_date).select_related('user').order_by('-created_at')
    valid_orders_qs = base_orders_qs.exclude(order_status='CANCELLED')

    total_orders = valid_orders_qs.count()
    net_revenue = valid_orders_qs.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
    total_discounts = valid_orders_qs.aggregate(total=Sum('discount_amount'))['total'] or Decimal('0.00')
    wallet_used = valid_orders_qs.filter(payment_method='WALLET').aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
    avg_order_value = (net_revenue / Decimal(total_orders)).quantize(Decimal('0.01')) if total_orders > 0 else Decimal('0.00')

    response = HttpResponse(content_type='text/csv')
    filename = f"Zitarra_Sales_Report_{filter_preset}_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(["ZITARRA SALES REPORT"])
    writer.writerow(["Period Preset", filter_preset])
    writer.writerow(["Date Range", f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"])
    writer.writerow([])
    writer.writerow(["SUMMARY METRICS"])
    writer.writerow(["Total Orders", total_orders])
    writer.writerow(["Net Revenue (INR)", f"{net_revenue:.2f}"])
    writer.writerow(["Avg Order Value (INR)", f"{avg_order_value:.2f}"])
    writer.writerow(["Total Discounts (INR)", f"{total_discounts:.2f}"])
    writer.writerow(["Wallet Revenue (INR)", f"{wallet_used:.2f}"])
    writer.writerow([])
    writer.writerow(["TRANSACTION LEDGER"])
    writer.writerow(["Order ID", "Date & Time", "Customer Name", "Customer Email", "Subtotal (INR)", "Discount (INR)", "Shipping (INR)", "Total Price (INR)", "Payment Method", "Status"])

    for order in valid_orders_qs:
        writer.writerow([
            order.order_id,
            order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            order.shipping_full_name or order.user.username,
            order.user.email,
            f"{order.subtotal:.2f}",
            f"{order.discount_amount:.2f}",
            f"{order.shipping_cost:.2f}",
            f"{order.total_price:.2f}",
            order.payment_method,
            order.get_order_status_display()
        ])

    return response


@admin_required
def export_sales_report_pdf(request):
    filter_preset = request.GET.get('preset', 'DAILY').strip().upper()
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()

    now, curr_tz, start_date, end_date, prev_start_date, prev_end_date, filter_preset = get_date_range_for_preset(filter_preset, start_date_str, end_date_str)

    base_orders_qs = Order.objects.filter(created_at__gte=start_date, created_at__lte=end_date).select_related('user').order_by('-created_at')
    valid_orders_qs = base_orders_qs.exclude(order_status='CANCELLED')

    total_orders = valid_orders_qs.count()
    net_revenue = valid_orders_qs.aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
    total_discounts = valid_orders_qs.aggregate(total=Sum('discount_amount'))['total'] or Decimal('0.00')
    wallet_used = valid_orders_qs.filter(payment_method='WALLET').aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
    avg_order_value = (net_revenue / Decimal(total_orders)).quantize(Decimal('0.01')) if total_orders > 0 else Decimal('0.00')

    context = {
        'filter_preset': filter_preset,
        'start_date_str': start_date.strftime('%Y-%m-%d'),
        'end_date_str': end_date.strftime('%Y-%m-%d'),
        'total_orders': total_orders,
        'net_revenue': net_revenue,
        'avg_order_value': avg_order_value,
        'total_discounts': total_discounts,
        'wallet_used': wallet_used,
        'orders': valid_orders_qs[:100],  # Limit printable rows
        'printed_at': now.strftime('%Y-%m-%d %H:%M:%S'),
    }

    return render(request, 'admin_panel/sales/sales_report_pdf.html', context)

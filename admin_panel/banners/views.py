from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from common.decorators import admin_required
from .models import Banner, ShopShowcase
from admin_panel.products.models import Product
from django.utils.dateparse import parse_date
from datetime import time, datetime


@admin_required
def admin_banners_view(request):
    banners_list = Banner.objects.filter(is_deleted=False).order_by('display_mode', 'priority')

    active_count = banners_list.filter(status='PUBLISHED').count()
    draft_count = banners_list.filter(status='DRAFT').count()

    paginator = Paginator(banners_list, 4)
    page_number = request.GET.get('page')
    try:
        banners_page = paginator.page(page_number)
    except PageNotAnInteger:
        banners_page = paginator.page(1)
    except EmptyPage:
        banners_page = paginator.page(paginator.num_pages)

    context = {
        'admin_name': getattr(request.user, 'fullname', 'Admin'),
        'banners': banners_page,
        'all_banners': banners_list,
        'active_count': active_count,
        'draft_count': draft_count,
        'now': timezone.now(),
    }
    return render(request, 'admin_panel/banners/banners.html', context)


@admin_required
def add_banner_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        target_url = request.POST.get('target_url', '').strip() or '/shop/'
        display_mode = request.POST.get('display_mode', 'HERO_SLIDER').strip()
        priority_val = request.POST.get('priority', '1').strip()
        image = request.FILES.get('image')
        end_date_val = request.POST.get('end_date', '').strip()

        if not title:
            messages.error(request, "Banner title is required.")
            return redirect('admin_banners')

        if not image:
            messages.error(request, "Please upload a high-resolution image asset.")
            return redirect('admin_banners')

        auto_reorder = request.POST.get('auto_reorder') == 'true'

        try:
            priority = int(priority_val)
            if priority < 1:
                priority = 1
        except ValueError:
            priority = 1

        end_date = None
        if end_date_val:
            try:
                d = parse_date(end_date_val)
                if d:
                    dt = datetime.combine(d, time(23, 59, 59))
                    end_date = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
            except Exception:
                end_date = None

        # Check for conflicting banner with the same priority in this display mode
        existing_banner = Banner.objects.filter(
            is_deleted=False,
            display_mode=display_mode,
            priority=priority
        ).first()

        if existing_banner:
            if auto_reorder:
                # Confirmed: Auto-shift existing banners with priority >= new_priority up by 1
                conflicting = list(Banner.objects.filter(
                    is_deleted=False,
                    display_mode=display_mode,
                    priority__gte=priority
                ).order_by('-priority'))
                for b in conflicting:
                    b.priority += 1
                    b.save(update_fields=['priority'])
            else:
                messages.error(
                    request,
                    f"Priority {priority} is already assigned to '{existing_banner.clean_title}'. Please choose an unused priority or reassign the existing banner."
                )
                return redirect('admin_banners')

        Banner.objects.create(
            title=title,
            target_url=target_url,
            display_mode=display_mode,
            priority=priority,
            image=image,
            end_date=end_date,
            status='PUBLISHED'
        )

        messages.success(request, f"Banner asset '{title}' deployed successfully!")
        return redirect('admin_banners')

    return redirect('admin_banners')


@admin_required
def edit_banner_view(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id, is_deleted=False)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        target_url = request.POST.get('target_url', '').strip()
        display_mode = request.POST.get('display_mode', '').strip()
        priority_val = request.POST.get('priority', '').strip()
        status = request.POST.get('status', '').strip()
        image = request.FILES.get('image')
        auto_reorder = request.POST.get('auto_reorder') == 'true'

        target_mode = display_mode if display_mode else banner.display_mode

        if priority_val:
            try:
                new_priority = int(priority_val)
                if new_priority < 1:
                    new_priority = 1

                existing_banner = Banner.objects.filter(
                    is_deleted=False,
                    display_mode=target_mode,
                    priority=new_priority
                ).exclude(id=banner.id).first()

                if existing_banner:
                    if auto_reorder:
                        conflicting = list(Banner.objects.filter(
                            is_deleted=False,
                            display_mode=target_mode,
                            priority__gte=new_priority
                        ).exclude(id=banner.id).order_by('-priority'))
                        for b in conflicting:
                            b.priority += 1
                            b.save(update_fields=['priority'])
                    else:
                        messages.error(
                            request,
                            f"Priority {new_priority} is already assigned to '{existing_banner.clean_title}'. Please choose an unused priority or reassign the existing banner."
                        )
                        return redirect('admin_banners')

                banner.priority = new_priority
            except ValueError:
                pass

        if title:
            banner.title = title
        if target_url:
            banner.target_url = target_url
        if display_mode:
            banner.display_mode = display_mode
        if status in ['PUBLISHED', 'DRAFT']:
            banner.status = status

        if image:
            banner.image = image

        if 'end_date' in request.POST:
            end_date_val = request.POST.get('end_date', '').strip()
            if end_date_val:
                try:
                    d = parse_date(end_date_val)
                    if d:
                        dt = datetime.combine(d, time(23, 59, 59))
                        banner.end_date = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
                except Exception:
                    pass
            else:
                banner.end_date = None

        banner.save()
        messages.success(request, f"Banner '{banner.title}' updated successfully!")
        return redirect('admin_banners')

    return redirect('admin_banners')


@admin_required
def toggle_banner_status_view(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id, is_deleted=False)
    
    if banner.status == 'PUBLISHED':
        banner.status = 'DRAFT'
        msg = f"Banner '{banner.title}' set to DRAFT."
    else:
        banner.status = 'PUBLISHED'
        msg = f"Banner '{banner.title}' is now LIVE NOW (Published)."

    banner.save()
    messages.success(request, msg)
    return redirect('admin_banners')


@admin_required
def delete_banner_view(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id, is_deleted=False)
    banner.is_deleted = True
    banner.save()
    messages.success(request, f"Banner '{banner.title}' removed successfully.")
    return redirect('admin_banners')


@admin_required
def admin_showcases_view(request):
    showcases = ShopShowcase.objects.all().select_related('product')
    showcase_dict = {s.slot: s for s in showcases}
    products = Product.objects.filter(is_deleted=False, is_active=True).order_by('name')

    context = {
        'admin_name': getattr(request.user, 'fullname', 'Admin'),
        'hero_left': showcase_dict.get('HERO_LEFT'),
        'hero_right': showcase_dict.get('HERO_RIGHT'),
        'grid_spotlight': showcase_dict.get('GRID_SPOTLIGHT'),
        'sidebar_promo': showcase_dict.get('SIDEBAR_PROMO'),
        'products': products,
    }
    return render(request, 'admin_panel/banners/showcases.html', context)


@admin_required
def edit_showcase_view(request, showcase_id):
    showcase = get_object_or_404(ShopShowcase, id=showcase_id)
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        badge_text = request.POST.get('badge_text', '').strip()
        custom_title = request.POST.get('custom_title', '').strip()
        subtitle = request.POST.get('subtitle', '').strip()
        button_label = request.POST.get('button_label', '').strip()
        banner_image = request.FILES.get('banner_image')
        is_active = request.POST.get('is_active') == 'true' or request.POST.get('is_active') == 'on'

        if product_id:
            try:
                selected_prod = Product.objects.get(id=product_id, is_deleted=False)
                showcase.product = selected_prod
            except Product.DoesNotExist:
                pass

        if badge_text:
            showcase.badge_text = badge_text
        showcase.custom_title = custom_title
        showcase.subtitle = subtitle
        if button_label:
            showcase.button_label = button_label
        if banner_image:
            showcase.banner_image = banner_image

        if showcase.slot == 'GRID_SPOTLIGHT':
            showcase.spec_1_label = request.POST.get('spec_1_label', 'Wattage').strip()
            showcase.spec_1_value = request.POST.get('spec_1_value', '').strip()
            showcase.spec_2_label = request.POST.get('spec_2_label', 'Speakers').strip()
            showcase.spec_2_value = request.POST.get('spec_2_value', '').strip()
            showcase.spec_3_label = request.POST.get('spec_3_label', 'Valves').strip()
            showcase.spec_3_value = request.POST.get('spec_3_value', '').strip()
            showcase.spec_4_label = request.POST.get('spec_4_label', 'Inputs').strip()
            showcase.spec_4_value = request.POST.get('spec_4_value', '').strip()

        showcase.is_active = is_active
        showcase.save()
        messages.success(request, f"Showcase slot '{showcase.get_slot_display()}' updated successfully!")
        return redirect('admin_showcases')

    return redirect('admin_showcases')


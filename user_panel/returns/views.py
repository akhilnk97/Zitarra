from datetime import timedelta
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from common.decorators import user_member_required
from user_panel.orders.models import Order, OrderItem
from user_panel.returns.models import ReturnRequestImage


@user_member_required
def return_order_view(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, order_id=order_id, user=request.user)

        if order.order_status == 'DELIVERED':
            reason_select = request.POST.get('return_reason_select', '').strip()
            reason_text = request.POST.get('return_reason', '').strip()
            uploaded_images = request.FILES.getlist('return_images') or request.FILES.getlist('images')

            if not reason_select and not reason_text:
                messages.error(request, "Please select or describe a reason for your return request.")
                return redirect('order_detail', order_id=order_id)

            if reason_select == 'Other' and not reason_text:
                messages.error(request, "Please provide details in the text field when selecting 'Other'.")
                return redirect('order_detail', order_id=order_id)
            
            # Check mandatory photo proof for defective / wrong item reasons
            is_proof_required = any(keyword in reason_select.lower() for keyword in ['defective', 'damaged', 'wrong'])
            if is_proof_required and not uploaded_images:
                messages.error(request, f"Please upload at least one photo proof for return reason '{reason_select}'.")
                return redirect('order_detail', order_id=order_id)

            reason = reason_select
            if reason_select == 'Other' or not reason:
                reason = reason_text
            elif reason_text:
                reason = f"{reason_select}: {reason_text}"

            with transaction.atomic():
                order.order_status = 'RETURN_REQUESTED'
                order.return_reason = reason
                order.save()

                for item in order.items.all():
                    if item.item_status not in ['CANCELLED', 'RETURNED']:
                        item.item_status = 'RETURN_REQUESTED'
                        item.cancel_reason = reason
                        item.expected_pickup_date = item.effective_expected_delivery_date + timedelta(days=3)
                        item.save(update_fields=['item_status', 'cancel_reason', 'expected_pickup_date'])

                        for img_file in uploaded_images:
                            ReturnRequestImage.objects.create(order_item=item, image=img_file)

            messages.success(request, f"Return request submitted for Order #{order.order_id}. Our team will review your request shortly.")
        else:
            messages.error(request, "Return requests can only be submitted for delivered orders.")

    return redirect('order_detail', order_id=order_id)


@user_member_required
def return_order_item_view(request, order_id, item_id):
    order_item = get_object_or_404(OrderItem, id=item_id, order__order_id=order_id, order__user=request.user)
    next_url = request.META.get('HTTP_REFERER') or reverse('order_detail', kwargs={'order_id': order_id})

    if request.method == 'POST':
        if order_item.admin_note and 'reject' in order_item.admin_note.lower() or order_item.cancel_reason and 'return rejected' in order_item.cancel_reason.lower():
            messages.error(request, f"A return request for '{order_item.product_name}' has already been rejected.")
            return redirect(next_url)

        if order_item.item_status == 'DELIVERED':
            reason_select = request.POST.get('return_reason_select', '').strip()
            reason_text = request.POST.get('return_reason', '').strip()
            uploaded_images = request.FILES.getlist('return_images') or request.FILES.getlist('images')

            if not reason_select and not reason_text:
                messages.error(request, "Please select or describe a reason for your return request.")
                return redirect(next_url)

            if reason_select == 'Other' and not reason_text:
                messages.error(request, "Please provide details in the text field when selecting 'Other'.")
                return redirect(next_url)
            
            is_proof_required = any(keyword in reason_select.lower() for keyword in ['defective', 'damaged', 'wrong'])
            if is_proof_required and not uploaded_images:
                messages.error(request, f"Please upload at least one photo proof for return reason '{reason_select}'.")
                return redirect(next_url)

            reason = reason_select
            if reason_select == 'Other' or not reason:
                reason = reason_text
            elif reason_text:
                reason = f"{reason_select}: {reason_text}"

            with transaction.atomic():
                order_item.item_status = 'RETURN_REQUESTED'
                order_item.cancel_reason = reason
                order_item.expected_pickup_date = order_item.effective_expected_delivery_date + timedelta(days=3)
                order_item.save(update_fields=['item_status', 'cancel_reason', 'expected_pickup_date'])
                
                for img_file in uploaded_images:
                    ReturnRequestImage.objects.create(order_item=order_item, image=img_file)

                order_item.order.recalculate_totals()

            messages.success(request, f"Return request submitted for '{order_item.product_name}'.")
        else:
            messages.error(request, "Only delivered products can be returned.")

    return redirect(next_url)

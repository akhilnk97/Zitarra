from django.shortcuts import redirect, get_object_or_404
from django.db.models import F
from admin_panel.banners.models import Banner


def track_banner_click_view(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id, is_deleted=False)
    
    # Atomically increment click count
    Banner.objects.filter(id=banner.id).update(clicks_count=F('clicks_count') + 1)
    
    target = banner.target_url if banner.target_url else '/shop/'
    return redirect(target)

import base64
import math
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.base import ContentFile
from django.contrib import messages
from django.db import transaction, models
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from common.decorators import admin_required
from common.services import save_base64_image
from .models import Product, ProductImage, ProductVariant, VariantImage
from admin_panel.category.models import Category
from admin_panel.brands.models import Brand
from admin_panel.offers.models import ProductOffer



@admin_required
def admin_products_view(request):
    products_list = Product.objects.filter(is_deleted=False)

    search = request.GET.get('search', '').strip()
    category_id = request.GET.get('category', '').strip()
    sort_by = request.GET.get('sort', 'newest').strip()

    if search:
        products_list = products_list.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    if category_id:
        products_list = products_list.filter(category_id=category_id)

    if sort_by == 'oldest':
        products_list = products_list.order_by('created_at')
    elif sort_by == 'name_asc':
        products_list = products_list.order_by('name')
    elif sort_by == 'name_desc':
        products_list = products_list.order_by('-name')
    else:  
        products_list = products_list.order_by('-created_at')

    paginator = Paginator(products_list, 10)
    page_number = request.GET.get('page', 1)
    try:
        products = paginator.page(page_number)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    categories = Category.objects.filter(is_deleted=False, is_active=True)

    return render(request, 'admin_panel/products/products.html', {
        "products": products,
        "categories": categories,
        "search": search,
        "category_id": category_id,
        "sort_by": sort_by,
        "admin_name": request.user.fullname
    })


@admin_required
def admin_product_add_view(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category_id = request.POST.get("category")
        category = get_object_or_404(Category, id=category_id)

        if not name:
            messages.error(request, "Product name is required.")
            return redirect('admin_product_add')

        if Product.objects.filter(name__iexact=name, category=category, is_deleted=False).exists():
            messages.error(request, f"A product named '{name}' already exists in the '{category.name}' category.")
            return redirect('admin_product_add')

        description = request.POST.get("description", "").strip()
        if len(description) > 500:
            messages.error(request, "Product description cannot exceed 500 characters.")
            return redirect('admin_product_add')
        
        # VALIDATE MAIN PRODUCT IMAGES (Before creating anything in DB)
        cropped_images_data = request.POST.getlist("cropped_images")
        if len(cropped_images_data) < 3 or len(cropped_images_data) > 5:
            messages.error(request, "YOU MUST UPLOAD AND CROP AT LEAST 3 IMAGES.")
            return redirect('admin_product_add')

        # VALIDATE VARIANTS (Before creating anything in DB)
        parsed_variants = []
        variant_indices_str = request.POST.get("variant_indices", "")
        if variant_indices_str:
            variant_indices = []
            for idx in variant_indices_str.split(","):
                idx = idx.strip()

                if idx.isdigit():
                    variant_indices.append(int(idx))
            
            for idx in variant_indices:
                v_name = request.POST.get(f"variant_name_{idx}", "").strip()
                v_color = request.POST.get(f"variant_color_{idx}", "").strip()
                v_price = request.POST.get(f"variant_price_{idx}", "").strip()
                v_stock = request.POST.get(f"variant_stock_{idx}", "").strip()
                v_image_data = request.POST.getlist(f"variant_images_{idx}")

                if v_name and v_color and v_stock:
                    is_base64 = len(v_image_data) > 0
                    img_list = v_image_data if is_base64 else request.FILES.getlist(f"variant_image_{idx}")

                    if len(img_list) < 3 or len(img_list) > 5:
                        messages.error(request, f"VARIANT '{v_name.upper()}': YOU MUST UPLOAD AND CROP AT LEAST 3 IMAGES (MAX 5).")
                        return redirect('admin_product_add')

                    try:
                        v_stock = int(v_stock)
                        if v_stock < 0:
                            v_stock = 0
                    except ValueError:
                        v_stock = 0    

                    try:
                        v_price = float(v_price) if v_price and float(v_price) > 0 else None
                    except ValueError:
                        v_price = None

                    parsed_variants.append({
                        "name": v_name,
                        "color_code": v_color,
                        "price": v_price,
                        "stock": v_stock,
                        "img_list": img_list,
                        "is_base64": is_base64
                    })  
        if not parsed_variants:
            # If no manual variant added, automatically create the primary variant so every product is a variant
            try:
                auto_price = float(request.POST.get("price", 0) or 0)
            except ValueError:
                auto_price = 0.0
            try:
                auto_stock = int(request.POST.get("stock", 0) or 0)
            except ValueError:
                auto_stock = 0

            parsed_variants.append({
                "name": "Standard Edition",
                "color_code": "#1A1A1A",
                "price": auto_price,
                "stock": auto_stock,
                "img_list": cropped_images_data,
                "is_base64": True
            })

        # Sync product price and stock from variants
        primary_var_price = parsed_variants[0]["price"] if parsed_variants[0]["price"] else request.POST.get("price")
        total_var_stock = sum(v["stock"] for v in parsed_variants)

        offer_val = request.POST.get("offer_id") or request.POST.get("offer")
        product_offer = None
        if offer_val and str(offer_val).isdigit():
            product_offer = ProductOffer.objects.filter(id=offer_val, is_active=True).first()

        with transaction.atomic():
            product = Product.objects.create(
                name=request.POST.get("name"),
                description=request.POST.get("description"),
                price=primary_var_price,
                stock=total_var_stock,
                category=category,
                is_active="is_active" in request.POST,
                highlights=request.POST.get("highlights", "").strip(),
                brand=request.POST.get("brand", "").strip(),
                offer=product_offer.name if product_offer else (request.POST.get("offer", "").strip() or None),
                product_offer=product_offer
            )

            # Save Main Product Images using save_base64_image
            for i, img_str in enumerate(cropped_images_data):
                image_file = save_base64_image(img_str, f"{product.id}_image_{i}")
                if image_file:
                    ProductImage.objects.create(product=product, image=image_file)
            
            # Save Product Variants & Variant Images
            for v_data in parsed_variants:
                variant = ProductVariant.objects.create(
                    product=product,
                    name=v_data["name"],
                    color_code=v_data["color_code"],
                    price=v_data["price"],
                    stock=v_data["stock"]
                )

                for i, img in enumerate(v_data["img_list"]):
                    if v_data["is_base64"]:
                        image_file = save_base64_image(img, f"variant_{variant.id}_image_{i}")
                    else:
                        image_file = img
                    if image_file:
                        VariantImage.objects.create(variant=variant, image=image_file)

        messages.success(request, "Product added successfully!")
        return redirect('admin_products')  
    
    categories = Category.objects.filter(is_deleted=False, is_active=True)
    brands = Brand.objects.filter(is_deleted=False, status='ACTIVE').order_by('name')
    active_offers = ProductOffer.objects.filter(is_active=True).order_by('name')
    return render(request, 'admin_panel/products/add_product.html', {
        'categories': categories,
        'brands': brands,
        'active_offers': active_offers,
        'admin_name': request.user.fullname
    })


@admin_required
def admin_product_edit_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_deleted=False)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category_id = request.POST.get("category")
        category = get_object_or_404(Category, id=category_id)

        if not name:
            messages.error(request, "Product name is required.")
            return redirect('admin_product_edit', product_id=product.id)

        if Product.objects.filter(name__iexact=name, category=category, is_deleted=False).exclude(id=product.id).exists():
            messages.error(request, f"A product named '{name}' already exists in the '{category.name}' category.")
            return redirect('admin_product_edit', product_id=product.id)

        description = request.POST.get("description", "").strip()
        if len(description) > 500:
            messages.error(request, "Product description cannot exceed 500 characters.")
            return redirect('admin_product_edit', product_id=product.id)

        # VALIDATE NEW IMAGES FIRST (If uploaded)
        cropped_images_data = request.POST.getlist("cropped_images")
        if cropped_images_data:
            if len(cropped_images_data) < 3 or len(cropped_images_data) > 5:
                messages.error(request, "YOU MUST UPLOAD AND CROP AT LEAST 3 IMAGES.")
                return redirect('admin_product_edit', product_id=product.id)

            for img_str in cropped_images_data:
                if not save_base64_image(img_str, "val_check"):
                    messages.error(request, "Invalid or corrupted image format detected.")
                    return redirect('admin_product_edit', product_id=product.id)

        uploaded_files = request.FILES.getlist("images") or request.FILES.getlist("image")
        for file in uploaded_files:
            if not is_valid_image_file(file):
                messages.error(request, "Invalid file format. Only JPG, PNG, WEBP, and AVIF image files are allowed.")
                return redirect('admin_product_edit', product_id=product.id)

        with transaction.atomic():
            product.name = request.POST.get("name")
            product.description = request.POST.get("description")
            if not product.has_active_variants:
                product.price = request.POST.get("price") or product.price
                product.stock = request.POST.get("stock") or product.stock
            product.category = category
            product.is_active = "is_active" in request.POST
            product.highlights = request.POST.get("highlights", "").strip()
            product.brand = request.POST.get("brand", "").strip()
            
            offer_val = request.POST.get("offer_id") or request.POST.get("offer")
            if offer_val and str(offer_val).isdigit():
                product.product_offer = ProductOffer.objects.filter(id=offer_val, is_active=True).first()
                product.offer = product.product_offer.name if product.product_offer else ""
            else:
                product.product_offer = None
                product.offer = ""

            product.save()

            if product.has_active_variants:
                product.sync_stock_from_variants()
                primary_var = product.variants.filter(is_active=True, is_deleted=False).first()
                if primary_var and primary_var.price:
                    Product.objects.filter(id=product.id).update(price=primary_var.price)

            # Handle updating or adding new images if any are uploaded
            if cropped_images_data:
                # Delete old images only when new set is valid and saving
                product.images.all().delete()
                for i, img_str in enumerate(cropped_images_data):
                    image_file = save_base64_image(img_str, f"{product.id}_image_{i}")
                    if image_file:
                        ProductImage.objects.create(product=product, image=image_file)

        messages.success(request, "Product updated successfully!")
        return redirect("admin_products")

    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_deleted=False, status='ACTIVE').order_by('name')
    active_offers = ProductOffer.objects.filter(is_active=True).order_by('name')
    variants = product.variants.filter(is_deleted=False).order_by('id')
    return render(request, "admin_panel/products/edit_product.html", {
        "product": product,
        "variants": variants,
        "categories": categories,
        "brands": brands,
        "active_offers": active_offers,
        "admin_name": request.user.fullname
    })


@admin_required
def admin_product_delete_view(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        product.is_deleted = True
        product.save()
        messages.success(request, "Product deleted successfully!")
    return redirect("admin_products")


@admin_required
def admin_product_detail_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_deleted=False)
    variants = product.variants.filter(is_deleted=False).order_by('id')
    active_variants = variants.filter(is_active=True)
    images = list(product.images.all())

    # Fallback to first variant or active variant (every product is viewed as a variant)
    initial_variant = active_variants.first() or variants.first()

    # Sync product.price in DB to variant price if out of sync
    if initial_variant and initial_variant.price and product.price != initial_variant.price:
        Product.objects.filter(id=product.id).update(price=initial_variant.price)
        product.price = initial_variant.price

    # Collect all visual assets (product images + variant images)
    all_visual_assets = []
    for img in images:
        all_visual_assets.append({
            'url': img.image.url,
            'title': f"{product.name} Main",
            'type': 'Product'
        })
    for var in variants:
        for v_img in var.images.all():
            all_visual_assets.append({
                'url': v_img.image.url,
                'title': f"{var.name}",
                'type': 'Variant'
            })

    # Highlights & Specs parsing
    highlights_list = []
    if product.highlights:
        highlights_list = [line.strip() for line in product.highlights.splitlines() if line.strip()]

    # Calculate pricing based on initial variant (no base product pricing)
    category = product.category
    has_discount = False
    discount_pct = 0

    if initial_variant and initial_variant.price:
        var_price = float(initial_variant.price)
    else:
        var_price = float(product.price)

    original_mrp = var_price
    final_price = var_price

    if category and getattr(category, 'is_offer_active', False) and getattr(category, 'discount', 0) > 0:
        has_discount = True
        discount_pct = category.discount
        final_price = round(original_mrp - (original_mrp * discount_pct / 100), 2)

    # Reviews
    reviews = product.reviews.all().order_by('-created_at')
    total_reviews = reviews.count()
    avg_rating = product.average_rating
    latest_review = reviews.first()

    # Generate professional SKU
    brand_code = (product.brand or 'ZTR').replace(' ', '').upper()[:4]
    cat_code = (category.name or 'GEN').replace(' ', '').upper()[:2]
    base_sku = f"{brand_code}-{cat_code}-{product.created_at.year if product.created_at else '2026'}-{product.id:04d}"
    initial_sku = f"{base_sku}-V{initial_variant.id:02d}" if initial_variant else base_sku

    # Initial image & visual assets
    initial_image = None
    initial_variant_images = []
    if initial_variant and initial_variant.images.exists():
        initial_variant_images = [img.image.url for img in initial_variant.images.all()]
        initial_image = initial_variant_images[0]
    elif images:
        initial_image = images[0].image.url
    else:
        initial_image = 'https://images.unsplash.com/photo-1510915361894-db8b60106cb1?w=800&q=80'

    # Build rich variant dataset for interactive client-side switching
    base_image_urls = [img.image.url for img in images]
    if not base_image_urls:
        base_image_urls = ['https://images.unsplash.com/photo-1510915361894-db8b60106cb1?w=800&q=80']

    variants_dict = {}
    for var in variants:
        v_imgs = [v_img.image.url for v_img in var.images.all()]
        if not v_imgs:
            v_imgs = base_image_urls

        v_price = float(var.price) if var.price else float(product.price)
        if has_discount and discount_pct > 0:
            var_mrp = v_price
            var_final = round(v_price - (v_price * discount_pct / 100), 2)
        else:
            var_mrp = v_price
            var_final = v_price

        var_sku = f"{base_sku}-V{var.id:02d}"

        variants_dict[str(var.id)] = {
            'id': str(var.id),
            'name': var.name,
            'color_code': var.color_code,
            'stock': var.stock,
            'is_active': var.is_active,
            'final_price': var_final,
            'original_mrp': var_mrp,
            'has_discount': has_discount,
            'discount_pct': discount_pct,
            'sku': var_sku,
            'images': v_imgs,
            'title': f"{product.name} — {var.name}",
        }

    context = {
        "product": product,
        "variants": variants,
        "active_variants": active_variants,
        "initial_variant": initial_variant,
        "initial_sku": initial_sku,
        "initial_image": initial_image,
        "initial_variant_images": initial_variant_images,
        "images": images,
        "all_visual_assets": all_visual_assets,
        "highlights_list": highlights_list,
        "original_mrp": original_mrp,
        "final_price": final_price,
        "has_discount": has_discount,
        "discount_pct": discount_pct,
        "reviews": reviews,
        "total_reviews": total_reviews,
        "avg_rating": avg_rating,
        "latest_review": latest_review,
        "sku": initial_sku,
        "variants_json": json.dumps(variants_dict),
        "admin_name": getattr(request.user, 'fullname', '') or getattr(request.user, 'username', '') or 'Admin',
    }
    return render(request, "admin_panel/products/product_detail.html", context)


@admin_required
def admin_product_toggle_view(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id, is_deleted=False)
        product.is_active = not product.is_active
        product.save()
        status_str = "listed and active" if product.is_active else "unlisted and hidden"
        messages.success(request, f"Product '{product.name}' is now {status_str}!")
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url and 'products' in next_url:
            return redirect(next_url)
        return redirect('admin_product_detail', product_id=product.id)
    return redirect('admin_products')


@admin_required
def admin_product_variants_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_deleted=False)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        color_code = request.POST.get("color_code", "").strip()
        price = request.POST.get("price", "").strip()
        stock = request.POST.get("stock", "").strip()
        sku = request.POST.get("sku", "").strip() or None

        if not name or not color_code or not stock:
            messages.error(request, "Please fill in all required fields.")
            return redirect('admin_product_variants', product_id=product.id)

        try:
            stock = int(stock)
            if stock < 0:
                raise ValueError()
        except ValueError:
            messages.error(request, "Stock must be a non-negative integer.")
            return redirect('admin_product_variants', product_id=product.id)

        if price:
            try:
                price = float(price)
                if price <= 0:
                    raise ValueError()
            except ValueError:
                messages.error(request, "Price must be a positive number.")
                return redirect('admin_product_variants', product_id=product.id)
        else:
            price = None

        if sku:
            if ProductVariant.objects.filter(sku__iexact=sku).exists():
                messages.error(request, f"SKU '{sku}' is already in use. Please enter a unique SKU or leave it blank.")
                return redirect('admin_product_variants', product_id=product.id)

        # EXTRACT IMAGES (Base64 cropped strings or standard files)
        variant_images_data = request.POST.getlist("images")
        is_base64 = len(variant_images_data) > 0
        img_list = variant_images_data if is_base64 else request.FILES.getlist("images")

        if len(img_list) < 3 or len(img_list) > 5:
            messages.error(request, "YOU MUST UPLOAD AND CROP AT LEAST 3 IMAGES AND MAXIMUM 5 IMAGES.")
            return redirect('admin_product_variants', product_id=product.id)

        with transaction.atomic():
            variant = ProductVariant.objects.create(
                product=product,
                name=name,
                color_code=color_code,
                price=price,
                stock=stock,
                sku=sku
            )

            for i, img in enumerate(img_list):
                if is_base64:
                    image_file = save_base64_image(img, f"variant_{variant.id}_image_{i}")
                else:
                    image_file = img

                if image_file:
                    VariantImage.objects.create(variant=variant, image=image_file)

            product.sync_stock_from_variants()
            if price and (not product.price or product.price <= 0):
                Product.objects.filter(id=product.id).update(price=price)

        messages.success(request, "Product variant added successfully!")
        return redirect('admin_product_variants', product_id=product.id)

    variants = product.variants.filter(is_deleted=False)
    return render(request, "admin_panel/products/variants.html", {
        "product": product,
        "variants": variants,
        "admin_name": request.user.fullname
    })


@admin_required
def admin_variant_delete_view(request, variant_id):
    if request.method == "POST":
        variant = get_object_or_404(ProductVariant, id=variant_id, is_deleted=False)
        variant.is_deleted = True
        variant.save()
        variant.product.sync_stock_from_variants()
        messages.success(request, "Product variant deleted successfully!")
        return redirect('admin_product_variants', product_id=variant.product.id)
    return redirect('admin_products')


@admin_required
def admin_variant_edit_view(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id, is_deleted=False)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        color_code = request.POST.get("color_code", "").strip()
        price = request.POST.get("price", "").strip()
        stock = request.POST.get("stock", "").strip()
        sku = request.POST.get("sku", "").strip() or None

        if not name or not color_code or stock == "":
            messages.error(request, "Please fill in all required fields.")
            return redirect('admin_product_variants', product_id=variant.product.id)

        try:
            stock = int(stock)
            if stock < 0:
                raise ValueError()
        except ValueError:
            messages.error(request, "Stock must be a non-negative integer.")
            return redirect('admin_product_variants', product_id=variant.product.id)

        if price:
            try:
                price = float(price)
                if price <= 0:
                    raise ValueError()
            except ValueError:
                messages.error(request, "Price must be a positive number.")
                return redirect('admin_product_variants', product_id=variant.product.id)
        else:
            price = None

        if sku:
            if ProductVariant.objects.filter(sku__iexact=sku).exclude(id=variant.id).exists():
                messages.error(request, f"SKU '{sku}' is already in use by another variant.")
                return redirect('admin_product_variants', product_id=variant.product.id)

        with transaction.atomic():
            # Validate final image count before applying changes
            delete_image_ids = request.POST.getlist("delete_image_ids")
            variant_images_data = request.POST.getlist("images")
            is_base64 = len(variant_images_data) > 0
            img_list = variant_images_data if is_base64 else request.FILES.getlist("images")

            existing_count = variant.images.count()
            total_after = existing_count - len(delete_image_ids) + len(img_list)
            if total_after < 3 or total_after > 5:
                messages.error(request, f"Variant '{variant.name}' must have at least 3 images and maximum 5 images.")
                return redirect('admin_product_variants', product_id=variant.product.id)

            variant.name = name
            variant.color_code = color_code
            variant.price = price
            variant.stock = stock
            if sku:
                variant.sku = sku
            variant.save()

            # Delete specific variant images if requested by admin
            if delete_image_ids:
                VariantImage.objects.filter(id__in=delete_image_ids, variant=variant).delete()

            # Replace specific variant images if requested by admin
            for key, val in request.POST.items():
                if key.startswith("replace_image_") and val:
                    img_id = key.replace("replace_image_", "")
                    try:
                        var_img = VariantImage.objects.get(id=img_id, variant=variant)
                        new_img_file = save_base64_image(val, f"variant_{variant.id}_replaced_{img_id}")
                        if new_img_file:
                            var_img.image = new_img_file
                            var_img.save()
                    except VariantImage.DoesNotExist:
                        pass

            # Handle new added cropped images
            if img_list:
                for i, img in enumerate(img_list):
                    if is_base64:
                        image_file = save_base64_image(img, f"variant_{variant.id}_new_{i}")
                    else:
                        image_file = img

                    if image_file:
                        VariantImage.objects.create(variant=variant, image=image_file)

            variant.product.sync_stock_from_variants()

        messages.success(request, f"Variant '{variant.name}' updated successfully!")
        return redirect('admin_product_variants', product_id=variant.product.id)

    return redirect('admin_product_variants', product_id=variant.product.id)


@admin_required
def admin_variant_image_delete_view(request, image_id):
    if request.method == "POST":
        image = get_object_or_404(VariantImage, id=image_id)
        variant = image.variant
        product_id = variant.product.id

        if variant.images.count() <= 3:
            messages.error(request, "A variant must keep at least 3 images. You cannot delete an image when only 3 images remain.")
        else:
            image.delete()
            messages.success(request, "Variant image deleted successfully!")

        return redirect('admin_product_variants', product_id=product_id)
    return redirect('admin_products')


@admin_required
def admin_variant_toggle_view(request, variant_id):
    if request.method == "POST":
        variant = get_object_or_404(ProductVariant, id=variant_id, is_deleted=False)
        variant.is_active = not variant.is_active
        variant.save()
        variant.product.sync_stock_from_variants()
        status_str = "enabled" if variant.is_active else "disabled"
        messages.success(request, f"Product variant '{variant.name}' has been {status_str} successfully!")
        return redirect('admin_product_variants', product_id=variant.product.id)
    return redirect('admin_products')


@admin_required
def admin_variant_add_select_view(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        if product_id:
            return redirect('admin_product_variants', product_id=product_id)
    products = Product.objects.filter(is_deleted=False).order_by('name')
    return render(request, "admin_panel/products/select_product_for_variant.html", {
        "products": products,
        "admin_name": request.user.fullname
    })
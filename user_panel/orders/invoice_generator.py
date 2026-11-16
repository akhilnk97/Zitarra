import io
from decimal import Decimal
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm


def generate_invoice_pdf(order):
    """
    Generates a high-quality PDF tax invoice for an order.
    Returns bytes of the generated PDF document.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    story = []
    styles = getSampleStyleSheet()

    # Color Palette
    brand_orange = colors.HexColor("#E8500A")
    brand_dark = colors.HexColor("#111111")
    brand_gray = colors.HexColor("#666666")
    bg_light = colors.HexColor("#F9F9F8")
    border_gray = colors.HexColor("#E0E0DC")

    # Typography styles
    brand_title_style = ParagraphStyle(
        'BrandTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=brand_dark,
        leading=24,
        spaceAfter=2,
    )
    brand_sub_style = ParagraphStyle(
        'BrandSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        textColor=brand_gray,
        leading=11,
    )
    invoice_head_style = ParagraphStyle(
        'InvoiceHead',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=brand_orange,
        alignment=2,  # Right aligned
        leading=16,
    )
    invoice_meta_style = ParagraphStyle(
        'InvoiceMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        textColor=brand_dark,
        alignment=2,
        leading=12,
    )
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=brand_dark,
        leading=11,
        textTransform='uppercase',
    )
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        textColor=colors.HexColor("#333333"),
        leading=12,
    )
    bold_body_style = ParagraphStyle(
        'BoldBodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        textColor=brand_dark,
        leading=12,
    )
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        textColor=colors.white,
        leading=10,
    )
    table_header_right = ParagraphStyle(
        'TableHeaderRight',
        parent=table_header_style,
        alignment=2,
    )
    table_cell_right = ParagraphStyle(
        'TableCellRight',
        parent=body_style,
        alignment=2,
    )
    table_cell_bold_right = ParagraphStyle(
        'TableCellBoldRight',
        parent=bold_body_style,
        alignment=2,
    )

    # 1. Header: Brand (Left) & Invoice Meta (Right)
    created_date = order.created_at.strftime('%d %b %Y, %I:%M %p') if order.created_at else ''
    payment_method_label = order.get_payment_method_display() if hasattr(order, 'get_payment_method_display') else order.payment_method

    header_left = [
        Paragraph("ZITARRA", brand_title_style),
        Paragraph("Acoustic Craft & Musical Instruments<br/>Tax Invoice / Bill of Supply", brand_sub_style),
    ]
    header_right = [
        Paragraph("TAX INVOICE", invoice_head_style),
        Spacer(1, 2),
        Paragraph(f"<b>Invoice No:</b> INV-{order.order_id}", invoice_meta_style),
        Paragraph(f"<b>Order Date:</b> {created_date}", invoice_meta_style),
        Paragraph(f"<b>Payment Method:</b> {payment_method_label}", invoice_meta_style),
        Paragraph(f"<b>Payment Status:</b> {order.payment_status}", invoice_meta_style),
    ]

    header_table = Table([[header_left, header_right]], colWidths=[95 * mm, 87 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=brand_orange, spaceBefore=4, spaceAfter=10))

    # 2. Seller and Customer Details
    seller_html = (
        "<b>SOLD & DISPATCHED BY:</b><br/>"
        "<b>Zitarra Technical Audio & Instruments Private Limited</b><br/>"
        "Registered Office: Building 4, Tech Park<br/>"
        "Kochi, Kerala, 682024, India<br/>"
        "GSTIN: 32AAACZ1234F1Z8<br/>"
        "Support: support@zitarra.com"
    )
    customer_html = (
        f"<b>SHIPPED & BILLED TO:</b><br/>"
        f"<b>{order.shipping_full_name}</b><br/>"
        f"{order.shipping_address_line_1}<br/>"
        f"{order.shipping_address_line_2 + '<br/>' if order.shipping_address_line_2 else ''}"
        f"{order.shipping_city}, {order.shipping_state} - {order.shipping_pincode}<br/>"
        f"Phone: {order.shipping_phone}<br/>"
        f"Email: {order.user.email}"
    )

    addresses_table = Table(
        [[Paragraph(seller_html, body_style), Paragraph(customer_html, body_style)]],
        colWidths=[91 * mm, 91 * mm]
    )
    addresses_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_light),
        ('BOX', (0, 0), (-1, -1), 0.5, border_gray),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(addresses_table)
    story.append(Spacer(1, 12))

    # 3. Product Items Table
    active_items = list(order.items.exclude(item_status__in=['CANCELLED', 'RETURNED', 'REFUNDED']))
    if not active_items:
        # Fallback to all items if all were cancelled/returned
        active_items = list(order.items.all())

    table_data = [[
        Paragraph("#", table_header_style),
        Paragraph("Item Description", table_header_style),
        Paragraph("Qty", table_header_right),
        Paragraph("Unit Price", table_header_right),
        Paragraph("Total (INR)", table_header_right),
    ]]

    for idx, item in enumerate(active_items, 1):
        desc = f"<b>{item.product_name}</b>"
        if item.variant_name:
            desc += f"<br/><font size='7.5' color='#666666'>Variant: {item.variant_name}</font>"
        
        table_data.append([
            Paragraph(str(idx), body_style),
            Paragraph(desc, body_style),
            Paragraph(str(item.quantity), table_cell_right),
            Paragraph(f"₹{item.price:,.2f}", table_cell_right),
            Paragraph(f"₹{item.item_subtotal:,.2f}", table_cell_right),
        ])

    items_table = Table(
        table_data,
        colWidths=[10 * mm, 92 * mm, 16 * mm, 32 * mm, 32 * mm]
    )
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), brand_dark),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, border_gray),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    # 4. Calculation Summary Table (Right aligned)
    half_tax = round(Decimal(str(order.tax_amount or '0.00')) / Decimal('2.0'), 2)
    totals_rows = [
        [Paragraph("Items Subtotal:", body_style), Paragraph(f"₹{order.subtotal:,.2f}", table_cell_right)],
        [Paragraph("CGST (2.5%):", body_style), Paragraph(f"₹{half_tax:,.2f}", table_cell_right)],
        [Paragraph("SGST (2.5%):", body_style), Paragraph(f"₹{half_tax:,.2f}", table_cell_right)],
    ]

    if order.shipping_cost and order.shipping_cost > Decimal('0.00'):
        totals_rows.append([Paragraph("Shipping Charges:", body_style), Paragraph(f"₹{order.shipping_cost:,.2f}", table_cell_right)])
    else:
        totals_rows.append([Paragraph("Shipping Charges:", body_style), Paragraph("FREE", table_cell_right)])

    if order.discount_amount and order.discount_amount > Decimal('0.00'):
        coupon_label = f"Promo Discount ({order.coupon_code}):" if order.coupon_code else "Promotional Discount:"
        totals_rows.append([
            Paragraph(coupon_label, body_style),
            Paragraph(f"-₹{order.discount_amount:,.2f}", table_cell_right)
        ])

    total_highlight = ParagraphStyle(
        'TotalHighlight',
        parent=bold_body_style,
        fontSize=11,
        textColor=brand_orange,
        alignment=2,
    )
    totals_rows.append([
        Paragraph("<b>Total Amount Paid:</b>", ParagraphStyle('TotalLabel', parent=bold_body_style, fontSize=10)),
        Paragraph(f"<b>₹{order.total_price:,.2f}</b>", total_highlight)
    ])

    totals_table = Table(totals_rows, colWidths=[55 * mm, 35 * mm], hAlign='RIGHT')
    totals_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, -1), (-1, -1), 1, brand_dark),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 18))

    # 5. Declarations & Footer
    declarations_text = (
        "<b>Declaration:</b><br/>"
        "1. This is an electronically generated official Tax Invoice under the GST regime.<br/>"
        "2. All disputes are subject to Kochi jurisdiction.<br/>"
        "3. Goods once sold can be returned within our stipulated return policy window via your account dashboard."
    )
    story.append(Paragraph(declarations_text, ParagraphStyle('Decl', parent=body_style, fontSize=7.5, textColor=brand_gray, leading=10)))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Thank you for choosing Zitarra. Architectural precision in sonic reproduction.", ParagraphStyle('FooterNote', parent=body_style, fontName='Helvetica-Oblique', fontSize=8, alignment=1, textColor=brand_dark)))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

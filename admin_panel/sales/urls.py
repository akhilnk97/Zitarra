from django.urls import path
from . import views

urlpatterns = [
    path('sales-report/', views.admin_sales_report_view, name='admin_sales_report'),
    path('sales-report/export/pdf/', views.export_sales_report_pdf, name='admin_sales_report_pdf'),
    path('sales-report/export/excel/', views.export_sales_report_excel, name='admin_sales_report_excel'),
]

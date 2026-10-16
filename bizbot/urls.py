from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('voice/sell/', views.voice_sell, name='voice_sell'),
    path('voice/buy/', views.voice_buy, name='voice_buy'),
    path('save/', views.save_transaction, name='save_transaction'),
    path('records/', views.records, name='records'),
    path('delete/<int:pk>/', views.delete_transaction, name='delete_transaction'),
    path('inventory/', views.inventory, name='inventory'),
    path('inventory/add/', views.add_product, name='add_product'),
    path('inventory/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('inventory/delete/<int:pk>/', views.delete_product, name='delete_product'),
    path('export/', views.export_csv, name='export_csv'),
    path('api/products/', views.products_json, name='products_json'),
    path('reset/', views.reset_transactions, name='reset_transactions'),
    # ✅ বাকির routes
    path('baki/', views.baki_list, name='baki_list'),
    path('baki/add/', views.baki_add, name='baki_add'),
    path('baki/delete/<int:pk>/', views.baki_delete, name='baki_delete'),
]
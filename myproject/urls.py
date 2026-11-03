"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from blog import views as blog_views  # Dùng chung 1 tên này cho app blog
from users import views as user_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    
    # 1. Trang chủ lấy 6 sản phẩm mới nhất
    path('', user_views.index, name='index'),

    # 2. Auth (Register / Login / Logout)
    path('register/', user_views.register_view, name='register'),
    path('login/', user_views.login_view, name='user_login'),
    path('logout/', user_views.logout_view, name='custom_logout'),

    # 3. Blog
    path('blog/', blog_views.blog_list, name='blog_list'),
    path('blog/<int:pk>/', blog_views.blog_detail, name='blog_detail'),
    path('ajax-rate/', blog_views.ajax_rate, name='ajax_rate'),
    path('ajax_comment/', blog_views.ajax_comment, name='comment'),

    # 4. Account & Product
    path('account/', user_views.account_view, name='account'),
    path('account/update/', user_views.account_view, name='account_update'),
    path('account/my-product/', user_views.my_product_view, name='my_product'),
    path('account/add-product/', user_views.add_product_view, name='add_product'),
    path('account/edit-product/<int:pk>/', user_views.edit_product_view, name='edit_product'),
    path('account/delete-product/<int:pk>/', user_views.delete_product_view, name='delete_product'),

    path('product-detail/<int:pk>/', user_views.product_detail_view, name='product_detail'),

    path('ajax/add-to-cart/', user_views.add_to_cart_ajax, name='add_to_cart_ajax'),
    path('cart/', user_views.cart_view, name='cart_view'),
    path('cart/update/<int:product_id>/<str:action>/', user_views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/delete/<int:product_id>/', user_views.delete_cart_item, name='delete_cart_item'),

    path('checkout/', user_views.checkout_view, name='checkout'),
    path('search/', user_views.search_product_view, name='search_product'),
    path('search-advanced/', user_views.search_advanced_view, name='search_advanced'),

    path('ajax/filter-price/', user_views.ajax_filter_price, name='ajax_filter_price'),
    
    path('forgot-password/', user_views.forgot_password, name='forgot_password'),
    path('reset-password-confirm/<uidb64>/<token>/', user_views.reset_password_confirm, name='reset_password_confirm'),
    ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
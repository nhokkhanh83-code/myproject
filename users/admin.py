from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.urls import reverse
from .models import Country, Category, Brand, Product, History, UserAccount

# =========================================================
# 1. MENU LIST USER (Hiện all user, cột Level, nút Edit/Xoá)
# =========================================================
@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'get_level', 'is_active', 'date_joined', 'action_buttons')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('-id',)

    # Dùng mark_safe cho HTML tĩnh để tránh lỗi format_html
    @admin.display(description='Level')
    def get_level(self, obj):
        if obj.is_superuser or obj.is_staff:
            return mark_safe(
                '<span style="background-color: #d9534f; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold; font-size: 11px;">Admin</span>'
            )
        return mark_safe(
            '<span style="background-color: #5bc0de; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">Member</span>'
        )

    # Nút bấm Edit và Xóa trực tiếp trên từng dòng
    @admin.display(description='Thao tác')
    def action_buttons(self, obj):
        edit_url = reverse('admin:users_useraccount_change', args=[obj.pk])
        delete_url = reverse('admin:users_useraccount_delete', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="background-color: #f0ad4e; color: white; padding: 3px 8px; border-radius: 3px; margin-right: 5px;">Edit</a>'
            '<a class="button" href="{}" style="background-color: #d9534f; color: white; padding: 3px 8px; border-radius: 3px;">Xoá</a>',
            edit_url, delete_url
        )


# =========================================================
# 2. MENU LIST PRODUCT (Hiện all product, tìm theo tên member, Edit/Xoá)
# =========================================================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'get_member_name', 'price', 'category', 'brand', 'action_buttons')
    list_filter = ('category', 'brand', 'status')
    search_fields = ('user__username', 'name')
    search_help_text = "Tìm kiếm theo tên Member hoặc tên sản phẩm..."
    ordering = ('-id',)

    @admin.display(description='Tên Member')
    def get_member_name(self, obj):
        return obj.user.username if obj.user else 'Ẩn danh'

    @admin.display(description='Thao tác')
    def action_buttons(self, obj):
        edit_url = reverse('admin:users_product_change', args=[obj.pk])
        delete_url = reverse('admin:users_product_delete', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="background-color: #f0ad4e; color: white; padding: 3px 8px; border-radius: 3px; margin-right: 5px;">Edit</a>'
            '<a class="button" href="{}" style="background-color: #d9534f; color: white; padding: 3px 8px; border-radius: 3px;">Xoá</a>',
            edit_url, delete_url
        )


# =========================================================
# 3. MENU HISTORY (Quản lý all thông tin mua hàng)
# =========================================================
@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        return [f.name for f in self.model._meta.fields]

    search_fields = ('name', 'email', 'phone', 'id_user')
    search_help_text = "Tìm đơn hàng theo Tên khách hàng (name), Email hoặc Số điện thoại..."
    ordering = ('-id',)


admin.site.register(Country)
admin.site.register(Category)
admin.site.register(Brand)





# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
# from .models import Country, User,Category,Brand

# class CustomUserAdmin(UserAdmin):
#     fieldsets = UserAdmin.fieldsets + (
#         ('Thông tin quốc gia', {'fields': ('country', 'avatar')}),
#     )
#     add_fieldsets = UserAdmin.add_fieldsets + (
#         ('Thông tin quốc gia', {'fields': ('country', 'avatar')}),
#     )

# class HistoryAdmin(admin.ModelAdmin):
#     search_fields = ('name', 'email', 'phone')
#     list_filter = ('created_at',)

    
# admin.site.register(Country)
# admin.site.register(User, CustomUserAdmin)
# admin.site.register(Category)
# admin.site.register(Brand)

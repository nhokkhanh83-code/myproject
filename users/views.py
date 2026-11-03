import json
import os
import ast

from PIL import Image

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from .forms import UserRegisterForm
from users.models import Country, Category, Brand, Product, History

User = get_user_model()


# =========================================================
# HELPER - PRODUCT IMAGE
# =========================================================

def get_original_images(images_data):
    if not images_data:
        return []

    try:
        images = json.loads(images_data)

        if isinstance(images, list):
            return [
                img for img in images
                if not str(img).startswith(('100_', '200_'))
            ]

    except (json.JSONDecodeError, TypeError):
        return [str(images_data)]

    return []


def get_first_image(product):
    images = get_original_images(product.images)

    if images:
        return images[0]

    return ''


# =========================================================
# REGISTER
# =========================================================

def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            user = form.save(commit=False)

            user.set_password(
                form.cleaned_data['password']
            )

            user.is_superuser = False
            user.is_staff = False

            user.save()

            messages.success(
                request,
                'Đăng ký tài khoản thành công!'
            )

            return redirect('user_login')

    else:
        form = UserRegisterForm()

    return render(
        request,
        'users/register.html',
        {
            'form': form
        }
    )


# =========================================================
# LOGIN
# =========================================================

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(
            request,
            data=request.POST
        )

        if form.is_valid():
            user = form.get_user()

            login(request, user)

            return redirect('index')

    else:
        form = AuthenticationForm()

    return render(
        request,
        'users/login.html',
        {
            'form': form
        }
    )


# =========================================================
# LOGOUT
# =========================================================

def logout_view(request):
    logout(request)

    return redirect('user_login')


# =========================================================
# ACCOUNT
# =========================================================

@login_required(login_url='user_login')
def account_view(request):
    user = request.user

    if request.method == 'POST':

        name = request.POST.get(
            'name',
            ''
        ).strip()

        email = request.POST.get(
            'email',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        )

        address = request.POST.get(
            'address',
            ''
        ).strip()

        country_val = request.POST.get(
            'country',
            ''
        ).strip()

        phone = request.POST.get(
            'phone',
            ''
        ).strip()

        avatar = request.FILES.get('avatar')

        if name:
            user.first_name = name

        # EMAIL
        if email:
            try:
                validate_email(email)

            except ValidationError:
                messages.error(
                    request,
                    'Email không hợp lệ.'
                )
                return redirect('account')

            if User.objects.exclude(
                pk=user.pk
            ).filter(
                email=email
            ).exists():

                messages.error(
                    request,
                    'Email này đã được sử dụng.'
                )

                return redirect('account')

            user.email = email

        # PASSWORD
        if password and password.strip():
            user.set_password(password)

            update_session_auth_hash(
                request,
                user
            )

        if hasattr(user, 'address'):
            user.address = address

        if hasattr(user, 'phone'):
            user.phone = phone

        # COUNTRY
        if hasattr(user, 'country'):

            if country_val:
                try:
                    user.country = Country.objects.get(
                        id=int(country_val)
                    )

                except (ValueError, Country.DoesNotExist):
                    user.country = Country.objects.filter(
                        name=country_val
                    ).first()

            else:
                user.country = None

        if avatar and hasattr(user, 'avatar'):
            user.avatar = avatar

        user.save()

        messages.success(
            request,
            'Cập nhật thông tin thành công!'
        )

        return redirect('account')

    countries = Country.objects.all()

    return render(
        request,
        'account/account.html',
        {
            'user': user,
            'countries': countries,
            'left_menu': 'menuLeftAccount.html',
        }
    )


# =========================================================
# MY PRODUCT
# =========================================================

@login_required(login_url='user_login')
def my_product_view(request):
    products = Product.objects.filter(
        user=request.user
    ).order_by('-id')

    product_list = []

    for product in products:
        product_list.append({
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'first_image': get_first_image(product),
        })

    return render(
        request,
        'account/myproduct.html',
        {
            'products': product_list
        }
    )


# =========================================================
# ADD PRODUCT
# =========================================================

@login_required(login_url='user_login')
def add_product_view(request):
    if request.method == 'POST':

        name = request.POST.get(
            'name',
            ''
        ).strip()

        price = request.POST.get(
            'price',
            ''
        ).strip()

        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')

        status = request.POST.get(
            'status',
            '0'
        )

        sale = request.POST.get(
            'sale_price',
            '0'
        )

        company = request.POST.get(
            'company',
            ''
        ).strip()

        detail = request.POST.get(
            'detail',
            ''
        ).strip()

        files = request.FILES.getlist('images')

        errors = {}

        # NAME
        if not name:
            errors['name'] = (
                'Vui lòng nhập tên sản phẩm.'
            )

        # PRICE
        if not price:
            errors['price'] = (
                'Vui lòng nhập giá.'
            )

        else:
            try:
                price_value = float(price)

                if price_value <= 0:
                    errors['price'] = (
                        'Giá phải lớn hơn 0.'
                    )

            except ValueError:
                errors['price'] = (
                    'Giá không hợp lệ.'
                )

        # CATEGORY
        category = None

        if not category_id:
            errors['category'] = (
                'Vui lòng chọn Category.'
            )

        else:
            try:
                category = Category.objects.get(
                    id=category_id
                )

            except (
                Category.DoesNotExist,
                ValueError,
                TypeError
            ):
                errors['category'] = (
                    'Category không tồn tại.'
                )

        # BRAND
        brand = None

        if not brand_id:
            errors['brand'] = (
                'Vui lòng chọn Brand.'
            )

        else:
            try:
                brand = Brand.objects.get(
                    id=brand_id
                )

            except (
                Brand.DoesNotExist,
                ValueError,
                TypeError
            ):
                errors['brand'] = (
                    'Brand không tồn tại.'
                )

        # STATUS
        try:
            status_value = int(status)

        except (ValueError, TypeError):
            status_value = 0

        # SALE
        sale_value = 0

        if status == '1':
            try:
                sale_value = int(sale)

                if sale_value < 0:
                    errors['sale_price'] = (
                        'Sale không được nhỏ hơn 0.'
                    )

            except (ValueError, TypeError):
                errors['sale_price'] = (
                    'Sale không hợp lệ.'
                )

        # IMAGE
        if not files:
            errors['images'] = (
                'Phải chọn ít nhất một ảnh.'
            )

        elif len(files) > 3:
            errors['images'] = (
                'Tối đa chỉ được upload 3 hình ảnh.'
            )

        else:
            for f in files:

                if f.content_type not in [
                    'image/jpeg',
                    'image/png'
                ]:
                    errors['images'] = (
                        f'File "{f.name}" không phải '
                        'ảnh hợp lệ (jpg/png).'
                    )
                    break

                if f.size > 1024 * 1024:
                    errors['images'] = (
                        f'File "{f.name}" vượt quá '
                        'dung lượng 1MB.'
                    )
                    break

        if errors:
            return JsonResponse(
                {
                    'status': 'error',
                    'errors': errors
                },
                status=400
            )

        # =================================================
        # SAVE IMAGE
        # =================================================

        saved_filenames = []

        save_folder = os.path.join(
            settings.MEDIA_ROOT,
            'products'
        )

        os.makedirs(
            save_folder,
            exist_ok=True
        )
        for f in files:

            clean_name = f.name.replace(
                ' ',
                '_'
            )

            base, ext = os.path.splitext(
                clean_name
            )

            ext = ext.lower()

            original_filename = (
                f'{base}{ext}'
            )

            original_path = os.path.join(
                save_folder,
                original_filename
            )

            # IMAGE GỐC
            with open(
                original_path,
                'wb+'
            ) as dest:
                for chunk in f.chunks():
                    dest.write(chunk)

            saved_filenames.append(
                original_filename
            )

            # THUMBNAIL
            try:
                with Image.open(
                    original_path
                ) as img:

                    for size in [100, 200]:

                        img_copy = img.copy()

                        img_copy.thumbnail(
                            (size, size)
                        )

                        if (
                            ext in ['.jpg', '.jpeg']
                            and img_copy.mode not in ('RGB', 'L')
                        ):
                            img_copy = img_copy.convert(
                                'RGB'
                            )

                        resized_name = (
                            f'{size}_{base}{ext}'
                        )

                        resized_path = os.path.join(
                            save_folder,
                            resized_name
                        )

                        img_copy.save(
                            resized_path
                        )

                        saved_filenames.append(
                            resized_name
                        )

            except Exception as e:
                print(
                    'Lỗi resize ảnh:',
                    e
                )

        # DATABASE
        Product.objects.create(
            user=request.user,
            name=name,
            price=price,
            category=category,
            brand=brand,
            status=status_value,
            sale=sale_value,
            company=company,
            detail=detail,
            images=json.dumps(saved_filenames)
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Thêm sản phẩm thành công!'
        })

    categories = Category.objects.all()
    brands = Brand.objects.all()

    return render(
        request,
        'account/addproduct.html',
        {
            'categories': categories,
            'brands': brands,
        }
    )


# =========================================================
# EDIT PRODUCT
# =========================================================

@login_required(login_url='user_login')
def edit_product_view(request, pk):

    product = get_object_or_404(
        Product,
        pk=pk,
        user=request.user
    )

    old_images_all = []

    if product.images:
        try:
            old_images_all = json.loads(
                product.images
            )

            if not isinstance(
                old_images_all,
                list
            ):
                old_images_all = []

        except (
            json.JSONDecodeError,
            TypeError
        ):
            old_images_all = []

    old_display_images = [
        img
        for img in old_images_all
        if not str(img).startswith(
            ('100_', '200_')
        )
    ]

    if request.method == 'POST':

        name = request.POST.get(
            'name',
            ''
        ).strip()

        price = request.POST.get(
            'price',
            ''
        ).strip()

        category_id = request.POST.get(
            'category'
        )

        brand_id = request.POST.get(
            'brand'
        )

        status = request.POST.get(
            'status',
            '0'
        )

        sale = request.POST.get(
            'sale_price',
            '0'
        )

        company = request.POST.get(
            'company',
            ''
        ).strip()

        detail = request.POST.get(
            'detail',
            ''
        ).strip()

        delete_images = (
            request.POST.getlist(
                'hinhxoa[]'
            )
        )

        new_files = (
            request.FILES.getlist(
                'images'
            )
        )

        errors = {}

        # NAME
        if not name:
            errors['name'] = (
                'Tên sản phẩm không được để trống.'
            )

        # PRICE
        if not price:
            errors['price'] = (
                'Giá không được để trống.'
            )

        else:
            try:
                price_value = float(price)

                if price_value <= 0:
                    errors['price'] = (
                        'Giá phải lớn hơn 0.'
                    )

            except ValueError:
                errors['price'] = (
                    'Giá không hợp lệ.'
                )

        # CATEGORY
        category = None

        if not category_id:
            errors['category'] = (
                'Vui lòng chọn Category.'
            )

        else:
            try:
                category = Category.objects.get(
                    id=category_id
                )

            except (
                Category.DoesNotExist,
                ValueError,
                TypeError
            ):
                errors['category'] = (
                    'Category không tồn tại.'
                )

        # BRAND
        brand = None

        if not brand_id:
            errors['brand'] = (
                'Vui lòng chọn Brand.'
            )

        else:
            try:
                brand = Brand.objects.get(
                    id=brand_id
                )

            except (
                Brand.DoesNotExist,
                ValueError,
                TypeError
            ):
                errors['brand'] = (
                    'Brand không tồn tại.'
                )

        # STATUS
        try:
            status_value = int(status)

        except (ValueError, TypeError):
            status_value = 0

        # SALE
        sale_value = 0

        if status == '1':
            try:
                sale_value = int(sale)

                if sale_value < 0:
                    errors['sale_price'] = (
                        'Sale không được nhỏ hơn 0.'
                    )

            except (
                ValueError,
                TypeError
            ):
                errors['sale_price'] = (
                    'Sale không hợp lệ.'
                )

        # Chỉ xóa ảnh thuộc product
        delete_images = [
            img
            for img in delete_images
            if img in old_display_images
        ]

        remaining_old_count = (
            len(old_display_images)
            - len(delete_images)
        )

        total_images = (
            remaining_old_count
            + len(new_files)
        )

        if total_images > 3:
            errors['images'] = (
                'Tổng số hình ảnh không được vượt quá 3.'
            )

        # NEW IMAGE
        for f in new_files:

            if f.content_type not in [
                'image/jpeg',
                'image/png'
            ]:
                errors['images'] = (
                    f'File "{f.name}" không phải '
                    'ảnh hợp lệ (jpg/png).'
                )
                break

            if f.size > 1024 * 1024:
                errors['images'] = (
                    f'File "{f.name}" vượt quá '
                    'dung lượng 1MB.'
                )
                break

        if errors:
            return JsonResponse(
                {
                    'status': 'error',
                    'errors': errors
                },
                status=400
            )

        save_folder = os.path.join(
            settings.MEDIA_ROOT,
            'products'
        )

        os.makedirs(
            save_folder,
            exist_ok=True
        )

        updated_images_list = list(
            old_images_all
        )

        # =================================================
        # DELETE IMAGE
        # =================================================

        for del_img in delete_images:

            base, ext = os.path.splitext(
                del_img
            )

            related_files = [
                del_img,
                f'100_{base}{ext}',
                f'200_{base}{ext}'
            ]

            for rf in related_files:

                if rf in updated_images_list:
                    updated_images_list.remove(
                        rf
                    )

                file_path = os.path.join(
                    save_folder,
                    rf
                )

                if os.path.exists(
                    file_path
                ):
                    try:
                        os.remove(
                            file_path
                        )

                    except OSError as e:
                        print(
                            'Lỗi xóa ảnh:',
                            e
                        )

        # =================================================
        # ADD NEW IMAGE
        # =================================================

        for f in new_files:

            clean_name = f.name.replace(
                ' ',
                '_'
            )

            base, ext = os.path.splitext(
                clean_name
            )

            ext = ext.lower()

            original_filename = (
                f'{base}{ext}'
            )

            original_path = os.path.join(
                save_folder,
                original_filename
            )

            with open(
                original_path,
                'wb+'
            ) as dest:
                for chunk in f.chunks():
                    dest.write(chunk)

            updated_images_list.append(
                original_filename
            )

            try:
                with Image.open(
                    original_path
                ) as img:

                    for size in [100, 200]:

                        img_copy = img.copy()

                        img_copy.thumbnail(
                            (size, size)
                        )

                        if (
                            ext in ['.jpg', '.jpeg']
                            and img_copy.mode not in ('RGB', 'L')
                        ):
                            img_copy = (
                                img_copy.convert(
                                    'RGB'
                                )
                            )

                        resized_name = (
                            f'{size}_{base}{ext}'
                        )

                        resized_path = os.path.join(
                            save_folder,
                            resized_name
                        )

                        img_copy.save(
                            resized_path
                        )

                        updated_images_list.append(
                            resized_name
                        )

            except Exception as e:
                print(
                    'Lỗi resize ảnh:',
                    e
                )

        # UPDATE
        product.name = name
        product.price = price
        product.category = category
        product.brand = brand
        product.status = status_value
        product.sale = sale_value
        product.company = company
        product.detail = detail

        product.images = json.dumps(
            updated_images_list
        )

        product.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Cập nhật sản phẩm thành công!'
        })
    categories = Category.objects.all()
    brands = Brand.objects.all()

    return render(
        request,
        'account/editproduct.html',
        {
            'product': product,
            'categories': categories,
            'brands': brands,
            'old_images': old_display_images,
        }
    )


# =========================================================
# HOME
# =========================================================

def index(request):

    products = Product.objects.all().order_by(
        '-id'
    )[:6]

    latest_products = []

    for p in products:
        latest_products.append({
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'status': p.status,
            'sale': p.sale,
            'image': get_first_image(p),
        })

    return render(
        request,
        'index.html',
        {
            'latest_products': latest_products
        }
    )


# =========================================================
# DELETE PRODUCT
# =========================================================

@login_required(login_url='user_login')
def delete_product_view(request, pk):

    product = get_object_or_404(
        Product,
        pk=pk,
        user=request.user
    )

    if product.images:
        try:
            image_list = json.loads(
                product.images
            )

            if isinstance(
                image_list,
                list
            ):

                save_folder = os.path.join(
                    settings.MEDIA_ROOT,
                    'products'
                )

                for img_name in image_list:

                    file_path = os.path.join(
                        save_folder,
                        str(img_name)
                    )

                    if os.path.exists(
                        file_path
                    ):
                        try:
                            os.remove(
                                file_path
                            )

                        except OSError as e:
                            print(
                                'Lỗi xóa file:',
                                e
                            )

        except (
            json.JSONDecodeError,
            TypeError
        ):
            pass

    product.delete()

    messages.success(
        request,
        'Xóa sản phẩm thành công!'
    )

    return redirect(
        'my_product'
    )


# =========================================================
# PRODUCT DETAIL
# =========================================================

def product_detail_view(request, pk):

    product = get_object_or_404(
        Product,
        pk=pk
    )

    image_list = get_original_images(
        product.images
    )

    first_image = ''

    if image_list:
        first_image = image_list[0]

    product.image_list = image_list
    product.first_image = first_image

    return render(
        request,
        'account/productdetail.html',
        {
            'product': product,
            'img_list': image_list,
            'first_image': first_image,
        }
    )


# =========================================================
# ADD TO CART
# =========================================================

def add_to_cart(request):
    # Lấy product_id và qty từ AJAX gửi lên
    product_id = (
        request.POST.get('product_id')
        or request.GET.get('product_id')
    )

    # 1. BẮT BUỘC: Lấy đúng số lượng từ input gửi lên, ép kiểu int
    qty = int(
        request.POST.get('qty')
        or request.GET.get('qty')
        or 1
    )

    cart = request.session.get('cart', {})
    p_id = str(product_id)

    if p_id in cart:
        # LỖI CŨ CÓ THỂ LÀ: cart[p_id]['quantity'] += 1
        # SỬA THÀNH: cộng thêm đúng số lượng 'qty'
        cart[p_id]['quantity'] += qty

    else:
        product = Product.objects.get(id=product_id)

        cart[p_id] = {
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
            'image': str(product.image) if product.image else '',
            # LỖI CŨ CÓ THỂ LÀ: 'quantity': 1
            # SỬA THÀNH: lưu đúng số lượng 'qty' vừa nhập
            'quantity': qty,
        }

    # Bắt buộc có dòng này để Django lưu session xuống database/cookie
    request.session['cart'] = cart
    request.session.modified = True

    # Tính tổng số lượng trả về cho Header
    total_qty = sum(
        item.get('quantity', 0)
        for item in cart.values()
    )

    return JsonResponse({
        'status': 'success',
        'total_qty': total_qty,
    })


@require_POST
def add_to_cart_ajax(request):

    if request.method == 'POST':

        product_id = request.POST.get(
            'product_id'
        )

        try:
            quantity = int(
                request.POST.get(
                    'quantity',
                    1
                )
            )

        except (ValueError, TypeError):
            quantity = 1

        if not product_id:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': 'Thiếu ID sản phẩm'
                },
                status=400
            )

        try:
            product = Product.objects.get(
                id=product_id
            )

        except Product.DoesNotExist:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': 'Sản phẩm không tồn tại'
                },
                status=404
            )

        cart = request.session.get(
            'cart',
            {}
        )

        p_id = str(product.id)

        # Lấy tên file ảnh đầu tiên chính xác
        first_image = ''

        if hasattr(product, 'images') and product.images:

            raw_imgs = product.images

            # Nếu lưu dạng string của list
            if isinstance(raw_imgs, str):

                try:
                    raw_imgs = ast.literal_eval(
                        raw_imgs
                    )

                except Exception:
                    try:
                        raw_imgs = json.loads(
                            raw_imgs.replace(
                                "'",
                                '"'
                            )
                        )

                    except Exception:
                        raw_imgs = [raw_imgs]

            if (
                isinstance(
                    raw_imgs,
                    (list, tuple)
                )
                and len(raw_imgs) > 0
            ):
                first_image = str(
                    raw_imgs[0]
                ).strip(" '\"[]")

            else:
                first_image = str(
                    raw_imgs
                ).strip(" '\"[]")

        if p_id in cart:

            cart[p_id]['quantity'] = (
                cart[p_id].get(
                    'quantity',
                    0
                ) + quantity
            )

            # Cập nhật lại đường dẫn ảnh mới
            cart[p_id]['image'] = first_image

        else:

            cart[p_id] = {
                'id': product.id,
                'name': product.name,
                'price': float(product.price),
                'image': first_image,
                'quantity': quantity,
            }

        request.session['cart'] = cart
        request.session.modified = True

        total_quantity = sum(
            item.get('quantity', 0)
            for item in cart.values()
        )

        return JsonResponse({
            'status': 'success',
            'total_quantity': total_quantity
        })

    return JsonResponse(
        {
            'status': 'error',
            'message': 'Phương thức không hợp lệ'
        },
        status=405
    )


# =========================================================
# CART
# =========================================================

def cart_view(request):

    cart = request.session.get(
        'cart',
        {}
    )

    cart_items = []
    grand_total = 0

    for item_id, item_data in cart.items():

        try:
            price = float(
                item_data.get(
                    'price',
                    0
                )
            )

            quantity = int(
                item_data.get(
                    'quantity',
                    0
                )
            )

        except (
            ValueError,
            TypeError
        ):
            continue

        subtotal = (
            price * quantity
        )

        grand_total += subtotal

        cart_items.append({
            'id': item_data.get('id'),
            'name': item_data.get(
                'name',
                ''
            ),
            'price': price,
            'image': item_data.get(
                'image',
                ''
            ),
            'quantity': quantity,
            'subtotal': subtotal,
        })

    return render(
        request,
        'account/cart.html',
        {
            'cart_items': cart_items,
            'grand_total': grand_total,
            'hide_menu_left': True,
        }
    )


# =========================================================
# UPDATE CART
# =========================================================

def update_cart_quantity(
    request,
    product_id,
    action
):

    cart = request.session.get(
        'cart',
        {}
    )

    product_id_str = str(
        product_id
    )

    if product_id_str in cart:

        if action == 'up':

            cart[
                product_id_str
            ]['quantity'] += 1

        elif action == 'down':

            cart[
                product_id_str
            ]['quantity'] -= 1

            if cart[
                product_id_str
            ]['quantity'] <= 0:

                del cart[
                    product_id_str
                ]

        request.session['cart'] = cart
        request.session.modified = True

    return redirect(
        'cart_view'
    )


# =========================================================
# DELETE CART
# =========================================================

def delete_cart_item(
    request,
    product_id
):

    cart = request.session.get(
        'cart',
        {}
    )

    product_id_str = str(
        product_id
    )

    if product_id_str in cart:

        del cart[
            product_id_str
        ]

        request.session['cart'] = cart
        request.session.modified = True

    return redirect(
        'cart_view'
    )


# =========================================================
# SEND ORDER EMAIL
# =========================================================

def send_order_email(
    user_name,
    user_email,
    user_phone,
    cart_items,
    grand_total
):

    if not user_email:
        raise ValueError(
            'Không có email người nhận.'
        )

    subject = (
        'Xác nhận đơn hàng từ E-Shopper!'
    )

    from_email = (
        settings.DEFAULT_FROM_EMAIL
    )

    shipping_fee = (
        2 if grand_total > 0 else 0
    )

    final_total = (
        grand_total + shipping_fee
    )

    context = {
        'user_name': user_name,
        'user_email': user_email,
        'user_phone': user_phone,
        'cart_items': cart_items,
        'grand_total': grand_total,
        'shipping_fee': shipping_fee,
        'final_total': final_total,
    }

    text_content = (
        f'Chào {user_name}, '
        'cảm ơn bạn đã mua hàng tại E-Shopper. '
        f'Tổng tiền: ${final_total:.2f}'
    )

    html_content = render_to_string(
        'emails/order_email.html',
        context
    )

    msg = EmailMultiAlternatives(
        subject,
        text_content,
        from_email,
        [user_email]
    )

    msg.attach_alternative(
        html_content,
        'text/html'
    )

    msg.send(
        fail_silently=False
    )
# =========================================================
# CHECKOUT
# =========================================================

def checkout_view(request):

    cart = request.session.get(
        'cart',
        {}
    )

    cart_items = []
    grand_total = 0

    for product_id, item_data in cart.items():

        try:
            product = Product.objects.get(
                id=product_id
            )

            qty = int(
                item_data.get(
                    'quantity',
                    1
                )
            )

            if qty <= 0:
                continue

            subtotal = (
                float(product.price)
                * qty
            )

            grand_total += subtotal

            cart_items.append({
                'id': product.id,
                'name': product.name,
                'price': product.price,
                'image': get_first_image(product),
                'quantity': qty,
                'subtotal': subtotal,
            })

        except (
            Product.DoesNotExist,
            ValueError,
            TypeError
        ):
            continue

    # SHIPPING
    shipping_fee = (
        2 if grand_total > 0 else 0
    )

    final_total = (
        grand_total + shipping_fee
    )

    # =====================================================
    # POST ORDER
    # =====================================================

    if request.method == 'POST':

        if not cart_items:

            messages.error(
                request,
                'Giỏ hàng của bạn đang trống!'
            )

            return redirect(
                'cart_view'
            )

        # USER ĐÃ LOGIN
        if request.user.is_authenticated:

            current_user = request.user

            user_id = current_user.id

            user_name = (
                getattr(
                    current_user,
                    'first_name',
                    ''
                )
                or current_user.username
            )

            user_email = current_user.email

            user_phone = (
                getattr(
                    current_user,
                    'phone',
                    ''
                )
                or request.POST.get(
                    'phone',
                    ''
                )
            )

            if not user_email:

                messages.error(
                    request,
                    'Tài khoản chưa có Email.'
                )

                return redirect(
                    'checkout'
                )

        # =================================================
        # USER CHƯA LOGIN
        # =================================================

        else:

            username = request.POST.get(
                'username',
                ''
            ).strip()

            email = request.POST.get(
                'email',
                ''
            ).strip()

            password = request.POST.get(
                'password',
                ''
            ).strip()

            confirm_password = request.POST.get(
                'confirm_password',
                ''
            ).strip()

            phone = request.POST.get(
                'phone',
                ''
            ).strip()

            address = request.POST.get(
                'address',
                ''
            ).strip()

            if (
                not username
                or not email
                or not password
            ):

                messages.error(
                    request,
                    'Vui lòng nhập đầy đủ thông tin!'
                )

                return redirect(
                    'checkout'
                )

            try:
                validate_email(
                    email
                )

            except ValidationError:

                messages.error(
                    request,
                    'Email không hợp lệ!'
                )

                return redirect(
                    'checkout'
                )

            if password != confirm_password:

                messages.error(
                    request,
                    'Mật khẩu xác nhận không khớp!'
                )

                return redirect(
                    'checkout'
                )

            if User.objects.filter(
                email=email
            ).exists():

                messages.error(
                    request,
                    'Email đã tồn tại. '
                    'Vui lòng đăng nhập!'
                )

                return redirect(
                    'user_login'
                )

            if User.objects.filter(
                username=username
            ).exists():

                messages.error(
                    request,
                    'Username đã tồn tại.'
                )

                return redirect(
                    'user_login'
                )

            # CREATE USER
            new_user = User.objects.create(
                username=username,
                email=email,
                password=make_password(
                    password
                )
            )

            if hasattr(
                new_user,
                'phone'
            ):
                new_user.phone = phone

            if hasattr(
                new_user,
                'address'
            ):
                new_user.address = address

            new_user.save()

            login(
                request,
                new_user
            )

            user_id = new_user.id
            user_name = new_user.username
            user_email = new_user.email
            user_phone = phone

        # =================================================
        # HISTORY
        # =================================================

        History.objects.create(
            email=user_email,
            phone=user_phone,
            name=user_name,
            id_user=user_id,
            price=final_total
        )

        # EMAIL
        try:

            send_order_email(
                user_name,
                user_email,
                user_phone,
                cart_items,
                grand_total
            )

        except Exception as e:
            print(
                'Lỗi gửi mail:',
                e
            )

        # CLEAR CART
        request.session['cart'] = {}
        request.session.modified = True

        messages.success(
            request,
            (
                'Đặt hàng thành công! '
                f'Thông tin đã gửi về {user_email}'
            )
        )

        return redirect(
            'checkout'
        )

    return render(
        request,
        'account/checkout.html',
        {
            'cart_items': cart_items,
            'grand_total': grand_total,
            'shipping_fee': shipping_fee,
            'final_total': final_total,
            'hide_menu_left': True,
        }
    )


# =========================================================
# SEARCH CƠ BẢN
# =========================================================

def search_product_view(request):

    keyword = request.GET.get(
        'keyword',
        ''
    ).strip()

    if keyword:

        products = Product.objects.filter(
            name__icontains=keyword
        ).order_by('-id')

    else:

        products = Product.objects.all().order_by(
            '-id'
        )

    search_products = []

    for p in products:

        search_products.append({
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'status': p.status,
            'sale': p.sale,
            'image': get_first_image(p),
        })

    return render(
        request,
        'search.html',
        {
            'products': search_products,
            'keyword': keyword,
            'total_results': len(search_products),
        }
    )


# =========================================================
# HELPER SEARCH ADVANCED
# =========================================================

def filter_products(request):

    name = request.GET.get(
        'name',
        ''
    ).strip()

    price_range = request.GET.get(
        'price',
        ''
    ).strip()

    category_id = request.GET.get(
        'category',
        ''
    ).strip()

    brand_id = request.GET.get(
        'brand',
        ''
    ).strip()

    status = request.GET.get(
        'status',
        ''
    ).strip()

    products_query = (
        Product.objects
        .all()
        .order_by('-id')
    )

    # NAME
    if name:
        products_query = (
            products_query.filter(
                name__icontains=name
            )
        )

    # PRICE BETWEEN
    if price_range:

        try:

            min_price, max_price = (
                price_range.split(
                    '-',
                    1
                )
            )

            products_query = (
                products_query.filter(
                    price__range=(
                        float(min_price),
                        float(max_price)
                    )
                )
            )

        except (
            ValueError,
            TypeError
        ):
            pass

    # CATEGORY
    if category_id:

        products_query = (
            products_query.filter(
                category_id=category_id
            )
        )

    # BRAND
    if brand_id:

        products_query = (
            products_query.filter(
                brand_id=brand_id
            )
        )

    # STATUS
    if status in ['0', '1']:

        products_query = (
            products_query.filter(
                status=int(status)
            )
        )

    return {
        'queryset': products_query,
        'name': name,
        'price': price_range,
        'category': category_id,
        'brand': brand_id,
        'status': status,
    }


# =========================================================
# HELPER BUILD SEARCH CONTEXT
# =========================================================

def build_search_context(request):

    filtered = filter_products(
        request
    )

    products_query = filtered[
        'queryset'
    ]

    # 6 PRODUCT / PAGE
    paginator = Paginator(
        products_query,
        6
    )

    page_number = request.GET.get(
        'page'
    )

    page_obj = paginator.get_page(
        page_number
    )

    product_list = []

    for p in page_obj:

        product_list.append({
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'status': p.status,
            'sale': p.sale,
            'image': get_first_image(p),
        })

    # Giữ filter khi chuyển page
    query_params = request.GET.copy()

    if 'page' in query_params:
        query_params.pop(
            'page'
        )

    # LẤY CATEGORY + BRAND TỪ DATABASE
    categories = (
        Category.objects
        .all()
        .order_by('name')
    )

    brands = (
        Brand.objects
        .all()
        .order_by('name')
    )

    return {
        'products': product_list,
        'page_obj': page_obj,
        'categories': categories,
        'brands': brands,
        'query_string': query_params.urlencode(),
        'selected_name': filtered['name'],
        'selected_price': filtered['price'],
        'selected_category': filtered['category'],
        'selected_brand': filtered['brand'],
        'selected_status': filtered['status'],
    }


# =========================================================
# SEARCH ADVANCED PAGE
# =========================================================

def search_advanced_view(request):

    # Lấy dữ liệu từ URL
    name = request.GET.get('name', '').strip()
    price_range = request.GET.get('price', '').strip()
    category_id = request.GET.get('category', '').strip()
    brand_id = request.GET.get('brand', '').strip()
    status = request.GET.get('status', '').strip()

    # Lấy tất cả sản phẩm
    products_query = Product.objects.all().order_by('-id')

    # =====================================================
    # 1. SEARCH NAME
    # SQL LIKE
    # =====================================================

    if name:
        products_query = products_query.filter(
            name__icontains=name
        )

    # =====================================================
    # 2. SEARCH PRICE
    # Tương đương SQL BETWEEN
    # =====================================================

    if price_range:
        try:
            min_price, max_price = price_range.split('-', 1)

            products_query = products_query.filter(
                price__range=(
                    float(min_price),
                    float(max_price)
                )
            )

        except (ValueError, TypeError):
            pass

    # =====================================================
    # 3. SEARCH CATEGORY
    # =====================================================

    if category_id:
        products_query = products_query.filter(
            category_id=category_id
        )

    # =====================================================
    # 4. SEARCH BRAND
    # =====================================================

    if brand_id:
        products_query = products_query.filter(
            brand_id=brand_id
        )

    # =====================================================
    # 5. SEARCH STATUS
    # 0 = NEW
    # 1 = SALE
    # =====================================================

    if status in ['0', '1']:
        products_query = products_query.filter(
            status=int(status)
        )

    # =====================================================
    # 6. PAGINATION
    # =====================================================

    paginator = Paginator(
        products_query,
        6
    )

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(
        page_number
    )

    # =====================================================
    # 7. XỬ LÝ PRODUCT + IMAGE
    # =====================================================

    product_list = []

    for p in page_obj:

        first_img = get_first_image(p)

        product_list.append({
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'status': p.status,
            'sale': p.sale,
            'image': first_img,
        })
    # =====================================================
    # 8. GIỮ FILTER KHI CHUYỂN PAGE
    # =====================================================

    query_params = request.GET.copy()

    if 'page' in query_params:
        query_params.pop('page')

    # =====================================================
    # 9. QUAN TRỌNG
    # LẤY CATEGORY + BRAND TỪ DATABASE
    # =====================================================

    categories = Category.objects.all()

    brands = Brand.objects.all()

    # =====================================================
    # 10. GỬI SANG search_advanced.html
    # =====================================================

    context = {
        'products': product_list,
        'page_obj': page_obj,

        'categories': categories,
        'brands': brands,

        'selected_name': name,
        'selected_price': price_range,
        'selected_category': category_id,
        'selected_brand': brand_id,
        'selected_status': status,

        'query_string': query_params.urlencode(),
    }

    return render(
        request,
        'search_advanced.html',
        context
    )

def ajax_filter_price(request):

    if request.method == 'GET':

        try:
            min_price = float(
                request.GET.get(
                    'min_price',
                    0
                )
            )

            max_price = float(
                request.GET.get(
                    'max_price',
                    600
                )
            )

        except (
            ValueError,
            TypeError
        ):
            min_price, max_price = 0, 600

        products = Product.objects.filter(
            price__gte=min_price,
            price__lte=max_price
        ).order_by('-id')

        product_data = []

        for p in products:

            first_img = ''

            if hasattr(
                p,
                'images'
            ) and p.images:

                raw_imgs = p.images

                if isinstance(
                    raw_imgs,
                    str
                ):

                    try:
                        raw_imgs = ast.literal_eval(
                            raw_imgs
                        )

                    except Exception:

                        try:
                            raw_imgs = json.loads(
                                raw_imgs.replace(
                                    "'",
                                    '"'
                                )
                            )

                        except Exception:
                            raw_imgs = [raw_imgs]

                if (
                    isinstance(
                        raw_imgs,
                        (list, tuple)
                    )
                    and len(raw_imgs) > 0
                ):
                    first_img = str(
                        raw_imgs[0]
                    ).strip(" '\"[]")

                else:
                    first_img = str(
                        raw_imgs
                    ).strip(" '\"[]")

            product_data.append({
                'id': p.id,
                'name': p.name,
                'price': float(p.price),
                'image': first_img
            })

        return JsonResponse({
            'status': 'success',
            'products': product_data
        })

    return JsonResponse(
        {
            'status': 'error',
            'message': 'Invalid request'
        },
        status=400
    )


def forgot_password(request):

    if request.method == 'POST':

        email = request.POST.get(
            'email',
            ''
        ).strip()

        users = User.objects.filter(
            email=email
        )

        if users.exists():

            for user in users:

                token = default_token_generator.make_token(
                    user
                )

                uidb64 = urlsafe_base64_encode(
                    force_bytes(user.pk)
                )

                reset_link = (
                    f"http://127.0.0.1:8000/"
                    f"reset-password-confirm/"
                    f"{uidb64}/{token}/"
                )

                subject = (
                    "Dat lai mat khau - E-Shopper"
                )

                message = (
                    f"Xin chao {user.username},\n\n"
                    f"Nhan vao link sau de dat lai mat khau:\n"
                    f"{reset_link}"
                )

                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False
                    )

                except Exception as e:
                    print(
                        "Loi gui mail:",
                        e
                    )

            return render(
                request,
                'users/forgot_password.html',
                {
                    'success': (
                        'Đã gửi liên kết đặt lại '
                        'mật khẩu vào email của bạn!'
                    )
                }
            )

        else:

            return render(
                request,
                'users/forgot_password.html',
                {
                    'error': (
                        'Email này chưa được '
                        'đăng ký trong hệ thống!'
                    )
                }
            )

    return render(
        request,
        'users/forgot_password.html'
    )


# =========================================================
# RESET PASSWORD
# =========================================================

def reset_password_confirm(
    request,
    uidb64,
    token
):

    try:
        uid = force_str(
            urlsafe_base64_decode(
                uidb64
            )
        )

        user = User.objects.get(
            pk=uid
        )

    except (
        TypeError,
        ValueError,
        OverflowError,
        User.DoesNotExist
    ):
        user = None

    if (
        user is not None
        and default_token_generator.check_token(
            user,
            token
        )
    ):

        if request.method == 'POST':

            new_password = request.POST.get(
                'new_password'
            )

            confirm_password = request.POST.get(
                'confirm_password'
            )

            if (
                new_password
                != confirm_password
            ):
                return render(
                    request,
                    'users/reset_password_confirm.html',
                    {
                        'error': (
                            'Mật khẩu xác nhận '
                            'không khớp!'
                        )
                    }
                )

            if len(new_password) < 6:
                return render(
                    request,
                    'users/reset_password_confirm.html',
                    {
                        'error': (
                            'Mật khẩu phải từ '
                            '6 ký tự trở lên!'
                        )
                    }
                )

            user.set_password(
                new_password
            )

            user.save()

            return render(
                request,
                'users/reset_password_confirm.html',
                {
                    'success': (
                        'Đổi mật khẩu thành công! '
                        'Bạn có thể đăng nhập ngay.'
                    )
                }
            )

        return render(
            request,
            'users/reset_password_confirm.html'
        )

    else:

        return render(
            request,
            'users/reset_password_confirm.html',
            {
                'error': (
                    'Liên kết đã hết hạn '
                    'hoặc không hợp lệ!'
                )
            }
        )
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Avg
from .models import Blog, Rate, Comment
from django.utils.dateformat import format as date_format


def index(request):
    return render(request, 'index.html')


def blog_list(request):
    blogs = Blog.objects.all().order_by('-created_at')
    paginator = Paginator(blogs, 3)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'blog/blog.html', {'page_obj': page_obj})


def blog_detail(request, pk):
    blog = get_object_or_404(Blog, pk=pk)

    avg_query = Rate.objects.filter(blog=blog).aggregate(Avg('rate'))['rate__avg']
    avg_rate = round(avg_query) if avg_query is not None else 0

    vote_count = Rate.objects.filter(blog=blog).count()

    comments = Comment.objects.filter(blog=blog).order_by('created_at')
    comment_count = comments.count()

    return render(request, 'blog/blog_detail.html', {
        'blog': blog,
        'avg_rate': avg_rate,
        'vote_count': vote_count,
        'comments': comments,
        'comment_count': comment_count,
    })


def post_comment(request, pk):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'not_logged_in',
                'message': 'Vui lòng login để cmt!'
            })

        blog = get_object_or_404(Blog, pk=pk)
        cmt_text = request.POST.get('message', '').strip()
        level = int(request.POST.get('level', 0))

        if cmt_text:
            avatar_url = request.user.avatar.url if getattr(request.user, 'avatar', None) else ''

            Comment.objects.create(
                cmt=cmt_text,
                blog=blog,
                user=request.user,
                avatar_user=avatar_url,
                name_user=request.user.username,
                level=level
            )

            return JsonResponse({
                'status': 'success',
                'message': 'Bình luận thành công!'
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Yêu cầu không hợp lệ.'
    })


def ajax_rate(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'not_logged_in',
                'message': 'Vui lòng đăng nhập để đánh giá!'
            })

        blog_id = request.POST.get('blog_id')
        rate_val = request.POST.get('rate')

        if blog_id and rate_val:
            blog = get_object_or_404(Blog, id=blog_id)

            if Rate.objects.filter(blog=blog, user=request.user).exists():
                return JsonResponse({
                    'status': 'already_rated',
                    'message': 'Bạn đã đánh giá bài viết này rồi, không thể đánh giá lại!'
                })

            Rate.objects.create(
                blog=blog,
                user=request.user,
                rate=int(rate_val)
            )

            return JsonResponse({
                'status': 'success',
                'rate': rate_val
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Yêu cầu không hợp lệ.'
    })


def ajax_comment(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'error',
                'message': 'vui long login để cmt'
            })

        blog_id = request.POST.get('blog_id')
        message = request.POST.get('message', '').strip()
        level = request.POST.get('level', 0)

        if not message:
            return JsonResponse({
                'status': 'error',
                'message': 'Vui lòng nhập nội dung!'
            })

        try:
            blog = Blog.objects.get(id=blog_id)
            user = request.user
            name_user = user.username

            avatar_url = '/static/images/blog/man-two.jpg'

            if hasattr(user, 'profile') and user.profile.avatar:
                avatar_url = user.profile.avatar.url

            cmt_obj = Comment.objects.create(
                user=user,
                blog=blog,
                name_user=name_user,
                avatar_user=avatar_url,
                cmt=message,
                level=int(level) if level else 0
            )

            return JsonResponse({
                'status': 'success',
                'message': 'Bình luận thành công!',
                'comment': {
                    'id': cmt_obj.id,
                    'cmt': cmt_obj.cmt,
                    'name_user': cmt_obj.name_user,
                    'avatar_user': cmt_obj.avatar_user,
                    'level': cmt_obj.level,
                    'time': date_format(cmt_obj.created_at, 'h:i A'),
                    'date': date_format(cmt_obj.created_at, 'M d, Y'),
                }
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request'
    }, status=400)
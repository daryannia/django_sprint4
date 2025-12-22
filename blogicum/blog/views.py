from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django import forms
from django.http import Http404
from .models import Category, Post, Comment
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import DeleteView
from django.db.models import Count


class UserEditForm(forms.ModelForm):
    """Форма редактирования профиля пользователя."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']


def get_published_posts():
    """Возвращает QuerySet опубликованных постов."""
    return Post.objects.select_related(
        'category', 'location', 'author'
    ).filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now()
    ).annotate(comment_count=Count('comments')).order_by('-pub_date')


def get_paginated_page(request, queryset, items_per_page=10):
    """Создает пагинацию для QuerySet."""
    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def index(request):
    """Главная страница со списком постов."""
    published_posts = get_published_posts()
    page_obj = get_paginated_page(request, published_posts)
    
    context = {'page_obj': page_obj}
    return render(request, 'blog/index.html', context)


def post_detail(request, post_id):
    """Страница просмотра поста и его комментариев."""
    # Получаем пост
    post = get_object_or_404(
        Post.objects.select_related('category', 'location', 'author'),
        id=post_id
    )

    # Проверяем видимость поста
    is_visible_to_all = (
        post.is_published
        and post.category.is_published
        and post.pub_date <= timezone.now()
    )

    # Если пост не опубликован и пользователь не автор - 404
    if not is_visible_to_all and request.user != post.author:
        raise Http404("Пост не найден")

    # Получаем комментарии
    comments = post.comments.all().order_by('created_at')

    # Обработка формы комментария
    if request.method == 'POST' and request.user.is_authenticated:
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return redirect('blog:post_detail', post_id=post_id)
    else:
        form = CommentForm()

    context = {
        'post': post,
        'comments': comments,
        'form': form,
    }
    return render(request, 'blog/detail.html', context)


def category_posts(request, category_slug):
    """Посты определенной категории."""
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )

    # Получаем посты категории
    post_list = Post.objects.select_related(
        'category', 'location', 'author'
    ).filter(
        category=category,
        is_published=True,
        pub_date__lte=timezone.now()
    ).annotate(comment_count=Count('comments')).order_by('-pub_date')

    page_obj = get_paginated_page(request, post_list)

    context = {'category': category, 'page_obj': page_obj}
    return render(request, 'blog/category.html', context)


def profile(request, username):
    """Страница профиля пользователя."""
    profile_user = get_object_or_404(User, username=username)

    # Определяем, какие посты показывать
    if request.user == profile_user:
        # Автор видит все свои посты
        posts = Post.objects.filter(
            author=profile_user
        ).annotate(comment_count=Count('comments')).order_by('-pub_date')
    else:
        # Другие видят только опубликованные
        posts = Post.objects.filter(
            author=profile_user,
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now()
        ).annotate(comment_count=Count('comments')).order_by('-pub_date')

    page_obj = get_paginated_page(request, posts)

    context = {
        'profile': profile_user,
        'page_obj': page_obj,
    }
    return render(request, 'blog/profile.html', context)


@login_required
def edit_profile(request):
    """Редактирование профиля текущего пользователя."""
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('blog:profile', username=request.user.username)
    else:
        form = UserEditForm(instance=request.user)

    return render(request, 'blog/user.html', {'form': form})


class PostCreateView(LoginRequiredMixin, CreateView):
    """Создание нового поста."""

    model = Post
    template_name = 'blog/create.html'
    fields = ['title', 'text', 'pub_date', 'image', 'category', 'location']

    def form_valid(self, form):
        """Добавляет автора к посту."""
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        """URL после создания поста."""
        return reverse_lazy(
            'blog:profile', kwargs={'username': self.request.user.username}
        )


class PostUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование поста."""

    model = Post
    template_name = 'blog/create.html'
    fields = ['title', 'text', 'pub_date', 'image', 'category', 'location']

    def dispatch(self, request, *args, **kwargs):
        """Проверяет права доступа."""
        if not request.user.is_authenticated:
            return redirect('login')

        self.object = self.get_object()

        if request.user != self.object.author:
            return redirect('blog:post_detail', post_id=self.object.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """URL после редактирования поста."""
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.object.pk}
        )


class CommentForm(forms.ModelForm):
    """Форма комментария."""

    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3}),
        }


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Удаление поста."""

    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'

    def test_func(self):
        """Проверяет авторство."""
        post = self.get_object()
        return self.request.user == post.author

    def get_context_data(self, **kwargs):
        """Добавляет форму комментария в контекст."""
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['deleting_post'] = True
        return context

    def get_success_url(self):
        """URL после удаления поста."""
        return reverse_lazy(
            'blog:profile', kwargs={'username': self.request.user.username}
        )


class CommentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Редактирование комментария."""

    model = Comment
    template_name = 'blog/comment.html'
    fields = ['text']
    pk_url_kwarg = 'pk'
    context_object_name = 'comment'

    def test_func(self):
        """Проверяет авторство комментария."""
        comment = self.get_object()
        return self.request.user == comment.author

    def get_success_url(self):
        """URL после редактирования комментария."""
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.object.post.pk}
        )


class CommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Удаление комментария."""

    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'pk'
    context_object_name = 'comment'

    def test_func(self):
        """Проверяет авторство комментария."""
        comment = self.get_object()
        return self.request.user == comment.author

    def get(self, request, *args, **kwargs):
        """Обрабатывает GET запрос."""
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_success_url(self):
        """URL после удаления комментария."""
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.object.post.pk}
        )


class RegistrationView(CreateView):
    """Регистрация нового пользователя."""

    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('blog:index')

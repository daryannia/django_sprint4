from django.contrib import admin
from blog.models import Category, Location, Post


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'created_at')
    list_editable = ('is_published',)
    search_fields = ('title',)
    list_filter = ('is_published',)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_published', 'created_at')
    list_editable = ('is_published',)
    search_fields = ('name',)
    list_filter = ('is_published',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'is_published',
        'pub_date',
        'author',
        'category',
        'location',
        'created_at',
    )
    list_editable = ('is_published',)
    search_fields = ('title', 'text')
    list_filter = ('category', 'is_published', 'pub_date', 'author')
    readonly_fields = ('created_at',)


admin.site.site_header = 'Панель администрирования Блогикум'
admin.site.site_title = 'Админ-панель Блогикум'
admin.site.index_title = 'Управление контентом'

from django.contrib import admin

from .models import Animal, Placement


class PlacementInline(admin.TabularInline):
    model = Placement
    extra = 0


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "species", "status", "intake_date"]
    list_filter = ["species", "status"]
    search_fields = ["code", "name", "breed"]
    inlines = [PlacementInline]


admin.site.register(Placement)

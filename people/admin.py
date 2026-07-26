from django.contrib import admin

from .models import Application, Household, Person, ResidentPet, Tag


class PersonInline(admin.TabularInline):
    model = Person
    extra = 0


class ResidentPetInline(admin.TabularInline):
    model = ResidentPet
    extra = 0


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ["name", "primary_contact", "email", "city", "is_active"]
    search_fields = ["name", "primary_first_name", "primary_last_name", "email"]
    list_filter = ["is_active", "tags"]
    inlines = [PersonInline, ResidentPetInline]
    filter_horizontal = ["tags"]


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["household", "app_type", "stage", "animal", "created_at"]
    list_filter = ["app_type", "stage"]


admin.site.register(Tag)
admin.site.register(Person)
admin.site.register(ResidentPet)

from django.contrib import admin
from .models import Plan, Subscription

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'currency', 'interval', 'duration_days', 'is_active')
    list_filter = ('interval', 'is_active')
    search_fields = ('name', 'apple_product_id', 'google_product_id')
    ordering = ('name',)
    readonly_fields = ()

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'renewal_date', 'platform')
    list_filter = ('status', 'platform')
    search_fields = ('user__email', 'plan__name', 'latest_receipt_token')
    ordering = ('-start_date',)
    
    actions = ['activate_subscription', 'cancel_subscription']

    def activate_subscription(self, request, queryset):
        """Admin থেকে সাবস্ক্রিপশন active করা যাবে"""
        for sub in queryset:
            sub.activate()
        self.message_user(request, "Selected subscriptions have been activated.")
    activate_subscription.short_description = "Activate selected subscriptions"

    def cancel_subscription(self, request, queryset):
        """Admin থেকে সাবস্ক্রিপশন cancel করা যাবে"""
        updated = queryset.update(status='cancelled', renewal_date=None)
        self.message_user(request, f"{updated} subscription(s) cancelled successfully.")
    cancel_subscription.short_description = "Cancel selected subscriptions"

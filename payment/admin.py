from django.contrib import admin
from django.utils.timezone import now
from datetime import timedelta
from .models import Plan, Subscription

# ---------------------------
# Plan Admin
# ---------------------------
@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'currency', 'interval', 'duration_days', 'is_active')
    list_filter = ('interval', 'is_active', 'currency')
    search_fields = ('name', 'apple_product_id', 'google_product_id')
    ordering = ('name',)
    fieldsets = (
        (None, {
            'fields': ('name', 'price', 'currency', 'interval', 'duration_days', 'is_active')
        }),
        ('Store IDs', {
            'fields': ('apple_product_id', 'google_product_id'),
            'description': "IDs from Apple App Store and Google Play Store"
        }),
    )

# ---------------------------
# Subscription Admin
# ---------------------------
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_plan_name', 'status', 'start_date', 'renewal_date', 'platform', 'is_active_status')
    list_filter = ('status', 'platform', 'plan')
    search_fields = ('user__email', 'user__username', 'latest_receipt_token', 'platform')
    readonly_fields = ('start_date',)
    ordering = ('-start_date',)
    
    actions = ['activate_trial', 'cancel_subscription', 'mark_as_expired']

    def get_plan_name(self, obj):
        return obj.plan.name if obj.plan else "No Plan"
    get_plan_name.short_description = 'Plan'

    def is_active_status(self, obj):
        return obj.is_active_and_valid()
    is_active_status.boolean = True
    is_active_status.short_description = 'Is Valid?'

    # --- Custom Actions ---

    def activate_trial(self, request, queryset):
        """Reset selected subscriptions to a fresh 7-day trial"""
        count = 0
        for sub in queryset:
            sub.start_trial() # Models এ start_trial() মেথড থাকতে হবে
            count += 1
        self.message_user(request, f"{count} subscription(s) reset to 7-day trial.")
    activate_trial.short_description = "Reset to 7-Day Trial"

    def cancel_subscription(self, request, queryset):
        """Immediately cancel subscriptions"""
        updated = queryset.update(status='cancelled', renewal_date=None)
        self.message_user(request, f"{updated} subscription(s) cancelled successfully.")
    cancel_subscription.short_description = "Cancel selected subscriptions"

    def mark_as_expired(self, request, queryset):
        """Manually expire subscriptions"""
        updated = queryset.update(status='expired', renewal_date=now() - timedelta(days=1))
        self.message_user(request, f"{updated} subscription(s) marked as expired.")
    mark_as_expired.short_description = "Mark as Expired"

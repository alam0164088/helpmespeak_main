from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from tts_app.views import home  # Import the home view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('authentication.urls')),
    path('api/payment/', include('payment.urls')),
    path('tts/', include('tts_app.urls')),
    path('api/', include('bot.urls')),
    path('api/', include('dashboard.urls')),
    
    # 🔹 allauth routes add করুন
    path('accounts/', include('allauth.urls')),  

    path('', home),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.contrib import admin
from django.urls import path, include
from controller.api import api
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('api/', api.urls),
                  path('app/', include('view.urls'))
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

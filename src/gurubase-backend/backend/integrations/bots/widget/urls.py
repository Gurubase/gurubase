from django.urls import path
from integrations.bots.widget import views as widget_views

urlpatterns = []

urlpatterns += [
    path('widget/ask/', widget_views.ask_widget, name='ask_widget'),
    path('widget/binge/', widget_views.widget_create_binge, name='widget_create_binge'),
    path('widget/guru/', widget_views.get_guru_visuals, name='get_guru_visuals'),
]


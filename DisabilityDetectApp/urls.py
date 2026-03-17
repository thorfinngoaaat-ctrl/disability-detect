from django.urls import path
from .import views
from django.views.generic import TemplateView
urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('home/', views.home, name='home'),
    path('test/', views.test, name='test'),
    path('typetest/', views.typetest, name='typetest'),
    path('call_llm/', views.call_llm, name='call_llm'),
    path('llm-test/', TemplateView.as_view(template_name='llm-test.html'), name='llm_test'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout, name='logout'),
    path('save_screening/', views.save_screening_result, name='save_screening'),
    path('save_typing/', views.save_typing_result, name='save_typing'),
    path('focustest/', views.focustest, name='focustest'),
    path('save_attention_test/', views.save_attention_test, name='save_attention_test'),
    path('save_autism_result/', views.save_autism_result, name='save_autism_result'),
    path('autism/', views.autism, name='autism'),
    path('math/', views.math, name='math'),
    path('save_math_result/', views.save_math_result, name='save_math_result')
]
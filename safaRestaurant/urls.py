from django.contrib import admin
from django.urls import path
from titoPicantitoRestaurant.views import *
from django.views.static import serve
from django.conf import settings
from django.urls import re_path
from django.conf.urls.static import static


urlpatterns = [
    path('', go_home, name='index'),
    path('home/', go_home, name='home'),
    path('conocenos/', go_conocenos, name='conocenos'),
    path('carta/', carta, name='carta'),
    path('añadir/', go_añadir, name='añadir'),
    path('registro/', registrar_usuario, name='registro'),
    path('login/', go_login, name='login'),
    path('logout/', go_logout, name='logout'),
    path('añadir_producto/', añadir_producto, name='añadir_producto'),
    path('productos/', lista_productos_admin, name='lista_productos_admin'),
    path('productos/editar/<int:producto_id>/', editar_producto, name='editar_producto'),
    path('productos/toggle/<int:producto_id>/', toggle_disponible, name='toggle_disponible'),
    path('usuarios/', lista_usuarios_admin, name='lista_usuarios_admin'),
    path('usuarios/editar/<int:usuario_id>/', editar_usuario, name='editar_usuario'),
    path('usuarios/toggle/<int:usuario_id>/', toggle_usuario_activo, name='toggle_usuario_activo'),
    path('usuarios/<int:usuario_id>/historial-logins/', historial_logins_usuario, name='historial_logins_usuario'),
    path('camarero/mesas/', gestion_mesas, name='gestion_mesas'),
    path('camarero/mesa/<int:mesa_id>/', gestion_pedido_mesa, name='gestion_pedido_mesa'),
    path('camarero/pedido/<int:pedido_id>/cerrar/', cerrar_pedido, name='cerrar_pedido'),
    path('camarero/pedido/<int:pedido_id>/ticket/', generar_ticket, name='generar_ticket'),
    path('camarero/linea/<int:linea_id>/eliminar/', eliminar_linea_pedido, name='eliminar_linea_pedido'),
    path('cocina/', vista_cocina, name='vista_cocina'),
    path('cocina/historial/', historial_cocina, name='historial_cocina'),
    path('cocina/marcar_preparado/<str:tipo_pedido>/<int:pedido_id>/', marcar_preparado, name='marcar_preparado'),
    path('cocina/marcar-linea/', marcar_linea_preparada, name='marcar_linea_preparada'),
    path('barra/', vista_barra, name='vista_barra'),
    path('barra/historial/', historial_barra, name='historial_barra'),
    path('barra/marcar_linea_preparada/', marcar_linea_barra_preparada, name='marcar_linea_barra_preparada'),
    path('catalogo/', catalogo_productos, name='catalogo'),
    path('carrito/', ver_carrito, name='carrito'),
    path('checkout/', checkout, name='checkout'),
    path('historial-pedidos/', historial_pedidos, name='historial_pedidos'),
    path('agregar-carrito/', agregar_al_carrito, name='agregar_carrito'),
    path('actualizar-carrito/', actualizar_carrito, name='actualizar_carrito'),
    path('eliminar-carrito/', eliminar_del_carrito, name='eliminar_carrito'),
    path('profile/', profile, name='profile'),
    path('crear_resena/', crear_resena, name='crear_resena'),
    path('mis_resenas/', mis_resenas, name='mis_resenas'),
    path('editar-resena/<int:id>/', editar_resena, name='editar_resena'),
    path('eliminar-resena/<int:id>/', eliminar_resena, name='eliminar_resena'),
    path('crear_reserva/', crear_reserva, name='crear_reserva'),
    path('ver_tus_reservas/', ver_tus_reservas, name='ver_tus_reservas'),
    path('editar-reserva/<int:id>/', editar_reserva, name='editar_reserva'),
    path('eliminar-reserva/<int:id>/', eliminar_reserva, name='eliminar_reserva'),





    # Esto sirve favicon.png directamente
    re_path(r'^favicon\.ico$', serve, {
        'path': 'static/favicon1.png',
        'document_root': settings.STATICFILES_DIRS[0],
    }),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
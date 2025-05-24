from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import *
from .models import *
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum, Prefetch
from django.http import HttpResponseNotAllowed
from django.views.decorators.http import require_POST


# Create your views here.

def go_home(request):
    return render(request, 'home.html')


def go_conocenos(request):
    return render(request, 'conocenos.html')

def carta(request):
    # Obtener productos por categoría que aparecen en la carta
    entrantes = Producto.objects.filter(tipo='ENTRANTE', aparece_en_carta=True)
    principales = Producto.objects.filter(tipo='PRINCIPAL', aparece_en_carta=True)
    bebidas = Producto.objects.filter(tipo='BEBIDA', aparece_en_carta=True)
    postres = Producto.objects.filter(tipo='POSTRE', aparece_en_carta=True)

    context = {
        'entrantes': entrantes,
        'principales': principales,
        'bebidas': bebidas,
        'postres': postres,
    }

    return render(request, 'carta_reactiva.html', context)

def go_añadir(request):
    return render(request, 'añadir_producto.html') # Asegúrate que el archivo html está en la ruta correcta


def registrar_usuario(request):
    if request.method == 'POST':
        form = RegistroFormulario(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '¡Registro exitoso! Bienvenido a nuestro restaurante.')
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        form = RegistroFormulario()

    return render(request, 'registro.html', {'form': form})


def go_login(request):
    if request.method == 'POST':
        form = LoginFormulario(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'¡Bienvenido de nuevo, {user.nombre}!')
                return redirect('home')
        messages.error(request, 'Email o contraseña incorrectos. Por favor, inténtalo de nuevo.')
    else:
        form = LoginFormulario()

    return render(request, 'login.html', {'form': form})


def go_logout(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente. ¡Vuelve pronto!')
    return redirect('login')



@login_required
@user_passes_test(lambda u: u.is_staff)
def añadir_producto(request):
    if request.method == 'POST':
        form = AñadirProductoFormulario(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save()
            # Manejar los alérgenos (ya que no se guardan automáticamente con ModelForm y ManyToMany)
            alergenos_seleccionados = request.POST.getlist('alergenos')
            producto.alergenos.set(alergenos_seleccionados)
            messages.success(request, "Producto añadido correctamente.")
            return redirect('carta')  # Redirige a la página de la carta o a donde desees
        else:
            messages.error(request, "Error al añadir el producto. Por favor, revisa el formulario.")
    else:
        form = AñadirProductoFormulario()

    alergenos = Alergeno.objects.all()
    return render(request, 'añadir_producto.html', {'form': form, 'alergenos': alergenos})


def admin_required(view_func):
    return user_passes_test(
        lambda u: u.is_authenticated and u.rol == Usuario.Rol.ADMIN,
        login_url='login'
    )(view_func)


@user_passes_test(admin_required, login_url='/login/')
def lista_productos_admin(request):
    # Obtener todos los productos ordenados por tipo y disponibilidad
    productos = Producto.objects.all().order_by('tipo', '-disponible', 'nombre')

    # Organizar por tipo
    productos_por_tipo = {
        'ENTRANTE': productos.filter(tipo='ENTRANTE'),
        'PRINCIPAL': productos.filter(tipo='PRINCIPAL'),
        'POSTRE': productos.filter(tipo='POSTRE'),
        'BEBIDA': productos.filter(tipo='BEBIDA'),
    }

    context = {
        'productos_por_tipo': productos_por_tipo,
    }

    return render(request, 'admin_productos.html', context)


@user_passes_test(admin_required, login_url='/login/')
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('lista_productos_admin')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'editar_producto.html', {'form': form})


@user_passes_test(admin_required, login_url='/login/')
def toggle_disponible(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    producto.disponible = not producto.disponible
    producto.save()
    return redirect('lista_productos_admin')


@admin_required
def lista_usuarios_admin(request):
    usuarios = Usuario.objects.all().order_by('rol', 'apellidos')
    return render(request, 'admin_usuarios.html', {'usuarios': usuarios})


@admin_required
def editar_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        # Procesar formulario de edición
        usuario.nombre = request.POST.get('nombre')
        usuario.apellidos = request.POST.get('apellidos')
        usuario.email = request.POST.get('email')
        usuario.telefono = request.POST.get('telefono')
        usuario.rol = request.POST.get('rol')
        usuario.save()
        messages.success(request, 'Usuario actualizado correctamente')
        return redirect('lista_usuarios_admin')

    return render(request, 'editar_usuario.html', {'usuario': usuario})


@admin_required
def toggle_usuario_activo(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    usuario.is_active = not usuario.is_active
    usuario.save()
    action = "activado" if usuario.is_active else "desactivado"
    messages.success(request, f'Usuario {action} correctamente')
    return redirect('lista_usuarios_admin')


##GESTION DE PEDIDOS MESA

def es_camarero_o_admin(user):
    return user.rol in [Usuario.Rol.CAMARERO, Usuario.Rol.ADMIN]


@login_required
@user_passes_test(es_camarero_o_admin)
def gestion_mesas(request):
    mesas = Mesa.objects.all().order_by('numero')
    pedidos_abiertos = PedidoMesa.objects.filter(estado__in=['PENDIENTE', 'EN_PREPARACION', 'SERVIDO'])

    # Crear un diccionario para saber qué mesas están ocupadas
    mesas_ocupadas = {pedido.mesa.id for pedido in pedidos_abiertos if pedido.mesa}

    return render(request, 'gestion_mesas.html', {
        'mesas': mesas,
        'mesas_ocupadas': mesas_ocupadas
    })


@login_required
@user_passes_test(es_camarero_o_admin)
def gestion_pedido_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id)
    pedido_activo = PedidoMesa.objects.filter(mesa=mesa, estado__in=['PENDIENTE', 'EN_PREPARACION', 'SERVIDO']).first()

    if not pedido_activo:
        if request.method == 'POST':
            form = PedidoMesaForm(request.POST)
            if form.is_valid():
                pedido_activo = form.save(commit=False)
                pedido_activo.mesa = mesa
                pedido_activo.camarero = request.user
                pedido_activo.save()
                mesa.disponible = False
                mesa.save()
                return redirect('gestion_pedido_mesa', mesa_id=mesa.id)
        else:
            form = PedidoMesaForm(initial={'num_comensales': mesa.capacidad})

        return render(request, 'nuevo_pedido_mesa.html', {
            'mesa': mesa,
            'form': form
        })

    productos = Producto.objects.filter(disponible=True).order_by('tipo', 'nombre')

    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')
        cantidad = int(request.POST.get('cantidad', 1))  # Por defecto 1 unidad

        if producto_id:
            producto = get_object_or_404(Producto, id=producto_id)

            # Buscar si ya existe una línea para este producto
            linea, created = LineaPedidoMesa.objects.get_or_create(
                pedido=pedido_activo,
                producto=producto,
                defaults={
                    'cantidad': cantidad,
                    'precio_unidad': producto.precio,
                    'subtotal': producto.precio * cantidad
                }
            )

            if not created:
                linea.cantidad += cantidad
                linea.subtotal = linea.cantidad * linea.precio_unidad
                linea.save()

            pedido_activo.calcular_total()

            return redirect('gestion_pedido_mesa', mesa_id=mesa.id)

    return render(request, 'gestion_pedido.html', {
        'mesa': mesa,
        'pedido': pedido_activo,
        'productos': productos,
        'form': LineaPedidoForm()
    })


@login_required
@user_passes_test(es_camarero_o_admin)
def cerrar_pedido(request, pedido_id):
    pedido = get_object_or_404(PedidoMesa, id=pedido_id)

    if request.method == 'POST':
        # Separar productos por zona de preparación
        lineas_cocina = pedido.lineas_pedido.filter(producto__zona_preparacion='COCINA')
        lineas_barra = pedido.lineas_pedido.filter(producto__zona_preparacion='BARRA')

        # Aquí podrías enviar notificaciones a cocina/barra
        # Por ahora solo imprimimos en consola para demostración
        print(f"Enviando a COCINA para mesa {pedido.mesa.numero}:")
        for linea in lineas_cocina:
            print(f"- {linea.cantidad}x {linea.producto.nombre}")

        print(f"\nEnviando a BARRA para mesa {pedido.mesa.numero}:")
        for linea in lineas_barra:
            print(f"- {linea.cantidad}x {linea.producto.nombre}")

        pedido.estado = 'CERRADO'
        pedido.fecha_cierre = timezone.now()
        pedido.save()

        # Liberar la mesa
        mesa = pedido.mesa
        mesa.disponible = True
        mesa.save()

        return redirect('generar_ticket', pedido_id=pedido.id)

    return render(request, 'confirmar_cierre.html', {
        'pedido': pedido
    })


@login_required
@user_passes_test(es_camarero_o_admin)
def generar_ticket(request, pedido_id):
    pedido = get_object_or_404(PedidoMesa, id=pedido_id)
    return render(request, 'ticket.html', {
        'pedido': pedido,
        'fecha': timezone.now()  # o datetime.now()
    })


@login_required
@user_passes_test(es_camarero_o_admin)
def eliminar_linea_pedido(request, linea_id):
    linea = get_object_or_404(LineaPedidoMesa, id=linea_id)
    pedido_id = linea.pedido.id
    linea.delete()

    # Recalcular el total
    pedido = get_object_or_404(PedidoMesa, id=pedido_id)
    pedido.calcular_total()

    return redirect('gestion_pedido_mesa', mesa_id=pedido.mesa.id)


##COCINA

def es_cocinero_o_admin(user):
    return user.rol in [Usuario.Rol.COCINERO, Usuario.Rol.ADMIN, Usuario.Rol.ENCARGADO]


from django.db.models import Q, Count, Sum
from django.http import HttpResponse


@login_required
@user_passes_test(es_cocinero_o_admin)
def vista_cocina(request):
    # Obtener pedidos con items de cocina no preparados
    pedidos_mesa = PedidoMesa.objects.filter(
        estado__in=['PENDIENTE', 'EN_PREPARACION', 'PARCIALMENTE_SERVIDO'],
        lineas_pedido__producto__zona_preparacion='COCINA',
        lineas_pedido__preparado=False
    ).distinct().prefetch_related(
        Prefetch('lineas_pedido',
                queryset=LineaPedidoMesa.objects.filter(
                    producto__zona_preparacion='COCINA',
                    preparado=False
                ).select_related('producto'))
    ).select_related('mesa')

    # Obtener pedidos online
    pedidos_online = PedidoOnline.objects.filter(
        estado__in=['PENDIENTE', 'EN_PREPARACION'],
        lineas_pedido__producto__zona_preparacion='COCINA',
        lineas_pedido__preparado=False
    ).distinct().prefetch_related(
        Prefetch('lineas_pedido',
                queryset=LineaPedidoOnline.objects.filter(
                    producto__zona_preparacion='COCINA',
                    preparado=False
                ).select_related('producto'))
    ).select_related('usuario')

    return render(request, 'cocina.html', {
        'pedidos_mesa': pedidos_mesa,
        'pedidos_online': pedidos_online,
        'hora_actual': timezone.now()
    })


@login_required
@user_passes_test(es_cocinero_o_admin)
def marcar_preparado(request, pedido_id, tipo_pedido):
    if request.method == 'POST':
        if tipo_pedido == 'mesa':
            pedido = get_object_or_404(PedidoMesa, id=pedido_id)
            lineas = pedido.lineas_pedido.filter(
                producto__zona_preparacion='COCINA',
                preparado=False
            )

            # Marcar todas las líneas como preparadas
            lineas.update(preparado=True)

            # Verificar si hay nuevas líneas añadidas
            pedido.refresh_from_db()
            if pedido.lineas_pedido.filter(preparado=False).exists():
                pedido.tiene_nuevos_productos = True
                pedido.estado = 'EN_PREPARACION'
                messages.success(request, f'Productos de la mesa {pedido.mesa.numero} marcados como preparados. Hay nuevos productos pendientes.')
            else:
                pedido.tiene_nuevos_productos = False
                pedido.estado = 'SERVIDO'
                messages.success(request, f'Todos los productos de la mesa {pedido.mesa.numero} están preparados.')
            pedido.save()

            return redirect('vista_cocina')

        elif tipo_pedido == 'online':
            pedido = get_object_or_404(PedidoOnline, id=pedido_id)
            lineas = pedido.lineas_pedido.filter(
                producto__zona_preparacion='COCINA',
                preparado=False
            )

            # Marcar todas las líneas como preparadas
            lineas.update(preparado=True)

            # Verificar si todas las líneas del pedido están preparadas
            todas_preparadas = not pedido.lineas_pedido.filter(preparado=False).exists()
            if todas_preparadas:
                pedido.estado = 'LISTO'
                pedido.save()
                messages.success(request, f'Todos los productos del pedido online {pedido.id} están preparados.')
            else:
                messages.success(request, f'Productos de cocina del pedido online {pedido.id} marcados como preparados.')

            return redirect('vista_cocina')

    return HttpResponseNotAllowed(['POST'])

from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import LineaPedidoMesa, LineaPedidoOnline

@login_required
@user_passes_test(es_cocinero_o_admin)
@require_POST
def marcar_linea_preparada(request):
    linea_id = request.POST.get('linea_id')
    tipo = request.POST.get('tipo')

    try:
        if tipo == 'mesa':
            linea = LineaPedidoMesa.objects.select_related('pedido').get(id=linea_id)
        elif tipo == 'online':
            linea = LineaPedidoOnline.objects.select_related('pedido').get(id=linea_id)
        else:
            messages.error(request, "Tipo de pedido inválido")
            return redirect('vista_cocina')

        linea.preparado = True
        linea.save()

        pedido = linea.pedido
        todas_preparadas = not pedido.lineas_pedido.filter(
            producto__zona_preparacion='COCINA',
            preparado=False
        ).exists()

        if todas_preparadas:
            pedido.estado = 'SERVIDO' if tipo == 'mesa' else 'LISTO'
            pedido.save()
            messages.success(request, f"Pedido {'de mesa' if tipo == 'mesa' else 'online'} {pedido.id} está listo.")
        else:
            messages.success(request, f"Línea marcada como preparada correctamente.")

    except Exception as e:
        messages.error(request, f"Error al marcar la línea: {e}")

    return redirect('vista_cocina')


@login_required
@user_passes_test(es_cocinero_o_admin)
def historial_cocina(request):
    # Obtener pedidos recientes (últimas 24 horas) que tenían productos de cocina
    desde = timezone.now() - timezone.timedelta(hours=24)

    # Consulta para pedidos de mesa (usando values() para evitar NCLOB)
    pedidos_mesa = PedidoMesa.objects.filter(
        lineas_pedido__producto__zona_preparacion='COCINA',
        fecha_creacion__gte=desde
    ).distinct().order_by('-fecha_creacion').values(
        'id', 'mesa__numero', 'fecha_creacion', 'fecha_cierre', 'estado', 'num_comensales'
    )

    # Consulta para pedidos online (usando values() para evitar NCLOB)
    pedidos_online = PedidoOnline.objects.filter(
        lineas_pedido__producto__zona_preparacion='COCINA',
        fecha_creacion__gte=desde
    ).distinct().order_by('-fecha_creacion').values(
        'id', 'usuario__nombre', 'usuario__apellidos', 'fecha_creacion', 'estado'
    )

    # Procesar los resultados
    historial = []

    for pedido in pedidos_mesa:
        # Obtener las líneas de cocina para este pedido
        lineas_cocina = LineaPedidoMesa.objects.filter(
            pedido_id=pedido['id'],
            producto__zona_preparacion='COCINA'
        ).aggregate(
            total_productos=Count('id'),
            total_unidades=Sum('cantidad')
        )

        historial.append({
            'tipo': 'mesa',
            'id': pedido['id'],
            'cliente': f"Mesa {pedido['mesa__numero']}",
            'fecha': pedido['fecha_creacion'],
            'estado': pedido['estado'],
            'comensales': pedido['num_comensales'],
            'productos': lineas_cocina['total_productos'],
            'unidades': lineas_cocina['total_unidades'] or 0,
            'fecha_cierre': pedido['fecha_cierre']
        })

    for pedido in pedidos_online:
        # Obtener las líneas de cocina para este pedido
        lineas_cocina = LineaPedidoOnline.objects.filter(
            pedido_id=pedido['id'],
            producto__zona_preparacion='COCINA'
        ).aggregate(
            total_productos=Count('id'),
            total_unidades=Sum('cantidad')
        )

        historial.append({
            'tipo': 'online',
            'id': pedido['id'],
            'cliente': f"{pedido['usuario__nombre']} {pedido['usuario__apellidos']}",
            'fecha': pedido['fecha_creacion'],
            'estado': pedido['estado'],
            'comensales': None,
            'productos': lineas_cocina['total_productos'],
            'unidades': lineas_cocina['total_unidades'] or 0,
            'fecha_cierre': None
        })

    # Ordenar por fecha descendente
    historial.sort(key=lambda x: x['fecha'], reverse=True)

    return render(request, 'historial_cocina.html', {
        'pedidos': historial,
        'hora_actual': timezone.now()
    })


@login_required
@user_passes_test(es_camarero_o_admin)
def gestion_pedido_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id)
    pedido_activo = PedidoMesa.objects.filter(
        mesa=mesa,
        estado__in=['PENDIENTE', 'EN_PREPARACION', 'SERVIDO', 'PARCIALMENTE_SERVIDO']
    ).first()

    if not pedido_activo:
        if request.method == 'POST':
            form = PedidoMesaForm(request.POST)
            if form.is_valid():
                pedido_activo = form.save(commit=False)
                pedido_activo.mesa = mesa
                pedido_activo.camarero = request.user
                pedido_activo.estado = 'PENDIENTE'
                pedido_activo.save()
                mesa.disponible = False
                mesa.save()
                return redirect('gestion_pedido_mesa', mesa_id=mesa.id)
        else:
            form = PedidoMesaForm(initial={'num_comensales': mesa.capacidad})

        return render(request, 'nuevo_pedido_mesa.html', {
            'mesa': mesa,
            'form': form
        })

    productos = Producto.objects.filter(disponible=True).order_by('tipo', 'nombre')

    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')
        cantidad = int(request.POST.get('cantidad', 1))

        if producto_id:
            producto = get_object_or_404(Producto, id=producto_id)

            linea, created = LineaPedidoMesa.objects.get_or_create(
                pedido=pedido_activo,
                producto=producto,
                defaults={
                    'cantidad': cantidad,
                    'precio_unidad': producto.precio,
                    'subtotal': producto.precio * cantidad,
                    'preparado': False  # Asegúrate que siempre sea False al crear
                }
            )

            if not created:
                linea.cantidad += cantidad
                linea.subtotal = linea.cantidad * linea.precio_unidad
                linea.preparado = False  # Resetear a no preparado
                linea.save()

            # Actualizar estado del pedido
            pedido_activo.estado = 'EN_PREPARACION'
            pedido_activo.tiene_nuevos_productos = True
            pedido_activo.save()
            pedido_activo.calcular_total()

            return redirect('gestion_pedido_mesa', mesa_id=mesa.id)

    return render(request, 'gestion_pedido.html', {
        'mesa': mesa,
        'pedido': pedido_activo,
        'productos': productos,
        'form': LineaPedidoForm()
    })

##BARRA

def es_bartender_o_admin(user):
    return user.is_authenticated and (user.rol == 'BARTENDER' or user.is_superuser)

@login_required
@user_passes_test(es_bartender_o_admin)  # Crea este helper si no existe
def vista_barra(request):
    pedidos_mesa = PedidoMesa.objects.filter(
        estado__in=['EN_PREPARACION', 'PENDIENTE']
    ).distinct()

    pedidos_online = PedidoOnline.objects.filter(
        estado__in=['EN_PREPARACION', 'PENDIENTE']
    ).distinct()

    hora_actual = timezone.now()

    return render(request, 'barra.html', {
        'pedidos_mesa': pedidos_mesa,
        'pedidos_online': pedidos_online,
        'hora_actual': hora_actual
    })


@require_POST
@login_required
@user_passes_test(es_bartender_o_admin)
def marcar_linea_barra_preparada(request):
    linea_id = request.POST.get('linea_id')
    tipo = request.POST.get('tipo')

    if tipo == 'mesa':
        linea = get_object_or_404(LineaPedidoMesa, id=linea_id)
    elif tipo == 'online':
        linea = get_object_or_404(LineaPedidoOnline, id=linea_id)
    else:
        return redirect('vista_barra')

    linea.preparado = True
    linea.save()
    messages.success(request, 'Producto marcado como preparado.')

    return redirect('vista_barra')


@login_required
@user_passes_test(es_bartender_o_admin)
def historial_barra(request):
    lineas_mesa = LineaPedidoMesa.objects.filter(
        producto__zona_preparacion='BARRA', preparado=True
    ).order_by('-id')[:50]

    lineas_online = LineaPedidoOnline.objects.filter(
        producto__zona_preparacion='BARRA', preparado=True
    ).order_by('-id')[:50]

    return render(request, 'barra_historial.html', {
        'lineas_mesa': lineas_mesa,
        'lineas_online': lineas_online,
    })


##mostrar el historial de logins

def historial_logins_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    logins = HistorialLogin.objects.filter(usuario=usuario).order_by('-fecha_login')

    return render(request, 'historial_logins.html', {
        'usuario': usuario,
        'logins': logins
    })
from datetime import timezone

from cloudinary.models import CloudinaryField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


# PRODUCTO Y ALERGENO
class Alergeno(models.Model):
    nombre = models.CharField(max_length=50)
    fecha_alta = models.DateTimeField(null=True, blank=True)
    fecha_modificacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'alergeno'

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    class ZonaPreparacion(models.TextChoices):
        COCINA = 'COCINA', 'Cocina'
        BARRA = 'BARRA', 'Barra'

    class TipoProducto(models.TextChoices):
        ENTRANTE = 'ENTRANTE', 'Entrante'
        PRINCIPAL = 'PRINCIPAL', 'Principal'
        BEBIDA = 'BEBIDA', 'Bebida'
        POSTRE = 'POSTRE', 'Postre'

    imagen = CloudinaryField('image', blank=True, null=True)  # Campo para la imagen
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=6, decimal_places=2)
    nivel_picante = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(5)], default=1)
    zona_preparacion = models.CharField(
        max_length=10,
        choices=ZonaPreparacion.choices,
        default=ZonaPreparacion.COCINA,
    )
    alergenos = models.ManyToManyField(
        Alergeno,
        through='ProductoAlergeno',
        blank=True,
    )
    disponible = models.BooleanField(default=True)
    tipo = models.CharField(
        max_length=10,
        choices=TipoProducto.choices,
        default=TipoProducto.PRINCIPAL,
    )
    aparece_en_carta = models.BooleanField(default=False)
    fecha_alta = models.DateTimeField(null=True, blank=True)
    fecha_modificacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'producto'

    def __str__(self):
        return self.nombre


class ProductoAlergeno(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    alergeno = models.ForeignKey(Alergeno, on_delete=models.CASCADE)
    fecha_alta = models.DateTimeField(null=True, blank=True)
    fecha_modificacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'producto_alergeno'
        unique_together = ('producto', 'alergeno')

    def __str__(self):
        return f"{self.producto.nombre} - {self.alergeno.nombre}"


## PEDIDO Y MESAS
class Mesa(models.Model):
    numero = models.IntegerField(unique=True)
    disponible = models.BooleanField(default=True)
    capacidad = models.PositiveIntegerField(default=4)  # Capacidad máxima de la mesa
    ubicacion = models.CharField(max_length=100, blank=True, null=True)  # Ejemplo: "Terraza", "Interior"
    fecha_alta = models.DateTimeField(null=True, blank=True)
    fecha_modificacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'mesa'
        ordering = ['numero']

    def __str__(self):
        return f'Mesa {self.numero} - {"Disponible" if self.disponible else "Ocupada"}'

class PedidoMesa(models.Model):
    class EstadoPedido(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        EN_PREPARACION = 'EN_PREPARACION', 'En Preparación'
        SERVIDO = 'SERVIDO', 'Servido'
        CERRADO = 'CERRADO', 'Cerrado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    mesa = models.ForeignKey(Mesa, on_delete=models.SET_NULL, null=True, related_name='pedidos_mesa')
    camarero = models.ForeignKey('Usuario', on_delete=models.SET_NULL, null=True, related_name='pedidos_atendidos')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=EstadoPedido.choices,
        default=EstadoPedido.PENDIENTE,
    )
    total = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    num_comensales = models.PositiveIntegerField(default=1)
    notas = models.CharField(max_length=100, blank=True, null=True)
    tiene_nuevos_productos = models.BooleanField(default=False)
    fecha_alta = models.DateTimeField(null=True, blank=True)
    fecha_modificacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'pedido_mesa'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'Pedido Mesa {self.id} - Mesa {self.mesa.numero if self.mesa else "?"} - {self.get_estado_display()}'

    def marcar_como_servido(self):
        """Marca el pedido como servido pero manteniéndolo visible si hay nuevos productos"""
        if self.lineas_pedido.filter(preparado=False).exists():
            self.tiene_nuevos_productos = True
        else:
            self.tiene_nuevos_productos = False
            self.estado = 'SERVIDO'
        self.save()

    def calcular_total(self):
        total = 0
        for detalle in self.lineas_pedido.all():  # <---- nombre correcto según related_name
            total += detalle.producto.precio * detalle.cantidad
        self.total = total
        self.save()

    def actualizar_estado(self):
        """Actualiza el estado del pedido según sus líneas"""
        if self.lineas_pedido.filter(preparado=False).exists():
            self.estado = 'EN_PREPARACION'
        else:
            self.estado = 'SERVIDO'
        self.save()

    @property
    def total_por_persona(self):
        return self.total / self.num_comensales if self.num_comensales > 0 else 0

class PedidoOnline(models.Model):
    class EstadoPedido(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        EN_PREPARACION = 'EN_PREPARACION', 'En Preparación'
        LISTO = 'LISTO', 'Listo para Recoger'
        CANCELADO = 'CANCELADO', 'Cancelado'

    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='pedidos_online')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=20,
        choices=EstadoPedido.choices,
        default=EstadoPedido.PENDIENTE,
    )
    total = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    fecha_alta = models.DateTimeField(null=True, blank=True)
    fecha_modificacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'pedido_online'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'Pedido Online {self.id} - {self.get_estado_display()} - {self.fecha_creacion}'


class LineaPedidoOnline(models.Model):
    pedido = models.ForeignKey(PedidoOnline, on_delete=models.CASCADE, related_name='lineas_pedido')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unidad = models.DecimalField(max_digits=6, decimal_places=2)
    subtotal = models.DecimalField(max_digits=8, decimal_places=2)
    preparado = models.BooleanField(default=False)  # Nuevo campo
    fecha_alta = models.DateTimeField(null=True, blank=True)
    fecha_modificacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'linea_pedido_online'
        unique_together = ('pedido', 'producto')

    def __str__(self):
        return f'{self.cantidad} x {self.producto.nombre} en Pedido Online {self.pedido.id}'


class LineaPedidoMesa(models.Model):
    pedido = models.ForeignKey(PedidoMesa, on_delete=models.CASCADE, related_name='lineas_pedido')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unidad = models.DecimalField(max_digits=6, decimal_places=2)
    subtotal = models.DecimalField(max_digits=8, decimal_places=2)
    preparado = models.BooleanField(default=False)
    fecha_alta = models.DateTimeField(null=True, blank=True)
    fecha_modificacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'linea_pedido_mesa'
        unique_together = ('pedido', 'producto')

    def __str__(self):
        return f'{self.cantidad} x {self.producto.nombre} en Pedido Mesa {self.pedido.id}'



## LOGIN Y REGISTRO
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # Cifra la contraseña
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not extra_fields.get('is_staff'):
            raise ValueError('El superusuario debe tener is_staff=True.')
        if not extra_fields.get('is_superuser'):
            raise ValueError('El superusuario debe tener is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

##RESENAS
class Resena(models.Model):
    puntuacion = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(5)])
    comentario = models.TextField()
    fecha_creacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'resena'

    def __str__(self):
        return self.comentario

class Usuario(AbstractBaseUser, PermissionsMixin):
    class Rol(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        ENCARGADO = 'encargado', 'Encargado'
        CAMARERO = 'camarero', 'Camarero'
        COCINERO = 'cocinero', 'Cocinero'
        BARTENDER = 'bartender', 'Bartender'
        CLIENTE = 'cliente', 'Cliente'

    imagen = imagen = CloudinaryField('image', blank=True, null=True)
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=150)
    fecha_nacimiento = models.DateField()
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20)
    rol = models.CharField(
        max_length=10,
        choices=Rol.choices,
        default=Rol.CLIENTE,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    fecha_alta = models.DateTimeField(null=True, blank=True)
    fecha_modificacion = models.DateTimeField(null=True, blank=True)
    resenas = models.ManyToManyField(
        Resena,
        through='ResenaUsuario',
        blank=True,
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellidos', 'fecha_nacimiento', 'telefono', 'rol']

    class Meta:
        db_table = 'usuario'

    def __str__(self):
        return f'{self.nombre} {self.apellidos} ({self.rol})'

    def save(self, *args, **kwargs):
        # Si el rol es admin, establece is_staff y is_superuser a True
        if self.rol == self.Rol.ADMIN:
            self.is_staff = True
            self.is_superuser = True
        else:
            # Para otros roles, aseguraro que no son superusuarios
            self.is_superuser = False
            if self.rol in [self.Rol.ENCARGADO]:
                self.is_staff = True
            else:
                self.is_staff = False

        super().save(*args, **kwargs)

class ResenaUsuario(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    resena = models.ForeignKey(Resena, on_delete=models.CASCADE)

    class Meta:
        db_table = 'resena_usuario'
        unique_together = ('resena', 'usuario')

    def __str__(self):
        return f"{self.resena.comentario} - {self.usuario.nombre}"

##CREAR EL HISTORIAL DE LOGINS

class HistorialLogin(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='logins')
    fecha_login = models.DateTimeField(auto_now_add=True)
    direccion_ip = models.CharField(max_length=45, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'historial_login'
        ordering = ['-fecha_login']
        verbose_name = 'Historial de Login'
        verbose_name_plural = 'Historial de Logins'

    def __str__(self):
        return f"{self.usuario.email} - {self.fecha_login}"


##CREAR RESERVAS DE MESAS

class ReservaMesa(models.Model):
    ncomensales = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    informacionMesa = models.TextField()
    fecha_reserva = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'reserva_mesa'

    def __str__(self):
        return self.informacionMesa

class ReservaUsuario(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    reserva = models.ForeignKey(ReservaMesa, on_delete=models.CASCADE)

    class Meta:
        db_table = 'reserva_usuario'
        unique_together = ('reserva', 'usuario')

    def __str__(self):
        return f"{self.reserva.informacionMesa} - {self.usuario.nombre}"

##SUGERENCIAS
class Sugerencia(models.Model):
    class tipoSugerencia(models.TextChoices):
        PLATOS = 'PLATOS', 'Platos'
        LOCAL = 'LOCAL', 'Local'
        PEDIDOS = 'PEDIDOS', 'Pedidos'

    titulo = models.CharField(max_length=100)
    tipo_sugerencia = models.CharField(
        max_length=10,
        choices=tipoSugerencia.choices,
        default=tipoSugerencia.LOCAL,
    )
    comentario = models.TextField()
    fecha_creacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sugerencia'

    def __str__(self):
        return self.titulo

class SugerenciaUsuario(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    sugerencia = models.ForeignKey(Sugerencia, on_delete=models.CASCADE)

    class Meta:
        db_table = 'sugerencia_usuario'
        unique_together = ('sugerencia', 'usuario')

    def __str__(self):
        return f"{self.sugerencia.titulo} - {self.usuario.nombre}"

##Solicitud de empleo Recuperación defensa
class Solicitud(models.Model):
    class puesto(models.TextChoices):
        CAMARERO = 'CAMARERO', 'Camarero'
        COCINERO = 'COCINERO', 'Cocinero'
        Gestor = 'GESTOR', 'Gestor'

    puesto = models.CharField(
        max_length=10,
        choices=puesto.choices,
        default=puesto.CAMARERO,
    )
    comentario = models.TextField()
    fecha_creacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'solicitud'

    def __str__(self):
        return self.puesto

class SolicitudUsuario(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE)

    class Meta:
        db_table = 'solicitud_usuario'
        unique_together = ('solicitud', 'usuario')

    def __str__(self):
        return f"{self.solicitud.puesto} - {self.usuario.nombre}"
from django.apps import AppConfig


class TitopicantitorestaurantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'titoPicantitoRestaurant'

    def ready(self):
        import titoPicantitoRestaurant.signals  # noqa
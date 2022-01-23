import csv

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Добавляет ингредиенты из сsv файла в базу данных sqlite3.'

    def handle(self, *args, **options):
        with open(
            'data/ingredients.csv',
            'r', encoding='utf-8'
        ) as file:
            reader = csv.reader(file, delimiter=',')
            Ingredient.objects.all().delete
            for row in reader:
                name, unit = row
                Ingredient.objects.get_or_create(
                    name=name, measurement_unit=unit)
        print('Загрузка завершена')

from django.contrib.auth import get_user_model
from django.db.models import F
from django.shortcuts import get_object_or_404

from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes.models import Favorite, Ingredient, IngredientRecipe, Recipe, Tag
from rest_framework import serializers
from rest_framework.serializers import ValidationError
from users.models import Subscribe

User = get_user_model()


class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = ('email', 'id', 'username',
                  'first_name', 'last_name', 'password')


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Subscribe.objects.filter(
            user=user,
            author=obj
        ).exists()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', )


class PasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class SubscriptionsRecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscribeSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', )

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Subscribe.objects.filter(
            user=user,
            author=obj
        ).exists()

    def get_recipes(self, obj):
        limit = self.context['request'].query_params.get('recipes_limit')
        if limit is None:
            recipes = obj.recipes.all()
        else:
            recipes = obj.recipes.all()[:int(limit)]
        return SubscriptionsRecipeSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time', )


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug', )


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit', )


class IngredientRecipeListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount', )


class IngredientRecipeCreateSerializer(serializers.ModelSerializer):
    amount = serializers.IntegerField(write_only=True)
    id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Ingredient
        fields = [
            'id',
            'amount'
        ]


class RecipeListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    author = CustomUserSerializer()
    ingredients = IngredientRecipeListSerializer(
        many=True,
        source='ingredient_recipe'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Favorite.objects.filter(
            user=user,
            recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Recipe.objects.filter(
            shopping_cart__user=user,
            id=obj.id
        ).exists()


class RecipeCreateSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    # author = CustomUserSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    ingredients = IngredientRecipeCreateSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('ingredients', 'tags', 'image',
                  'name', 'text', 'cooking_time', 'author')

    def validate_ingredients(self, data):
        ingredients = self.initial_data.get('ingredients')
        if ingredients == []:
            raise ValidationError('Нужно выбрать минимум 1 ингридиент!')
        for ingredient in ingredients:
            if int(ingredient['amount']) <= 0:
                raise ValidationError('Количество должно быть положительным!')
        return data

    def get_ingredients(self, obj):
        ingredients = IngredientRecipe.objects.filter(recipe=obj)
        return IngredientRecipeListSerializer(ingredients).data

    def add_recipe_ingredients(self, ingredients, recipe):
        for ingredient in ingredients:
            ingredient_id = ingredient['id']
            amount = ingredient['amount']
            if IngredientRecipe.objects.filter(
                recipe=recipe, ingredient=ingredient_id
            ).exists():
                amount += F('amount')
            IngredientRecipe.objects.update_or_create(
                recipe=recipe, ingredient=ingredient_id,
                defaults={'amount': amount})

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        for ingredient in ingredients:
            id = ingredient.get('id')
            amount = ingredient.get('amount')
            ingredient_id = get_object_or_404(Ingredient, id=id)
            IngredientRecipe.objects.create(
                recipe=recipe, ingredient=ingredient_id, amount=amount
            )
        recipe.save()
        return recipe

    def update(self, instance, validated_data):
        instance.image = validated_data.get('image', instance.image)
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time
        )
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        instance.tags.clear()
        instance.ingredients.clear()
        for tag in tags_data:
            tag_id = tag.id
            tag_object = get_object_or_404(Tag, id=tag_id)
            instance.tags.add(tag_object)
        for ingredient in ingredients_data:
            ingredient_id = ingredient.get('id')
            amount = ingredient.get('amount')
            ingredient_object = get_object_or_404(Ingredient, id=ingredient_id)
            instance.ingredients.add(
                ingredient_object,
                through_defaults={'amount': amount}
            )
        instance.save()
        return instance

    def to_representation(self, instance):
        serializer = RecipeListSerializer(
            instance,
            context=self.context
        )
        return serializer.data


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time', )

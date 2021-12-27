from backend.users.models import Subscribe
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from users.models import User

from .filters import RecipeFilter
from .permissions import IsAuthorAdminOrReadOnly
from .serializers import (IngredientSerializer, RecipeSerializer,
                          SubscribeSerializer, TagSerializer, UserSerializer)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthorAdminOrReadOnly, )

    @action(detail=False,
            methods=['get'],
            permission_classes=(IsAuthenticated, ))
    def me(self, request):
        serializer = UserSerializer(self.request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False,
            methods=['post'],
            permission_classes=(IsAuthenticated, ))
    def set_password(self, request, pk=None):
        user = self.request.user
        serializer = UserSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            user.set_password(serializer.data['new_password'])
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False,
            methods=['get'],
            permission_classes=(IsAuthenticated, ))
    def subscriptions(self, request):
        user = request.user
        queryset = Subscribe.objects.filter(user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        methods=['get', 'delete'],
        detail=True,
        permission_classes=(IsAuthenticated, )
    )
    def subscribe(self, request, id):
        user = self.request.user
        author = get_object_or_404(User, id=id)
        subscribe = Subscribe.objects.filter(user=user, author=author).exists()
        if request.method == 'GET':
            if author != user and not subscribe:
                Subscribe.objects.create(user=user, author=author)
                serializer = UserSerializer(
                    author,
                    context={'request': request}
                )
                return Response(data=serializer.data,
                                status=status.HTTP_201_CREATED)
            data = {
                'errors': ('Вы подписаны на этого автора, '
                           'или пытаетесь подписаться на себя.')
            }
            return Response(data=data, status=status.HTTP_403_FORBIDDEN)
        if not Subscribe.objects.filter(author=author).exists():
            data = {
                'errors': ('Вы не подписаны на данного автора.')
            }
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        Subscribe.objects.filter(user=user, author=author).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagsViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny, )


class IngredientsViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny, )
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)


class RecipesViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthorAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    @action(
        methods=['get', 'delete'],
        detail=True,
        permission_classes=[IsAuthenticated, ],
        url_path='favorite'
    )
    def favorite(self, request, pk=None):
        if request.method == 'GET':
            return self.create_obj(Favorite, request.user, pk)
        elif request.method == 'DELETE':
            return self.delete_obj(Favorite, request.user, pk)
        return None

    @action(
        detail=True,
        methods=["get", "delete"],
        permission_classes=[IsAuthenticated, ],
    )
    def shopping_cart(self, request, pk=None):
        if request.method == 'GET':
            return self.create_obj(ShoppingCart, request.user, pk)
        elif request.method == 'DELETE':
            return self.delete_obj(ShoppingCart, request.user, pk)
        return None

    def create_obj(self, model, user, pk):
        if model.objects.filter(user=user, recipe__id=pk).exists():
            return Response(
                {'errors': 'Такой рецепт уже есть в списке.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe = get_object_or_404(Recipe, id=pk)
        model.objects.create(user=user, recipe=recipe)
        serializer = RecipeSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_obj(self, model, user, pk):
        obj = model.objects.filter(user=user, recipe__id=pk)
        if obj.exists():
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': 'Рецепт уже удален'}, status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        methods=['get'],
        detail=False,
        permission_classes=[IsAuthenticated, ],
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        user = request.user
        shopping_cart = ShoppingCart.objects.filter(user=user)
        list = {}
        ingredients = IngredientRecipe.objects.filter(
            recipe__in=shopping_cart.values_list('ingredient_recipe')
        )
        for ingredient in ingredients:
            amount = ingredient.amount
            name = ingredient.ingredient.name
            measurement_unit = ingredient.ingredient.measurement_unit
            if name not in list:
                list[name] = {
                    'measurement_unit': measurement_unit,
                    'amount': amount
                }
            else:
                list[name]['amount'] = (
                    list[name]['amount'] + amount
                )

        shopping_list = []
        for item in list:
            shopping_list.append(f'{item} - {list[item]["amount"]} '
                                 f'{list[item]["measurement_unit"]} \n')
        response = HttpResponse(shopping_list, 'Content-Type: text/plain')
        response['Content-Disposition'] = 'attachment; filename="shoplist.txt"'

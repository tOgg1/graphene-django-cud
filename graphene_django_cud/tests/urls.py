from django.urls import re_path
from graphene_file_upload.django import FileUploadGraphQLView

urlpatterns = [
    re_path(r'^graphql', FileUploadGraphQLView.as_view(graphiql=True))
]



# Dummy Query object for testing so that GraphQL 3.0 does not complain
import graphene


class DummyQuery(graphene.ObjectType):
    ok = graphene.Boolean()

    def resolve_ok(self, info):
        return True

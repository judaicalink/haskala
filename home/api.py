from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, routers, viewsets

from .models import (
    Alignment,
    Book,
    City,
    DateFormat,
    Edition,
    Font,
    FootnoteLocation,
    Gender,
    Geolocation,
    Language,
    LanguageCount,
    Mention,
    MentionDescription,
    Occupation,
    OriginalType,
    Person,
    Preface,
    Production,
    ProductionRole,
    Publisher,
    Series,
    TargetAudience,
    TextualModel,
    Topic,
    Translation,
    TranslationType,
    Typography,
)
from .serializers import (
    AlignmentSerializer,
    BookSerializer,
    CitySerializer,
    DateFormatSerializer,
    EditionSerializer,
    FontSerializer,
    FootnoteLocationSerializer,
    GenderSerializer,
    GeolocationSerializer,
    LanguageCountSerializer,
    LanguageSerializer,
    MentionDescriptionSerializer,
    MentionSerializer,
    OccupationSerializer,
    OriginalTypeSerializer,
    PersonSerializer,
    PrefaceSerializer,
    ProductionRoleSerializer,
    ProductionSerializer,
    PublisherSerializer,
    SeriesSerializer,
    TargetAudienceSerializer,
    TextualModelSerializer,
    TopicSerializer,
    TranslationSerializer,
    TranslationTypeSerializer,
    TypographySerializer,
)


class ReadOnlyBaseViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only base view set with filtering, search and ordering enabled."""

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields: list[str] = []
    search_fields: list[str] = []
    ordering_fields: list[str] = []


class BookViewSet(ReadOnlyBaseViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filterset_fields = [
        "bundle",
        "gregorian_year",
        "languages",
        "publication_place",
        "publisher",
        "series",
        "alignment",
        "topics",
    ]
    search_fields = [
        "name",
        "full_title",
        "subtitle",
        "authors__pref_label",
        "authors__german_name",
        "authors__hebrew_name",
    ]
    ordering_fields = ["name", "gregorian_year", "created_at", "updated_at"]
    ordering = ["name"]


class PersonViewSet(ReadOnlyBaseViewSet):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    filterset_fields = [
        "gender",
        "occupations",
        "place_of_birth",
        "place_of_death",
    ]
    search_fields = [
        "pref_label",
        "german_name",
        "hebrew_name",
        "pseudonym",
    ]
    ordering_fields = ["pref_label", "german_name", "hebrew_name"]
    ordering = ["pref_label"]


class CityViewSet(ReadOnlyBaseViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class GeolocationViewSet(ReadOnlyBaseViewSet):
    queryset = Geolocation.objects.select_related("city")
    serializer_class = GeolocationSerializer
    filterset_fields = ["city"]
    search_fields = ["city__name"]
    ordering_fields = ["city__name"]


class EditionViewSet(ReadOnlyBaseViewSet):
    queryset = Edition.objects.select_related("book", "city")
    serializer_class = EditionSerializer
    filterset_fields = ["book", "city", "year"]
    search_fields = ["name", "book__name", "city__name"]
    ordering_fields = ["year", "name", "created_at"]


class TranslationViewSet(ReadOnlyBaseViewSet):
    queryset = Translation.objects.select_related("book", "translator", "language", "city")
    serializer_class = TranslationSerializer
    filterset_fields = ["book", "translator", "language", "city"]
    search_fields = ["title", "book__name", "translator__pref_label"]
    ordering_fields = ["title"]


class MentionViewSet(ReadOnlyBaseViewSet):
    queryset = Mention.objects.select_related(
        "mentionee", "mentionee_city", "mentionee_description"
    )
    serializer_class = MentionSerializer
    filterset_fields = ["mentionee", "mentionee_city", "mentionee_description"]
    search_fields = ["mentionee__pref_label", "mentionee_city__name"]


class LanguageViewSet(ReadOnlyBaseViewSet):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class AlignmentViewSet(ReadOnlyBaseViewSet):
    queryset = Alignment.objects.all()
    serializer_class = AlignmentSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class FontViewSet(ReadOnlyBaseViewSet):
    queryset = Font.objects.all()
    serializer_class = FontSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class PublisherViewSet(ReadOnlyBaseViewSet):
    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer
    filterset_fields = ["slug"]
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class SeriesViewSet(ReadOnlyBaseViewSet):
    queryset = Series.objects.all()
    serializer_class = SeriesSerializer
    filterset_fields = ["slug"]
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class TargetAudienceViewSet(ReadOnlyBaseViewSet):
    queryset = TargetAudience.objects.all()
    serializer_class = TargetAudienceSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class TypographyViewSet(ReadOnlyBaseViewSet):
    queryset = Typography.objects.all()
    serializer_class = TypographySerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class DateFormatViewSet(ReadOnlyBaseViewSet):
    queryset = DateFormat.objects.all()
    serializer_class = DateFormatSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class TextualModelViewSet(ReadOnlyBaseViewSet):
    queryset = TextualModel.objects.all()
    serializer_class = TextualModelSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class LanguageCountViewSet(ReadOnlyBaseViewSet):
    queryset = LanguageCount.objects.all()
    serializer_class = LanguageCountSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class GenderViewSet(ReadOnlyBaseViewSet):
    queryset = Gender.objects.all()
    serializer_class = GenderSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class OccupationViewSet(ReadOnlyBaseViewSet):
    queryset = Occupation.objects.all()
    serializer_class = OccupationSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class TopicViewSet(ReadOnlyBaseViewSet):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class MentionDescriptionViewSet(ReadOnlyBaseViewSet):
    queryset = MentionDescription.objects.all()
    serializer_class = MentionDescriptionSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class ProductionRoleViewSet(ReadOnlyBaseViewSet):
    queryset = ProductionRole.objects.all()
    serializer_class = ProductionRoleSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class FootnoteLocationViewSet(ReadOnlyBaseViewSet):
    queryset = FootnoteLocation.objects.all()
    serializer_class = FootnoteLocationSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class OriginalTypeViewSet(ReadOnlyBaseViewSet):
    queryset = OriginalType.objects.all()
    serializer_class = OriginalTypeSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class TranslationTypeViewSet(ReadOnlyBaseViewSet):
    queryset = TranslationType.objects.all()
    serializer_class = TranslationTypeSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class PrefaceViewSet(ReadOnlyBaseViewSet):
    queryset = Preface.objects.select_related("book", "writer")
    serializer_class = PrefaceSerializer
    filterset_fields = ["book", "writer"]
    search_fields = ["title", "book__name", "writer__pref_label"]


class ProductionViewSet(ReadOnlyBaseViewSet):
    queryset = Production.objects.select_related("book", "producer", "role")
    serializer_class = ProductionSerializer
    filterset_fields = ["book", "producer", "role"]
    search_fields = ["book__name", "producer__pref_label", "role__name"]


api_router = routers.DefaultRouter()
api_router.register(r"books", BookViewSet, basename="book")
api_router.register(r"persons", PersonViewSet, basename="person")
api_router.register(r"cities", CityViewSet, basename="city")
api_router.register(r"geolocations", GeolocationViewSet, basename="geolocation")
api_router.register(r"editions", EditionViewSet, basename="edition")
api_router.register(r"translations", TranslationViewSet, basename="translation")
api_router.register(r"mentions", MentionViewSet, basename="mention")
api_router.register(r"languages", LanguageViewSet, basename="language")
api_router.register(r"alignments", AlignmentViewSet, basename="alignment")
api_router.register(r"fonts", FontViewSet, basename="font")
api_router.register(r"publishers", PublisherViewSet, basename="publisher")
api_router.register(r"series", SeriesViewSet, basename="series")
api_router.register(r"target-audiences", TargetAudienceViewSet, basename="target-audience")
api_router.register(r"typographies", TypographyViewSet, basename="typography")
api_router.register(r"date-formats", DateFormatViewSet, basename="date-format")
api_router.register(r"textual-models", TextualModelViewSet, basename="textual-model")
api_router.register(r"language-counts", LanguageCountViewSet, basename="language-count")
api_router.register(r"genders", GenderViewSet, basename="gender")
api_router.register(r"occupations", OccupationViewSet, basename="occupation")
api_router.register(r"topics", TopicViewSet, basename="topic")
api_router.register(r"mention-descriptions", MentionDescriptionViewSet, basename="mention-description")
api_router.register(r"production-roles", ProductionRoleViewSet, basename="production-role")
api_router.register(r"footnote-locations", FootnoteLocationViewSet, basename="footnote-location")
api_router.register(r"original-types", OriginalTypeViewSet, basename="original-type")
api_router.register(r"translation-types", TranslationTypeViewSet, basename="translation-type")
api_router.register(r"prefaces", PrefaceViewSet, basename="preface")
api_router.register(r"productions", ProductionViewSet, basename="production")

# home/serializers.py

from rest_framework import serializers

from .models import (
    Book,
    Person,
    City,
    Geolocation,
    Edition,
    Translation,
    Mention,
    Language,
    Alignment,
    Font,
    Publisher,
    Series,
    TargetAudience,
    Typography,
    DateFormat,
    TextualModel,
    LanguageCount,
    Gender,
    Occupation,
    Topic,
    MentionDescription,
    ProductionRole,
    FootnoteLocation,
    OriginalType,
    TranslationType,
    Preface,
    Production,
)


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = "__all__"


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = "__all__"


class GeolocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Geolocation
        fields = "__all__"


class GenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gender
        fields = "__all__"


class OccupationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Occupation
        fields = "__all__"


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = "__all__"
        depth = 1  # Resolve gender, places, occupations as well


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = "__all__"


class SeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Series
        fields = "__all__"


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = "__all__"


class AlignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alignment
        fields = "__all__"


class FontSerializer(serializers.ModelSerializer):
    class Meta:
        model = Font
        fields = "__all__"


class TargetAudienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetAudience
        fields = "__all__"


class TypographySerializer(serializers.ModelSerializer):
    class Meta:
        model = Typography
        fields = "__all__"


class DateFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = DateFormat
        fields = "__all__"


class TextualModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextualModel
        fields = "__all__"


class LanguageCountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LanguageCount
        fields = "__all__"


class FootnoteLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FootnoteLocation
        fields = "__all__"


class OriginalTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OriginalType
        fields = "__all__"


class TranslationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranslationType
        fields = "__all__"


class MentionDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentionDescription
        fields = "__all__"


class ProductionRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionRole
        fields = "__all__"


class EditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Edition
        fields = "__all__"
        depth = 1


class TranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Translation
        fields = "__all__"
        depth = 1


class MentionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mention
        fields = "__all__"
        depth = 1


class PrefaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preface
        fields = "__all__"
        depth = 1


class ProductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Production
        fields = "__all__"
        depth = 1


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = "__all__"
        depth = 1  # Include languages, authors, places, etc.

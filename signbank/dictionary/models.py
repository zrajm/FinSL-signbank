"""Models for the Signbank dictionary database."""

import json
from collections import OrderedDict

from django.db import models, OperationalError
from django.conf import settings
from django.http import Http404
import tagging
import os
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.core.exceptions import FieldDoesNotExist

from signbank.dictionary.choicelists import *


class Translation(models.Model):
    """A first language (Finnish) translation equivalent of a sign"""

    gloss = models.ForeignKey("Gloss")
    translation = models.ForeignKey("Keyword")
    index = models.IntegerField("Index")

    def __unicode__(self):
        return self.gloss.idgloss + '-' + self.translation.text

    def get_absolute_url(self):
        """Return a URL for a view of this translation."""

        alltrans = self.translation.translation_set.all()
        idx = 0
        for tr in alltrans:
            if tr == self:
                return "/dictionary/words/" + str(self.translation) + "-" + str(idx + 1) + ".html"

            idx += 1
        return "/dictionary/"

    class Meta:
        ordering = ['gloss', 'index']

    class Admin:
        list_display = ['gloss', 'translation']
        search_fields = ['gloss__idgloss']


class TranslationEnglish(models.Model):
    """English translation equivalent of a sign"""

    gloss = models.ForeignKey("Gloss")
    translation_english = models.ForeignKey("KeywordEnglish")
    index = models.IntegerField("Index")

    def __unicode__(self):
        return self.gloss.idgloss + '-' + self.translation_english.text

    def get_absolute_url(self):
        """Return a URL for a view of this translation."""

        alltrans = self.translationenglish.translation_english_set.all()
        idx = 0
        for tr in alltrans:
            if tr == self:
                return "/dictionary/words/" + str(self.translation_english) + "-" + str(idx + 1) + ".html"

            idx += 1
        return "/dictionary/"

    class Meta:
        ordering = ['gloss', 'index']

    class Admin:
        list_display = ['gloss', 'translation_english']
        search_fields = ['gloss__idgloss']


class Keyword(models.Model):
    """A keyword that is a possible translation equivalent of a sign"""

    def __unicode__(self):
        return self.text

    text = models.CharField(max_length=100, unique=True)

    def in_web_dictionary(self):
        """Return True if some gloss associated with this
        keyword is in the web version of the dictionary"""

        return len(self.translation_set.filter(gloss__in_web_dictionary__exact=True)) != 0

    class Meta:
        ordering = ['text']

    class Admin:
        search_fields = ['text']

    def match_request(self, request, n):
        """Find the translation matching a keyword request given an index 'n'
        response depends on login status
        Returns a tuple (translation, count) where count is the total number
        of matches."""

        if request.user.has_perm('dictionary.search_gloss'):
            alltrans = self.translation_set.all()
        else:
            alltrans = self.translation_set.filter(gloss__inWeb__exact=True)

        # remove crude signs for non-authenticated users if ANON_SAFE_SEARCH is
        # on
        try:
            from tagging.models import Tag
        except ImportError:
            import tagging
        try:
            crudetag = tagging.models.Tag.objects.get(name='lexis:crude')
        except tagging.models.Tag.DoesNotExist:
            crudetag = None

        safe = (not request.user.is_authenticated()
                ) and settings.ANON_SAFE_SEARCH
        if safe and crudetag:
            alltrans = [
                tr for tr in alltrans if not crudetag in tagging.models.Tag.objects.get_for_object(tr.gloss)]

        # if there are no translations, generate a 404
        if len(alltrans) == 0:
            raise Http404

        # take the nth translation if n is in range
        # otherwise take the last
        if n - 1 < len(alltrans):
            trans = alltrans[n - 1]
        else:
            trans = alltrans[len(alltrans) - 1]

        return (trans, len(alltrans))


class KeywordEnglish(models.Model):
    """A keyword that is a possible translation equivalent of a sign"""

    def __unicode__(self):
        return self.text

    text = models.CharField(max_length=100, unique=True)

    def in_web_dictionary(self):
        """Return True if some gloss associated with this
        keyword is in the web version of the dictionary"""

        return len(self.translation_english_set.filter(gloss__in_web_dictionary__exact=True)) != 0

    class Meta:
        ordering = ['text']

    class Admin:
        search_fields = ['text']

    def match_request_english(self, request, n):
        """Find the translation matching a keyword request given an index 'n'
        response depends on login status
        Returns a tuple (translation, count) where count is the total number
        of matches."""

        if request.user.has_perm('dictionary.search_gloss'):
            alltrans = self.translation_english_set.all()
        else:
            alltrans = self.translation_english_set.filter(gloss__inWeb__exact=True)

        # remove crude signs for non-authenticated users if ANON_SAFE_SEARCH is
        # on
        try:
            from tagging.models import Tag
        except ImportError:
            import tagging

        try:
            crudetag = tagging.models.Tag.objects.get(name='lexis:crude')
        except tagging.models.Tag.DoesNotExist:
            crudetag = None

        safe = (not request.user.is_authenticated()
                ) and settings.ANON_SAFE_SEARCH
        if safe and crudetag:
            alltrans = [
                tr for tr in alltrans if not crudetag in tagging.models.Tag.objects.get_for_object(tr.gloss)]

        # if there are no translations, generate a 404
        if len(alltrans) == 0:
            raise Http404

        # take the nth translation if n is in range
        # otherwise take the last
        if n - 1 < len(alltrans):
            trans = alltrans[n - 1]
        else:
            trans = alltrans[len(alltrans) - 1]

        return (trans, len(alltrans))


DEFN_ROLE_CHOICES = (
    # Translators: DEFN_ROLE_CHOICES
    ('note', _('Note')),
    # Translators: DEFN_ROLE_CHOICES
    ('privatenote', _('Private Note')),
    # Translators: DEFN_ROLE_CHOICES
    ('phon', _('Phonology')),
    # Translators: DEFN_ROLE_CHOICES
    ('todo', _('To Do')),
    # Translators: DEFN_ROLE_CHOICES
    ('sugg', _('Suggestion for other gloss')),
)


class Definition(models.Model):
    """An English text associated with a gloss. It's called a note in the web interface"""

    def __unicode__(self):
        return unicode(self.gloss) + "/" + unicode(self.role)

    gloss = models.ForeignKey("Gloss")
    text = models.TextField()
    role = models.CharField("Type", max_length=20, choices=DEFN_ROLE_CHOICES)
    count = models.IntegerField()
    published = models.BooleanField(default=True)

    class Meta:
        ordering = ['gloss', 'role', 'count']

    class Admin:
        list_display = ['gloss', 'role', 'count', 'text']
        list_filter = ['role']
        search_fields = ['gloss__idgloss']


class Language(models.Model):
    """A sign language name"""

    class Meta:
        ordering = ['name']

    name = models.CharField(max_length=50)
    description = models.TextField()

    def __unicode__(self):
        return unicode(self.name)


class Dialect(models.Model):
    """A dialect name - a regional dialect of a given Language"""

    class Meta:
        ordering = ['language', 'name']

    language = models.ForeignKey(Language)
    name = models.CharField(max_length=50)
    description = models.TextField()

    def __unicode__(self):
        return unicode(self.language.name) + "/" + unicode(self.name)


class RelationToForeignSign(models.Model):
    """Defines a relationship to another sign in another language (often a loan)"""

    def __unicode__(self):
        return unicode(self.gloss) + "/" + unicode(self.other_lang) + ',' + unicode(self.other_lang_gloss)

    gloss = models.ForeignKey("Gloss")
    # Translators: RelationToForeignSign field verbose name
    loan = models.BooleanField(_("Loan Sign"), default=False)
    # Translators: RelationToForeignSign field verbose name
    other_lang = models.CharField(_("Related Language"), max_length=20)
    # Translators: RelationToForeignSign field verbose name
    other_lang_gloss = models.CharField(
        _("Gloss in related language"), max_length=50)

    class Meta:
        ordering = ['gloss', 'loan', 'other_lang', 'other_lang_gloss']

    class Admin:
        list_display = ['gloss', 'loan', 'other_lang', 'other_lang_gloss']
        list_filter = ['other_lang']
        search_fields = ['gloss__idgloss']


class FieldChoice(models.Model):
    field = models.CharField(max_length=50)
    english_name = models.CharField(max_length=50)
    machine_value = models.IntegerField(unique=True)

    def __unicode__(self):
        # return self.field + ': ' + self.english_name + ' (' + str(self.machine_value) + ')'
        return unicode(self.english_name)

    class Meta:
        ordering = ['field', 'machine_value']


# This method builds a list of choices from the database
def build_choice_list(field):
    # choice_list = [('0', '-'), ('1', 'N/A')]
    choice_list = []

    # Try to look for fields in FieldName and choose choices from there

    try:
        for choice in FieldChoice.objects.filter(field=field):
            choice_list.append((str(choice.machine_value), choice.english_name))

        return choice_list

        # Enter this exception if for example the db has no data yet (without this it is impossible to migrate)
    except OperationalError:
        pass
    return choice_list


# This method gets choices from FieldChoice and returns them as a dict
def get_choices(field):
    choice_list = []
    try:
        for choice in FieldChoice.objects.filter(field=field):
            choice_list.append((str(choice.machine_value), choice.english_name))

        return choice_list

        # Enter this exception if for example the db has no data yet (without this it is impossible to migrate)
    except OperationalError:
        pass
    return choice_list


def get_choices_with_int(field):
    choice_list = []
    try:
        for choice in FieldChoice.objects.filter(field=field):
            choice_list.append((choice.machine_value, choice.english_name))

        return choice_list

        # Enter this exception if for example the db has no data yet (without this it is impossible to migrate)
    except OperationalError:
        pass
    return choice_list


class Gloss(models.Model):
    class Meta:
        # Translators: This is verbose_name_plural, so it has to be plural here
        verbose_name_plural = _("Glosses")
        ordering = ['idgloss']
        permissions = (
            # Translators: Gloss permissions
            ('update_video', _("Can Update Video")),
            # Translators: Gloss permissions
            ('search_gloss', _('Can Search/View Full Gloss Details')),
            # Translators: Gloss permissions
            ('export_csv', _('Can export sign details as CSV')),
            # Translators: Gloss permissions
            ('can_publish', _('Can publish signs and definitions')),
            # Translators: Gloss permissions
            ('can_delete_unpublished', _('Can delete unpub signs or defs')),
            # Translators: Gloss permissions
            ('can_delete_published', _('Can delete pub signs and defs')),
            # Translators: Gloss permissions
            ('view_advanced_properties', _('Include all properties in sign detail view')),
            # Translators: Gloss permissions
            ('lock_gloss', _('Can lock and unlock Gloss from editing')),
        )

    def __unicode__(self):
        return "%s" % (unicode(self.idgloss))

    def field_labels(self):
        """Return the dictionary of field labels for use in a template"""

        d = dict()
        for f in self._meta.fields:
            try:
                d[f.name] = self._meta.get_field(f.name).verbose_name
            except FieldDoesNotExist:
                pass

        return d

    def admin_fields(self):
        """Return a list of field values in settings.ADMIN_RESULT_FIELDS 
        for use in the admin list view"""

        result = []
        for field in settings.ADMIN_RESULT_FIELDS:
            fname = self._meta.get_field(field).verbose_name

            # First, try to give the human readable choice value back
            try:
                result.append(
                    (fname, getattr(self, 'get_' + field + '_display')()))

            # If that doesn't work, give the raw value back
            except AttributeError:
                result.append((fname, getattr(self, field)))

        return result

    ### Fields begin ###

    locked = models.BooleanField(_("Locked"), default=False)

    # Translators: Gloss models field: idgloss, verbose name
    idgloss = models.CharField(_("Gloss"), max_length=60,
                               # Translators: Help text for Gloss models field: idgloss
                               help_text=_("""
    This is the unique identifying name of an entry of a sign form in the
database. No two Sign Entry Names can be exactly the same, but a "Sign
Entry Name" can be (and often is) the same as the Annotation Idgloss."""))

    # Changed this Gloss to be for the University of Jyvaskyla folks
    # Translators: Gloss models field: annotation_idgloss_jkl, verbose name
    annotation_idgloss_jkl = models.CharField(_("Gloss JKL"), blank=True, max_length=60,
                                              # Translators: Help text for Gloss models field: annotation_idgloss_jkl
                                              help_text=_("""
    This is the Jyvaskyla name of a sign used by annotators when glossing the corpus in
an ELAN annotation file. The Jyvaskyla Annotation Idgloss may be the same for two or
more entries (each with their own 'Sign Entry Name'). If two sign entries
have the same 'Annotation Idgloss' that means they differ in form in only
minor or insignificant ways that can be ignored."""))
    # the idgloss used in transcription, may be shared between many signs

    # ID gloss for JKL Gloss' translation to English
    # Translators: Gloss models field: annotation_idgloss_jkl_en (english), verbose name
    annotation_idgloss_jkl_en = models.CharField(_("Gloss JKL (Eng)"), blank=True, max_length=60,
                                                 # Translators: Help text for Gloss models field: annotation_idgloss_jkl_en (english)
                                                 help_text=_("""
    This is the English name for the corresponding Jyvaskyla Gloss"""))

    # Changed this Gloss to be for the Helsinki folks
    # Translators: Gloss models field: annotation_idgloss_hki, verbose name
    annotation_idgloss_hki = models.CharField(_("Gloss HKI"), blank=True, max_length=60,
                                              # Translators: Help text for Gloss models field: annotation_idgloss_hki
                                              help_text=_("""
    This is the Helsinki name of a sign used by annotators when glossing the corpus in
an ELAN annotation file. The Helsinki Annotation Idgloss may be the same for two or
more entries (each with their own 'Sign Entry Name'). If two sign entries
have the same 'Annotation Idgloss' that means they differ in form in only
minor or insignificant ways that can be ignored."""))

    # ID Gloss for HKI gloss translation to English
    # Translators: Gloss models field: annotation_idgloss_hki_en (english), verbose name
    annotation_idgloss_hki_en = models.CharField(_("Gloss HKI (Eng)"), blank=True, max_length=60,
                                                 # Translators: Help text for Gloss models field: annotation_id_gloss_hki_en (english)
                                                 help_text=_("""
    This is the English name for the corresponding Jyvaskyla Gloss"""))

    # Languages that this gloss is part of
    language = models.ManyToManyField(Language, blank=True)

    # Translators: Gloss models field: annotation_comments, verbose name
    annotation_comments = models.CharField(
        _("Comments"), max_length=200, blank=True)

    # Translators: Gloss models field: url
    url_field = models.URLField(_("URL"), max_length=200, blank=True, unique=False)

    ########

    # One or more regional dialects that this gloss is used in
    dialect = models.ManyToManyField(Dialect, blank=True)
    # This field type is a guess.

    # Fields representing creation time, updated_at time, creator and updater
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name='created_by_user')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, related_name='updated_by_user')

    # ### Phonology fields
    # Translators: Gloss models field: handedness, verbose name
    # handedness = models.CharField(_("Handedness"), blank=True, null=True, choices=build_choice_list("handedness"),
    #                               max_length=5)  # handednessChoices <- use this if you want static
    handedness = models.ForeignKey('FieldChoice', verbose_name=_("Handedness"), to_field='machine_value',
                                   db_column='handedness', limit_choices_to={'field': 'handedness'},
                                   related_name="handedness", blank=True, null=True)
    # Translators: Gloss models field: strong_handshape, verbose name
    # strong_handshape = models.CharField(_("Strong Hand"), blank=True, null=True, choices=build_choice_list("handshape"),
    #                                     max_length=5)
    strong_handshape = models.ForeignKey('FieldChoice', verbose_name=_("Strong Hand"), to_field='machine_value',
                                         db_column='strong_handshape', limit_choices_to={'field': 'strong_handshape'},
                                         related_name="strong_handshape", blank=True, null=True)

    # Translators: Gloss models field: weak_handshape, verbose name
    # weak_handshape = models.CharField(_("Weak Hand"), null=True, choices=build_choice_list("handshape"), blank=True,
    #                                  max_length=5)
    weak_handshape = models.ForeignKey('FieldChoice', verbose_name=_("Weak Hand"), to_field='machine_value',
                                       db_column='weak_handshape', limit_choices_to={'field': 'weak_handshape'},
                                       related_name="weak_handshape", blank=True, null=True)

    # Translators: Gloss models field: location, verbose name
    # location = models.CharField(
    #     _("Location"), choices=build_choice_list("location"), null=True, blank=True, max_length=20)
    location = models.ForeignKey('FieldChoice', verbose_name=_("Location"), to_field='machine_value',
                                 db_column='location', limit_choices_to={'field': 'location'}, related_name="location",
                                 blank=True, null=True)

    # Translators: Gloss models field: relation_between_articulators, verbose name
    # relation_between_articulators = models.CharField(
    #    _("Relation between Articulators"), choices=build_choice_list("relation_between_articulators"),
    #    null=True, blank=True, max_length=5)
    relation_between_articulators = models.ForeignKey('FieldChoice', verbose_name=_("Relation Between Articulators"),
                                                      to_field='machine_value',
                                                      db_column='relation_between_articulators',
                                                      limit_choices_to={'field': 'relation_between_articulators'},
                                                      related_name="relation_between_articulators", blank=True,
                                                      null=True)

    # Translators: Gloss models field: absolute_orientation_palm, verbose name
    # absolute_orientation_palm = models.CharField(_("Absolute Orientation: Palm"),
    #                                             choices=build_choice_list("relation_between_articulators"), null=True,
    #                                             blank=True, max_length=5)
    absolute_orientation_palm = models.ForeignKey('FieldChoice', verbose_name=_("Absolute Orientation: Palm"),
                                                  to_field='machine_value', db_column='absolute_orientation_palm',
                                                  limit_choices_to={'field': 'absolute_orientation_palm'},
                                                  related_name="absolute_orientation_palm", blank=True, null=True)
    # Translators: Gloss models field: absolute_orientation_fingers, verbose name
    # absolute_orientation_fingers = models.CharField(_("Absolute Orientation: Fingers"),
    #                                                choices=build_choice_list("absolute_orientation_fingers"),
    #                                                null=True,
    #                                                blank=True, max_length=5)
    absolute_orientation_fingers = models.ForeignKey('FieldChoice', verbose_name=_("Absolute Orientation: Fingers"),
                                                     to_field='machine_value', db_column='absolute_orientation_fingers',
                                                     limit_choices_to={'field': 'absolute_orientation_fingers'},
                                                     related_name="absolute_orientation_fingers", blank=True, null=True)

    # Translators: Gloss models field: relative_orientation_movement, verbose name
    # relative_orientation_movement = models.CharField(_("Relative Orientation: Movement"),
    #                                                 choices=build_choice_list("relative_orientation_movement"),
    #                                                 null=True,
    #                                                 blank=True, max_length=5)
    relative_orientation_movement = models.ForeignKey('FieldChoice', verbose_name=_("Relative Orientation: Movement"),
                                                      to_field='machine_value',
                                                      db_column='relative_orientation_movement',
                                                      limit_choices_to={'field': 'relative_orientation_movement'},
                                                      related_name="relative_orientation_movement", blank=True,
                                                      null=True)
    # Translators: Gloss models field: relative_orientation_location, verbose name
    # relative_orientation_location = models.CharField(_("Relative Orientation: Location"),
    #                                                 choices=build_choice_list("relative_orientation_location"),
    #                                                 null=True,
    #                                                 blank=True, max_length=5)
    relative_orientation_location = models.ForeignKey('FieldChoice', verbose_name=_("Relative Orientation: Location"),
                                                      to_field='machine_value',
                                                      db_column='relative_orientation_location',
                                                      limit_choices_to={'field': 'relative_orientation_location'},
                                                      related_name="relative_orientation_location", blank=True,
                                                      null=True)
    # Translators: Gloss models field: orientation_change, verbose name
    # orientation_change = models.CharField(_("Orientation Change"), choices=build_choice_list("orientation_change"),
    #                                      null=True, blank=True,
    #                                      max_length=5)
    orientation_change = models.ForeignKey('FieldChoice', verbose_name=_("Orientation Change"),
                                           to_field='machine_value', db_column='orientation_change',
                                           limit_choices_to={'field': 'orientation_change'},
                                           related_name="orientation_change", blank=True, null=True)

    # Translators: Gloss models field: handshape_change, verbose name
    # handshape_change = models.CharField(_("Handshape Change"), choices=build_choice_list("handshape_change"), null=True,
    #                                    blank=True,
    #                                    max_length=5)
    handshape_change = models.ForeignKey('FieldChoice', verbose_name=_("Handshape Change"), to_field='machine_value',
                                         db_column='handshape_change', limit_choices_to={'field': 'handshape_change'},
                                         related_name="handshape_change", blank=True, null=True)

    # Translators: Gloss models field: repeated_movement, verbose name
    repeated_movement = models.NullBooleanField(_("Repeated Movement"), null=True, default=False)
    # Translators: Gloss models field: alternating_movement, verbose name
    alternating_movement = models.NullBooleanField(_("Alternating Movement"), null=True, default=False)

    # Translators: Gloss models field: movement_shape, verbose name
    # movement_shape = models.CharField(_("Movement Shape"), choices=build_choice_list("movement_shape"), null=True,
    #                                  blank=True,
    #                                  max_length=5)
    movement_shape = models.ForeignKey('FieldChoice', verbose_name=_("Movement Shape"), to_field='machine_value',
                                       db_column='movement_shape', limit_choices_to={'field': 'movement_shape'},
                                       related_name="movement_shape", blank=True, null=True)
    # Translators: Gloss models field: movement_direction, verbose name
    # movement_direction = models.CharField(_("Movement Direction"), choices=build_choice_list("movement_direction"),
    #                                      null=True, blank=True,
    #                                      max_length=5)
    movement_direction = models.ForeignKey('FieldChoice', verbose_name=_("Movement Direction"),
                                           to_field='machine_value', db_column='movement_direction',
                                           limit_choices_to={'field': 'movement_direction'},
                                           related_name="movement_direction", blank=True, null=True)
    # Translators: Gloss models field: movement_manner, verbose name
    # movement_manner = models.CharField(_("Movement Manner"), choices=build_choice_list("movement_manner"), null=True,
    #                                   blank=True,
    #                                   max_length=5)
    movement_manner = models.ForeignKey('FieldChoice', verbose_name=_("Movement Manner"), to_field='machine_value',
                                        db_column='movement_manner', limit_choices_to={'field': 'movement_manner'},
                                        related_name="movement_manner", blank=True, null=True)
    # Translators: Gloss models field: contact_type, verbose name
    # contact_type = models.CharField(_("Contact Type"), choices=build_choice_list("contact_type"), null=True, blank=True,
    #                                max_length=5)
    contact_type = models.ForeignKey('FieldChoice', verbose_name=_("Contact Type"), to_field='machine_value',
                                     db_column='contact_type', limit_choices_to={'field': 'contact_type'},
                                     related_name="contact_type", blank=True, null=True)

    # Translators: Gloss models field: phonology_other verbose name
    phonology_other = models.TextField(_("Phonology Other"), null=True, blank=True)

    # Translators: Gloss models field: mouth_gesture, verbose name
    mouth_gesture = models.CharField(_("Mouth Gesture"), max_length=50, blank=True)
    # Translators: Gloss models field: mouthing, verbose name
    mouthing = models.CharField(_("Mouthing"), max_length=50, blank=True)
    # Translators: Gloss models field: phonetic_variation, verbose name
    phonetic_variation = models.CharField(_("Phonetic Variation"), max_length=50, blank=True, )

    # ### Semantic fields
    # Translators: Gloss models field: iconic_image, verbose name
    iconic_image = models.CharField(_("Iconic Image"), max_length=50, blank=True)
    # Translators: Gloss models field: named_entity, verbose name
    # named_entity = models.CharField(_("Named Entity"), choices=build_choice_list("named_entity"), null=True, blank=True,
    #                                max_length=5)
    named_entity = models.ForeignKey('FieldChoice', verbose_name=_("Named Entity"), to_field='machine_value',
                                     db_column='named_entity', limit_choices_to={'field': 'named_entity'},
                                     related_name="named_entity", blank=True, null=True)
    # Translators: Gloss models field: semantic_field, verbose name
    # semantic_field = models.CharField(_("Semantic Field"), choices=build_choice_list("semantic_field"), null=True,
    #                                  blank=True,
    #                                  max_length=5)
    semantic_field = models.ForeignKey('FieldChoice', verbose_name=_("Semantic Field"), to_field='machine_value',
                                       db_column='semantic_field', limit_choices_to={'field': 'semantic_field'},
                                       related_name="semantic_field", blank=True, null=True)

    # ### Frequency fields
    # Translators: Gloss models field_ number_of_occurences, verbose name
    number_of_occurences = models.IntegerField(
        _("Number of Occurrences"), null=True, blank=True,
        # Translators: Help text for Gloss models field: number_of_occurences
        help_text=_("Number of occurences in annotation materials"))

    # ### Publication status
    # Translators: Gloss models field: in_web_dictionary, verbose name
    in_web_dictionary = models.NullBooleanField(_("In the Web dictionary"), default=False)
    # Translators: Gloss models field: is_proposed_new_sign, verbose name
    is_proposed_new_sign = models.NullBooleanField(
        _("Is this a proposed new sign?"), null=True, default=False)

    def get_fields(self):
        return [(field.name, field.value_to_string(self)) for field in Gloss._meta.fields]


    def get_absolute_url(self):
        """Returns an url with the gloss name (ending with .html), used for 'public view' of gloss @ word template"""
        return "/dictionary/gloss/%s.html" % self.idgloss

    def get_video_gloss(self):
        # This method was used for finding a gloss that has the video TODO: Can this be removed?
        return self

    def get_video(self):
        """Return the video object for this gloss or None if no video available"""

        video_path = self.get_video_path()

        #if os.path.isfile(settings.MEDIA_ROOT + '/' + video_path):
        if os.path.isfile(os.path.join(settings.MEDIA_ROOT, video_path)):
            return video_path
        else:
            return None


    def get_video_path(self):
        """return 'glossvideo/' + \
                     unicode(self.idgloss[:2]) + '/' + unicode(self.idgloss) + '-' + unicode(self.pk) + '.mp4'"""
        return os.path.join('glossvideo',unicode(self.idgloss[:2]), (unicode(self.idgloss)+'-'+unicode(self.pk)+'.mp4'))

    def count_videos(self):
        """Return a count of the number of videos we have 
        for this video - ie. the number of versions stored"""

        video_with_gloss = self.get_video_gloss()
        return video_with_gloss.glossvideo_set.count()

    def get_video_url(self):
        """Return  the url of the video for this gloss"""

        #return '/home/wessel/signbank/signbank/video/testmedia/AANBELLEN-320kbits.mp4'  # TODO: Remove this line?
        video = self.get_video()
        if video is not None:
            # return video.get_absolute_url()
            return self.get_absolute_url()
        else:
            return ""


    def get_video_id(self):
        """Returns video.glossvideo.id"""
        from signbank.video.models import GlossVideo
        return GlossVideo.objects.get(gloss=self,version=0).id

    def has_video(self):
        """Test to see if the video for this sign is present"""

        return self.get_video() is not None

    def published_definitions(self):
        """Return a query set of just the published definitions for this gloss
        also filter out those fields not in DEFINITION_FIELDS"""

        defs = self.definition_set.filter(published__exact=True)

        return [d for d in defs if d.role in settings.DEFINITION_FIELDS]

    def definitions(self):
        """Gather together the definitions for this gloss"""

        defs = dict()
        for d in self.definition_set.all().order_by('count'):
            if not defs.has_key(d.role):
                defs[d.role] = []

            defs[d.role].append(d.text)
        return defs

    def options_to_json(self, options):
        """Convert an options list to a json dict"""

        result = []
        for k, v in options:
            result.append('"%s":"%s"' % (k, v))
        return "{" + ",".join(result) + "}"

    def handshape_choices_json(self):
        """Return JSON for the handshape choice list"""

        return self.options_to_json(handshape_choices)

    def location_choices_json(self):
        """Return JSON for the location choice list"""

        return self.options_to_json(location_choices)

    def palm_orientation_choices_json(self):
        """Return JSON for the palm orientation choice list"""

        return self.options_to_json(palm_orientation_choices)

    def relative_orientation_choices_json(self):
        """Return JSON for the relative orientation choice list"""

        return self.options_to_json(relative_orientation_choices)

    def secondary_location_choices_json(self):  # TODO: see if these can be removed
        """Return JSON for the secondary location (BSL) choice list"""

        return self.options_to_json(BSLsecondLocationChoices)

    def definition_role_choices_json(self):
        """Return JSON for the definition role choice list"""

        return self.options_to_json(DEFN_ROLE_CHOICES)

    def relation_role_choices_json(self):
        """Return JSON for the relation role choice list"""

        return self.options_to_json(RELATION_ROLE_CHOICES)

    def language_choices(self):
        """Return JSON for langauge choices"""

        d = dict()
        for l in Language.objects.all():
            d[l.name] = l.name

        return json.dumps(d)

    @staticmethod
    def dialect_choices():
        """Return JSON for dialect choices"""

        d = dict()
        for l in Dialect.objects.all():
            d[l.name] = l.name

        return json.dumps(d)

    @staticmethod
    def get_choice_lists():
        """Return JSON for the location choice list"""

        choice_lists = {}

        # Start with your own choice lists
        for fieldname in ['handedness', 'location', 'strong_handshape', 'weak_handshape',
                          'relation_between_articulators', 'absolute_orientation_palm', 'absolute_orientation_fingers',
                          'relative_orientation_movement', 'relative_orientation_location', 'handshape_change',
                          'repeated_movement', 'alternating_movement', 'movement_shape', 'movement_direction',
                          'movement_manner', 'contact_type', 'named_entity', 'orientation_change', 'semantic_field']:
            # Get the list of choices for this field
            # li = self._meta.get_field(fieldname).choices
            li = get_choices(fieldname)

            # Sort the list
            sorted_li = sorted(li, key=lambda x: x[1])

            # Put it in another format
            reformatted_li = [('_' + str(value), text)
                              for value, text in sorted_li]
            choice_lists[fieldname] = OrderedDict(reformatted_li)

        # Choice lists for other models
        # choice_lists['morphology_role'] = [human_value for machine_value, human_value in
        #                                   build_choice_list('MorphologyType')]
        choice_lists['morphology_role'] = get_choices('MorphologyType')
        reformatted_morph_role = [('_' + str(value), text)
                                  for value, text in choice_lists['morphology_role']]
        choice_lists['morphology_role'] = OrderedDict(reformatted_morph_role)
        # morphology_role
        return json.dumps(choice_lists)

# Register Gloss for tags
try:
    tagging.register(Gloss)
except tagging.AlreadyRegistered:
    pass

RELATION_ROLE_CHOICES = (
    # Translators: RELATION_ROLE_CHOICES
    ('homonym', _('Homonym')),
    # Translators: RELATION_ROLE_CHOICES
    ('synonym', _('Synonym')),
    # Translators: RELATION_ROLE_CHOICES
    ('variant', _('Variant')),
    # Translators: RELATION_ROLE_CHOICES
    ('antonym', _('Antonym')),
    # Translators: RELATION_ROLE_CHOICES
    ('hyponym', _('Hyponym')),
    # Translators: RELATION_ROLE_CHOICES
    ('hypernym', _('Hypernym')),
    # Translators: RELATION_ROLE_CHOICES
    ('seealso', _('See Also')),
)


class Relation(models.Model):
    """A relation between two glosses"""

    source = models.ForeignKey(Gloss, related_name="relation_sources")
    target = models.ForeignKey(Gloss, related_name="relation_targets")
    # role = models.CharField(max_length=20, choices=build_choice_list('MorphologyType'))
    role = models.ForeignKey('FieldChoice', to_field='machine_value', db_column='MorphologyType',
                             limit_choices_to={'field': 'MorphologyType'}, blank=True)
    # antonym, synonym, cf (what's this? - see also), var[b-f]
    # (what's this - variant (XXXa is the stem, XXXb is a variant)

    class Admin:
        list_display = ['source', 'role', 'target']
        search_fields = ['source__idgloss', 'target__idgloss']

    class Meta:
        ordering = ['source']


class MorphologyDefinition(models.Model):
    """Tells something about morphology of a gloss"""

    parent_gloss = models.ForeignKey(Gloss, related_name="parent_glosses")
    # role = models.CharField(max_length=5, choices=(build_choice_list('MorphologyType')))
    role = models.ForeignKey('FieldChoice', to_field='machine_value', db_column='MorphologyType',
                             limit_choices_to={'field': 'MorphologyType'}, blank=True)
    morpheme = models.ForeignKey(Gloss, related_name="morphemes")

    def __unicode__(self):
        # return unicode(self.morpheme.idgloss) + ' is ' + unicode(self.get_role_display()) + ' of ' + unicode(
        #    self.parent_gloss.idgloss)
        return unicode(
            self.morpheme.idgloss + ' is ' + unicode(self.role) + ' of ' + unicode(self.parent_gloss.idgloss))

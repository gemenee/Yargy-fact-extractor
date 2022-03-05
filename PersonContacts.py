#!/usr/bin/env python
# coding: utf-8

from natasha.grammars.name import NAME
from yargy.relations import gnc_relation

from yargy import (
    Parser,
    or_,
    not_,
    rule
)
from yargy.pipelines import morph_pipeline
from yargy.predicates import (
    eq, in_, dictionary,
    type, gram, is_capitalized, is_upper
)
from yargy.tokenizer import MorphTokenizer
from yargy import interpretation as interp
from yargy.interpretation import fact, attribute

from yargy.tokenizer import EMAIL_RULE, PHONE_RULE

gnc = gnc_relation()

tokenizer = MorphTokenizer().add_rules(EMAIL_RULE, PHONE_RULE)

#Defining basic rules for grammemes and digits
INT = rule(type('INT'))
NOUN = gram('NOUN')
ADJF = gram('ADJF')
ADVB = gram('ADVB')
PRTF = gram('PRTF')
NUMR = gram('NUMR')
GENT = gram('gent')
DOT = eq('.')
COMMA = eq(',')
PUNCT = rule(type('PUNCT'))
GEOX = rule(gram('Geox'))

from yargy.record import Record
class Synonyms(Record):
    __attributes__ = ['name', 'synonyms']
    
    def __init__(self, name, synonyms=()):
        self.name = name
        self.synonyms = synonyms

ORG_NAMES = [
    Synonyms('Министерство обороны', ['МО', 'минобороны']),
    Synonyms('Министерство внутренних дел', ['МВД', 'полиция']),
    Synonyms('Министерство зравоохранения', ['минздрав']),
    Synonyms('Министерство науки и высшего образования Российской Федерации', ['минобрнауки']),
    Synonyms('Пенсионный фонд', ['ПФРФ', 'ПФ РФ', 'Пенсионный фонд России'])
    ]

mapping = {}

def fill_synonyms(ORG_NAMES):
    org_names = []
    for record in ORG_NAMES:
        name = record.name
        org_names.append(name)
        mapping[name] = name
        for synonym in record.synonyms:
            org_names.append(synonym)
            mapping[synonym] = name
    return org_names

org_names = fill_synonyms(ORG_NAMES)

Organization = fact(
    'Organization',
    ['unit', 'org_name']
)

ORG_NAME = morph_pipeline(org_names).interpretation(
    Organization.org_name.normalized()
)

Modifier = fact('Modifier', ['value'])
Subdivision = fact('Subdivision', ['modifier', 'subdiv_type'])

SUBDIVISION_TYPE = morph_pipeline([
    'управление',
    'отдел',
    'отделение',
    'служба',
    'центр',
    'департамент',
    'агентство',
    'сектор',
    'участок',
    'лаборатория',
    'институт',
    'университет'
]).interpretation(Subdivision.subdiv_type.normalized())

Number = fact(
    'Number',
    ['value']
)

NUMBER = rule(
    or_(INT, rule(NUMR)).interpretation(Number.value)
).interpretation(Number)

Adjs = fact(
    'Adjs',
    [attribute('parts').repeatable()]
)

ADJ = or_(
    rule(or_(ADJF, PRTF)),
    rule(ADVB, PUNCT,ADJF)
         ).interpretation(
    interp.normalized()
).interpretation(
    Adjs.parts
)

ADJS = ADJ.repeatable(max=3).interpretation(
    Adjs
)

MODIFIER = rule(or_(
    ADJS,
    NUMBER
).interpretation(
    Modifier.value
)).interpretation(Subdivision.modifier)

SUBDIVISION = or_(rule(MODIFIER, SUBDIVISION_TYPE),
                  SUBDIVISION_TYPE
                 ).interpretation(Subdivision)

Unit = fact('Unit', [attribute('parts').repeatable()])

UNIT = SUBDIVISION.interpretation(Unit.parts).repeatable().interpretation(Unit)
UNIT = UNIT.interpretation(Organization.unit)
ORGANIZATION = or_(
    rule(UNIT, ORG_NAME),
    rule(ORG_NAME),
    rule(UNIT)
).interpretation(
    Organization
)

Contacts = fact('Contacts', ['phone', 'email'])
PHONE = rule(type('PHONE')).interpretation(Contacts.phone)
EMAIL = rule(type('EMAIL')).interpretation(Contacts.email)
CONTACTS = rule(or_(rule(PHONE, PUNCT, EMAIL),
                    rule(EMAIL, PHONE),
                   rule(PHONE),
                   rule(EMAIL))).interpretation(Contacts)
 
Person = fact(
    'Person',
    ['position', 'organization', 'name', 'contacts']
)

Position = fact('Position', [attribute('prefix'), attribute('value', 'сотрудник')])

POSITION_NAMES = {
    'сотрудник',
    'офицер',
    'глава',
    'руководитель',
    'начальник',
    'оперуполномоченный',
    'детектив',
    'водитель',
    'директор',
    'преподаватель'
}

POSITION_NAME = dictionary(POSITION_NAMES).interpretation(Position.value)

PREFIX = morph_pipeline(
    ['старший',
     'заместитель',
     'главный',
     'первый',
     'второй',
     'первый заместитель',
     'генеральный',
     'исполнительный',
     'ведущий',
     'оперативный'
    ]).interpretation(Position.prefix)

POSITION = rule(PREFIX.optional(),
                POSITION_NAME
               ).interpretation(Position)

PERSON = rule(
    POSITION.optional().interpretation(
        Person.position
    ).match(gnc),
    ORGANIZATION.optional().interpretation(
        Person.organization
    ),
    NAME.interpretation(
        Person.name
    ),
    CONTACTS.interpretation(Person.contacts)
).interpretation(
    Person
)

parser = Parser(PERSON, tokenizer)
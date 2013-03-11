from mongoengine import *

class SemsiDocument(Document):
    id = StringField(unique=True, primary_key=True)
    title = StringField(required=True)
    text = StringField(required=True)

    index = StringField(required=True)
    indexed = BooleanField(default=False)
    tags = ListField(StringField())
    time_added = DateTimeField()

    meta = {
        'indexes': ['index']
    }
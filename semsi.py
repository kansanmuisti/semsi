from flask import Blueprint, Flask, Response, request, jsonify, make_response
from flask.ext import restful
from flask.ext.restful import fields, reqparse, abort
from mongoengine import connect
from simserver import SessionServer
from gensim import utils
from lexicon.stemming import Stemmer
from models import SemsiDocument

MAX_DOCUMENT_LENGTH = 200000

app = Flask(__name__)
api = restful.Api(app)

stemmer = Stemmer(language="fi")

def tokenize(s):
    return stemmer.convert_string(s)

class StemResource(restful.Resource):
    def stem(self, text):
        text = text.strip()
        if len(text) > MAX_DOCUMENT_LENGTH:
            err = 'Document too big (max. %d chars)' % MAX_DOCUMENT_LENGTH
            return make_response(err, 400)
        if not text:
            return {'response': ''}
        ret = {'response': tokenize(text)}
        return ret

    def post(self):
        d = request.form['text']
        return self.stem(d)
    def get(self):
        d = request.args['text']
        return self.stem(d)

api.add_resource(StemResource, '/stem')

def check_fields(fields, d):
    if not d:
        abort(400, message="Required fields not present")
    for f in fields:
        if f not in d:
            abort(400, message="Field '%s' not present" % f)

INDEXES = ('kamu', 'am')

def make_corpus(doc):
    ret = {'id': doc.id, 'tokens': tokenize(doc.text)}
    return ret

class DocumentResource(restful.Resource):
    def post(self):
        json = request.json
        check_fields(('text', 'id', 'title', 'url', 'index'), json)
        created = False
        doc_id = unicode(json['id'])
        try:
            doc = SemsiDocument.objects.get(id=doc_id)
        except SemsiDocument.DoesNotExist:
            doc = SemsiDocument(id=doc_id)
            created = True
        doc.text = json['text']
        doc.title = json['title']
        doc.url = json['url']
        if not json['index'] in INDEXES:
            abort(404, message="Index '%s' not found" % json['index'])
        doc.index = json['index']
        doc.save()
        if 'train' in json and not doc.indexed:
            ss = simservers[json['index']]
            ss.index([make_corpus(doc)])
            doc.indexed = True
            doc.save()
        return {'created': created}, 200

api.add_resource(DocumentResource, '/doc')

class IndexResource(restful.Resource):
    def post(self, index):
        json = request.json
        if not index in INDEXES:
            abort(404, message="Index '%s' not found" % index)
        train = json.get('train', False)

        ss = simservers[index]
        corpus = []
        docs = SemsiDocument.objects.filter(index=index)
        # If it's an indexing operation, we choose only the non-indexed docs.
        if not train:
            docs = docs.filter(indexed=False)

        for idx, doc in enumerate(docs):
            corpus.append(make_corpus(doc))
        if train:
            ss.train(corpus, method='lsi')
            action = "training"
        else:
            ss.index(corpus)
            docs.update(set__indexed=True)
            action = "indexing"
        return {'message': '%s completed with %d documents' % (action, len(corpus))}

    def delete(self, index):
        if not index in INDEXES:
            abort(404, message="Index '%s' not found" % index)
        ss = simservers[index]
        ss.drop_index()
        SemsiDocument.objects.filter(index=index).update(set__indexed=False)
        return {'message': 'index %s deleted' % index}

api.add_resource(IndexResource, '/index/<string:index>')

# args: threshold, limit
class DocumentSimilarityResource(restful.Resource):
    def get(self, index):
        json = request.json
        check_fields(('text',), json)
        if not index in INDEXES:
            abort(404, message="Index '%s' not found" % index)
        ss = simservers[index]
        if not ss.stable.fresh_index:
            abort(404, message="Index '%s' empty" % index)
        text = json['text'].strip()
        tokens = tokenize(text)
        res_list = ss.find_similar({'tokens': tokens}, max_results=10)
        id_list = [x[0] for x in res_list]
        docs = SemsiDocument.objects.filter(id__in=id_list)
        doc_dict = {}
        for doc in docs:
            doc_dict[doc.id] = doc
        doc_list = []
        for r in res_list:
            doc = doc_dict[r[0]]
            d = {'id': doc.id, 'title': doc.title, 'summary': doc.text[0:200], 'relevance': r[1]}
            doc_list.append(d)
        return doc_list

api.add_resource(DocumentSimilarityResource, '/index/<string:index>/similar')

connect('semsi')

simservers = {}
for idx in INDEXES:
    simservers[idx] = SessionServer('/tmp/%s_index' % idx)

if __name__ == "__main__":
    app.run(debug=True)

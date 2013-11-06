import os

from flask import Blueprint, Flask, Response, request, jsonify, make_response
from flask.ext import restful
from flask.ext.restful import fields, reqparse, abort
from mongoengine import connect, ValidationError
from simserver import SessionServer
from gensim import utils
from lexicon.stemming import Stemmer
from models import SemsiDocument

from local_settings import *

MAX_DOCUMENT_LENGTH = 200000

app = Flask(__name__)
api = restful.Api(app)

stemmer = Stemmer(language="fi")

CORS_HEADERS = [
    ("Access-Control-Allow-Origin", "*"),
    ("Access-Control-Allow-Methods", ', '.join(["GET", "POST", "DELETE", "OPTIONS"])),
    ("Access-Control-Allow-Headers", ', '.join(["Content-Type"])),
]

def add_cors_headers(resp):
    for hdr in CORS_HEADERS:
        resp.headers.add_header(hdr[0], hdr[1])
    return resp
app.after_request(add_cors_headers)

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

def get_index(index_id):
    if not index_id in INDEXES:
        abort(404, message="Index '%s' not found" % index_id)
    return index_id

class DocumentResource(restful.Resource):
    def post(self, index):
        json = request.json
        index = get_index(index)
        check_fields(('text', 'id', 'title', 'url'), json)
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
        doc.name = json.get('name', None)
        doc.indexed = False
        doc.index = index
        try:
            doc.save()
        except ValidationError:
            abort(400, message="Invalid fields supplied")

        if 'index' in json and not doc.indexed:
            ss = simservers[index]
            ss.index([make_corpus(doc)])
            doc.indexed = True
            doc.save()
        return {'created': created}, 200

api.add_resource(DocumentResource, '/index/<string:index>/doc')

class IndexResource(restful.Resource):
    def post(self, index):
        json = request.json
        if not json:
            json = {}
        index = get_index(index)
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
        index = get_index(index)
        ss = simservers[index]
        ss.drop_index()
        msg = 'index %s deleted' % index
        if request.args and request.args.get('docs', '').lower() in ('1', 'true'):
            SemsiDocument.objects.filter(index=index).delete()
            msg += ' and documents removed'
        else:
            SemsiDocument.objects.filter(index=index).update(set__indexed=False)
        return {'message': msg}

api.add_resource(IndexResource, '/index/<string:index>')

# args: threshold, limit
class DocumentSimilarityResource(restful.Resource):
    def options(self, index):
        return {}

    def post(self, index):
        return self.get(index)

    def get(self, index):
        args = request.args
        index = get_index(index)
        ss = simservers[index]
        if not ss.stable.fresh_index:
            abort(404, message="Index '%s' empty" % index)
        if 'text' in args:
            text = args['text'].strip()
            tokens = tokenize(text)
            doc = {'tokens': tokens}
        elif 'id' in args:
            doc_id = args['id'].strip()
            try:
                doc = SemsiDocument.objects.get(id=doc_id)
            except SemsiDocument.DoesNotExist:
                abort(404, message="Doc with id '%s' not found" % doc_id)
            if not doc.indexed:
                abort(404, message="Doc '%s' not indexed" % doc_id)
            doc = doc_id
        else:
            abort(400, message="Must supply either 'text' or 'id'")

        res_list = ss.find_similar(doc, max_results=11)
        id_list = [x[0] for x in res_list]
        docs = SemsiDocument.objects.filter(id__in=id_list)
        doc_dict = {}
        for doc in docs:
            doc_dict[doc.id] = doc
        doc_list = []
        no_summary = request.args.get('no_summary', '').lower() in ('true', '1')
        for r in res_list:
            doc = doc_dict[r[0]]
            d = {'id': doc.id, 'relevance': r[1], 'name': doc.name}
            if not no_summary:
                d['title'] = doc.title
                d['summary'] = doc.text[0:200]
            doc_list.append(d)
        return doc_list

api.add_resource(DocumentSimilarityResource, '/index/<string:index>/similar')

connect('semsi')

simservers = {}
for idx in INDEXES:
    simservers[idx] = SessionServer(os.path.join(INDEX_PATH, '%s_index' % idx))

if __name__ == "__main__":
    app.run(debug=True)
